import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { enable, disable, prepare, enqueue, flush, merge, status, validateSummary } from './auto-report.mjs';

const key = 'offline-test-key-at-least-24-characters';
const cmd = (root, args) => execFileSync('git', ['-C', root, ...args], {
  encoding: 'utf8', env: { ...process.env, PROJECT_REPORT_QUEUE_ONLY: '1',
    GIT_AUTHOR_NAME: 'Offline Test', GIT_AUTHOR_EMAIL: 'test@example.invalid',
    GIT_COMMITTER_NAME: 'Offline Test', GIT_COMMITTER_EMAIL: 'test@example.invalid' }, windowsHide: true }).trim();
async function fixture(fn) {
  const root = await mkdtemp(join(tmpdir(), 'project-report-auto-'));
  try {
    cmd(root, ['init', '-q']);
    await mkdir(join(root, '.project-hub'));
    await writeFile(join(root, '.project-hub/config.json'), JSON.stringify({ apiKey: key, projectId: 'fixture', url: 'https://project.boomclaws.com' }));
    await writeFile(join(root, '.gitignore'), '.project-hub/\n');
    await writeFile(join(root, 'app.txt'), 'initial');
    cmd(root, ['add', '.gitignore', 'app.txt']);
    cmd(root, ['commit', '-qm', 'initial']);
    await writeFile(join(root, '.project-hub/report.json'), JSON.stringify({ id: 'fixture', name: 'Fixture', progress: 20,
      pending: ['Keep pending'], pendingTests: ['Human test'], tasks: [{ id: 't', title: 'Existing', status: 'in_progress' }],
      metadata: { openQuestions: ['Unknown deadline'] } }));
    await fn(root);
  } finally {
    assert.ok(resolve(root).startsWith(resolve(tmpdir())) && root.includes('project-report-auto-'));
    await rm(root, { recursive: true, force: true });
  }
}

test('real post-commit queues facts; no network; disable keeps other hooks/config intact', async () => fixture(async root => {
  const enabled = await enable(root);
  await writeFile(join(root, 'app.txt'), 'changed');
  cmd(root, ['add', 'app.txt']);
  cmd(root, ['commit', '-qm', 'changed']);
  const queued = await readdir(join(root, '.project-hub/queue'));
  assert.equal(queued.length, 1);
  const event = JSON.parse(await readFile(join(root, '.project-hub/queue', queued[0]), 'utf8'));
  assert.equal(event.commit.subject, 'changed');
  assert.equal(event.summary, null);
  const before = await readFile(enabled.hookPath, 'utf8');
  await disable(root);
  assert.equal((await status(root)).enabled, false);
  assert.equal(await readFile(enabled.hookPath, 'utf8'), before);
  assert.equal((await enqueue(root, false)).skipped, 'disabled');
}));

test('existing hooks are never overwritten', async () => fixture(async root => {
  const path = join(root, '.git/hooks/post-commit');
  await writeFile(path, '#!/bin/sh\necho original\n');
  await assert.rejects(enable(root), /post-commit/);
  assert.equal(await readFile(path, 'utf8'), '#!/bin/sh\necho original\n');
}));

test('summary binds to staged tree; stale summary is not attached', async () => fixture(async root => {
  await enable(root);
  await writeFile(join(root, 'app.txt'), 'first change');
  cmd(root, ['add', 'app.txt']);
  const input = join(root, '.project-hub/patch.json');
  await writeFile(input, JSON.stringify({ completed: ['Implemented behavior'], testSummaryAppend: 'Offline check passed' }));
  await prepare(root, input);
  cmd(root, ['commit', '-qm', 'first change']);
  const sha = cmd(root, ['rev-parse', 'HEAD']);
  const first = JSON.parse(await readFile(join(root, '.project-hub/queue', `${sha}.json`), 'utf8'));
  assert.ok(first.summary);
  await writeFile(join(root, 'app.txt'), 'second change');
  cmd(root, ['add', 'app.txt']);
  cmd(root, ['commit', '-qm', 'second change']);
  const second = JSON.parse(await readFile(join(root, '.project-hub/queue', `${cmd(root, ['rev-parse', 'HEAD'])}.json`), 'utf8'));
  assert.equal(second.summary, null);
}));

test('query failure preserves queue; successful retry preserves project facts and redacts key', async () => fixture(async root => {
  await enable(root);
  await enqueue(root, false);
  await assert.rejects(flush(root, { get: async () => { throw new Error('network unavailable'); } }), /network/);
  assert.equal((await status(root)).pending, 1);
  let uploaded;
  const original = { id: 'fixture', name: 'Remote', progress: 42, pending: ['Do not clear'], pendingTests: ['Manual'],
    tasks: [{ id: 'x', title: 'Live state', status: 'in_progress' }], metadata: { apiKey: key, evidence: [key] } };
  const result = await flush(root, { get: async () => original, report: async (saved, project) => { uploaded = project; return { id: 'fixture' }; } });
  assert.equal(result.uploaded, 1);
  assert.equal(uploaded.progress, 42);
  assert.deepEqual(uploaded.pending, ['Do not clear']);
  assert.deepEqual(uploaded.tasks, original.tasks);
  assert.ok(!JSON.stringify(uploaded).includes(key));
  assert.equal((await status(root)).pending, 0);
  assert.equal((await enqueue(root, false)).skipped, 'already_uploaded');
}));

test('ambiguous upload outcome is reconciled by remote commit evidence without duplicate upload', async () => fixture(async root => {
  await enable(root);
  await enqueue(root, false);
  let remote = JSON.parse(await readFile(join(root, '.project-hub/report.json'), 'utf8'));
  let calls = 0;
  await assert.rejects(flush(root, { get: async () => remote, report: async (saved, project) => {
    calls++; remote = project; throw new Error('connection lost after saving');
  } }));
  await flush(root, { get: async () => remote, report: async () => { calls++; return { id: 'fixture' }; } });
  assert.equal(calls, 1);
  assert.equal((await status(root)).pending, 0);
}));

test('explicit summary merges lists/tasks without inventing completion from the commit', () => {
  const event = { projectId: 'fixture', commit: { sha: 'a'.repeat(40), subject: 'code commit' },
    summary: { patch: { completed: ['Evidence-backed change'], remove: { pending: ['Finished'] },
      tasks: [{ id: 't', title: 'Existing', status: 'done', testResult: 'Actual test evidence' }] } } };
  const original = { id: 'fixture', name: 'Fixture', progress: 15, pending: ['Finished', 'Keep'],
    tasks: [{ id: 't', title: 'Existing', status: 'in_progress', requiresHuman: false }] };
  const result = merge(original, null, event).project;
  assert.equal(result.progress, 15);
  assert.deepEqual(result.pending, ['Keep']);
  assert.equal(result.tasks[0].requiresHuman, false);
  assert.equal(result.tasks[0].status, 'done');
  assert.deepEqual(original.pending, ['Finished', 'Keep']);
});

test('automatic summary rejects fabricated progress and malformed fields', () => {
  assert.throws(() => validateSummary({ progress: 100 }), /未支持字段/);
  assert.throws(() => validateSummary({ testSummaryAppend: { passed: true } }), /字符串/);
  assert.throws(() => validateSummary({ status: 'all-done' }), /status/);
});

test('reusing key preserves auto mode; changing key pauses it and does not migrate queued events', async () => fixture(async root => {
  await enable(root);
  await enqueue(root, false);
  const helper = resolve('skills/project-report/scripts/hub.mjs');
  execFileSync(process.execPath, [helper, 'set', '--replace', '--project', root], { input: key + '\n', encoding: 'utf8', windowsHide: true });
  assert.equal((await status(root)).enabled, true);
  execFileSync(process.execPath, [helper, 'set', '--replace', '--project', root], { input: 'changed-offline-test-key-24-characters\n', encoding: 'utf8', windowsHide: true });
  assert.equal((await status(root)).enabled, false);
  await enable(root);
  let networkCalled = false;
  await assert.rejects(flush(root, { get: async () => { networkCalled = true; return null; } }), /旧 Key/);
  assert.equal(networkCalled, false);
  assert.equal((await status(root)).pending, 1);
}));
