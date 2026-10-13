import { spawn, execFileSync } from 'node:child_process';
import { readFile, writeFile, mkdir, rename, readdir, unlink, chmod, open } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const service = 'https://project.boomclaws.com';
const script = fileURLToPath(import.meta.url);
const keyValid = key => typeof key === 'string' && /^[\x21-\x7e]{24,256}$/.test(key);
const arrayFields = ['completed', 'pending', 'pendingTests', 'blockers', 'nextActions'];
const patchFields = ['name', 'description', 'goal', 'status', 'priority', 'deadline'];
const taskStatuses = new Set(['todo', 'in_progress', 'pending_test', 'testing', 'done', 'blocked']);

async function json(path, fallback) {
  try { return JSON.parse(await readFile(path, 'utf8')); }
  catch (e) { if (e.code === 'ENOENT' && fallback !== undefined) return fallback; throw e; }
}
async function atomic(path, value) {
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const temp = `${path}.${process.pid}.tmp`;
  await writeFile(temp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  await rename(temp, path);
}
function git(root, args) {
  const env = { ...process.env };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_PREFIX', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES']) delete env[key];
  return execFileSync('git', ['-C', root, ...args], { encoding: 'utf8', env, windowsHide: true, timeout: 15000 }).trim();
}
function samePath(a, b) { return process.platform === 'win32' ? resolve(a).toLowerCase() === resolve(b).toLowerCase() : resolve(a) === resolve(b); }
function repository(root) {
  if (!samePath(git(root, ['rev-parse', '--show-toplevel']), root)) throw new Error('--project 必须是目标仓库根目录');
}
async function config(root) {
  const value = await json(resolve(root, '.project-hub/config.json'));
  if (!keyValid(value.apiKey) || !/^[a-zA-Z0-9_-]{1,128}$/.test(value.projectId ?? '')) throw new Error('请先设置有效的项目 Key 与项目 ID');
  return value;
}
function shellQuote(value) { return `'${value.replaceAll('\\', '/').replaceAll("'", "'\"'\"'")}'`; }
async function ignore(root) {
  const path = resolve(root, '.gitignore');
  let text;
  try { text = await readFile(path, 'utf8'); } catch (e) { if (e.code !== 'ENOENT') throw e; text = ''; }
  if (!text.split(/\r?\n/).includes('.project-hub/')) await writeFile(path, `${text}${text && !text.endsWith('\n') ? '\n' : ''}.project-hub/\n`);
}

export async function enable(root) {
  root = resolve(root);
  repository(root);
  const saved = await config(root);
  let hooksPath;
  try { hooksPath = git(root, ['config', '--get', 'core.hooksPath']); } catch (e) { if (e.status !== 1) throw e; }
  if (hooksPath) throw new Error('已有 core.hooksPath；请按 README 将 enqueue 命令接入现有 post-commit，不自动覆盖');
  const directory = resolve(root, git(root, ['rev-parse', '--git-path', 'hooks']));
  const hook = resolve(directory, 'post-commit');
  const body = `#!/bin/sh\n# project-report managed post-commit v1\n${shellQuote(process.execPath)} ${shellQuote(script)} enqueue --project "$(git rev-parse --show-toplevel)" || :\nexit 0\n`;
  let existing;
  try { existing = await readFile(hook, 'utf8'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  if (existing && existing !== body) throw new Error('已有或已自定义 post-commit；保留原钩子，按 README 手动接入 enqueue');
  await ignore(root);
  await mkdir(directory, { recursive: true });
  await writeFile(hook, body, { mode: 0o755 });
  await chmod(hook, 0o755);
  await atomic(resolve(root, '.project-hub/config.json'), { ...saved, autoReport: { enabled: true, enabledAt: new Date().toISOString(), hookPath: hook, summaryProtocol: 1 } });
  return { enabled: true, projectId: saved.projectId, hookPath: hook, uploadsOn: 'future post-commit', keyReused: true };
}
export async function disable(root) {
  const saved = await config(root);
  await atomic(resolve(root, '.project-hub/config.json'), { ...saved, autoReport: { ...saved.autoReport, enabled: false } });
  return { enabled: false, pendingPreserved: true, hookPreserved: true };
}
export function validateSummary(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('摘要必须是 JSON 对象');
  const allowed = new Set([...patchFields, ...arrayFields, 'remove', 'tasks', 'testSummaryAppend', 'openQuestions']);
  if (Object.keys(value).some(k => !allowed.has(k))) throw new Error('摘要包含未支持字段；进度比例、凭据和任意 metadata 不能自动覆盖');
  for (const field of [...patchFields, 'testSummaryAppend']) if (value[field] !== undefined && typeof value[field] !== 'string') throw new Error(`${field} 必须是字符串`);
  if (value.status && !['planned', 'active', 'paused', 'completed', 'blocked'].includes(value.status)) throw new Error('项目 status 无效');
  if (value.priority && !['low', 'medium', 'high', 'urgent'].includes(value.priority)) throw new Error('项目 priority 无效');
  for (const field of [...arrayFields, 'openQuestions']) if (value[field] !== undefined && (!Array.isArray(value[field]) || value[field].some(x => typeof x !== 'string'))) throw new Error(`${field} 必须为字符串数组`);
  if (value.remove) for (const [field, values] of Object.entries(value.remove)) {
    if (!arrayFields.includes(field) || !Array.isArray(values) || values.some(x => typeof x !== 'string')) throw new Error('remove 只接受指定列表的明确字符串项');
  }
  if (value.tasks) {
    if (!Array.isArray(value.tasks) || value.tasks.some(t => !t.id || !t.title || !taskStatuses.has(t.status))) throw new Error('任务必须含 id/title/合法 status');
    if (new Set(value.tasks.map(t => t.id)).size !== value.tasks.length) throw new Error('摘要任务 ID 重复');
  }
  return value;
}
export async function prepare(root, input) {
  repository(root);
  const saved = await config(root);
  const patch = validateSummary(await json(input));
  let baseCommit = null;
  try { baseCommit = git(root, ['rev-parse', '--verify', 'HEAD']); } catch { /* first commit */ }
  const stagedTree = git(root, ['write-tree']);
  const summary = { protocol: 1, projectId: saved.projectId, baseCommit, stagedTree, preparedAt: new Date().toISOString(), patch };
  await atomic(resolve(root, '.project-hub/summary.json'), summary);
  return { prepared: true, stagedTree, baseCommit, appliesTo: 'matching next commit only' };
}
export async function enqueue(root, background = true) {
  root = resolve(root);
  repository(root);
  const saved = await config(root);
  if (!saved.autoReport?.enabled) return { skipped: 'disabled' };
  const sha = git(root, ['rev-parse', 'HEAD']);
  const path = resolve(root, '.project-hub/queue', `${sha}.json`);
  if (await json(resolve(root, '.project-hub/sent', `${sha}.json`), null)) return { skipped: 'already_uploaded', commit: sha };
  const commit = { sha, tree: git(root, ['rev-parse', 'HEAD^{tree}']),
    parents: git(root, ['show', '-s', '--format=%P', sha]).split(' ').filter(Boolean),
    subject: git(root, ['show', '-s', '--format=%s', sha]), committedAt: git(root, ['show', '-s', '--format=%cI', sha]),
    files: git(root, ['diff-tree', '--root', '--no-commit-id', '--name-only', '-z', '-r', sha]).split('\0').filter(Boolean),
    branch: git(root, ['rev-parse', '--abbrev-ref', 'HEAD']) };
  const summary = await json(resolve(root, '.project-hub/summary.json'), null);
  const matched = summary?.projectId === saved.projectId && summary.stagedTree === commit.tree && summary.baseCommit === (commit.parents[0] ?? null);
  const event = { projectId: saved.projectId, keyIdentity: createHash('sha256').update(saved.apiKey).digest('hex'),
    queuedAt: new Date().toISOString(), commit, summary: matched ? summary : null };
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  if (!await json(path, null)) await atomic(path, event);
  if (background && process.env.PROJECT_REPORT_QUEUE_ONLY !== '1') {
    const worker = spawn(process.execPath, [script, 'retry', '--project', root], { detached: true, stdio: 'ignore', windowsHide: true });
    worker.on('error', () => {});
    worker.unref();
  }
  return { queued: true, commit: sha, summaryAttached: Boolean(matched) };
}
function sanitize(value, apiKey) {
  if (typeof value === 'string') return value.replaceAll(apiKey, '[REDACTED]');
  if (Array.isArray(value)) return value.map(v => sanitize(v, apiKey));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value)
    .filter(([k]) => !/^(api_?key|authorization|password|secret|cookie|access_?token)$/i.test(k))
    .map(([k, v]) => [k, sanitize(v, apiKey)]));
  return value;
}
export function merge(remote, baseline, event) {
  const project = structuredClone(remote ?? baseline);
  if (!project?.name || project.id !== event.projectId) throw new Error('项目不存在时需要匹配 ID/name 的本地 report.json；不凭提交虚构整个项目');
  delete project.updatedAt;
  const metadata = project.metadata ??= {};
  const activity = metadata.codeActivity ??= [];
  if (activity.some(c => c.sha === event.commit.sha)) return { duplicate: true, project };
  const patch = event.summary?.patch;
  if (patch) {
    validateSummary(patch);
    for (const field of patchFields) if (patch[field] !== undefined) project[field] = patch[field];
    for (const field of arrayFields) {
      const remove = patch.remove?.[field] ?? [];
      project[field] = [...new Set([...(project[field] ?? []).filter(x => !remove.includes(x)), ...(patch[field] ?? [])])];
    }
    const tasks = new Map((project.tasks ?? []).map(t => [t.id, t]));
    for (const task of patch.tasks ?? []) tasks.set(task.id, { ...tasks.get(task.id), ...task });
    project.tasks = [...tasks.values()];
    if (patch.testSummaryAppend) project.testSummary = `${project.testSummary ?? ''}\n${patch.testSummaryAppend}`.trim();
    metadata.openQuestions = [...new Set([...(metadata.openQuestions ?? []), ...(patch.openQuestions ?? [])])];
  }
  activity.push({ ...event.commit, summaryApplied: Boolean(patch), recordedAt: new Date().toISOString() });
  metadata.codeActivity = activity.slice(-100);
  metadata.lastAutomaticReport = { commit: event.commit.sha, summaryApplied: Boolean(patch),
    note: patch ? 'AI staged-tree-bound summary plus commit facts' : 'Commit facts only; task/test/progress state not inferred' };
  project.source = 'project-report post-commit (existing snapshot + explicit AI summary + Git facts)';
  return { duplicate: false, project };
}
async function rpc(saved, endpoint, method, params, id) {
  const response = await fetch(`${service}${endpoint}`, { method: 'POST', redirect: 'error', signal: AbortSignal.timeout(8000),
    headers: { Authorization: `Bearer ${saved.apiKey}`, 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' },
    body: JSON.stringify({ jsonrpc: '2.0', id, method, params }) });
  if (!response.ok) throw new Error(`MCP HTTP ${response.status}`);
  const body = await response.json();
  if (body.error) throw new Error(`MCP protocol error ${body.error.code}`);
  return body.result;
}
async function tool(saved, endpoint, name, args) {
  await rpc(saved, endpoint, 'initialize', { protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'project-report-auto', version: '1.0.0' } }, 1);
  const result = await rpc(saved, endpoint, 'tools/call', { name, arguments: args }, 2);
  const content = result.content?.find(c => c.type === 'text')?.text;
  const value = JSON.parse(content);
  if (result.isError) {
    if (name === 'get_project' && value.error === 'Project not found') return null;
    throw new Error('MCP tool rejected operation');
  }
  return value;
}
const client = {
  get: (saved, id) => tool(saved, '/mcp/query', 'get_project', { id }),
  report: (saved, project) => tool(saved, '/mcp/report', 'report_project', { project })
};
async function lock(directory) {
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const path = resolve(directory, 'auto.lock');
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const handle = await open(path, 'wx', 0o600);
      await handle.writeFile(JSON.stringify({ pid: process.pid }));
      await handle.close();
      return async () => { if ((await json(path, null))?.pid === process.pid) await unlink(path); };
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      const previous = await json(path, null);
      if (!previous?.pid) return null;
      try { process.kill(previous.pid, 0); return null; }
      catch (error) { if (error.code !== 'ESRCH') return null; await unlink(path); }
    }
  }
  return null;
}
export async function flush(root, transport = client) {
  const saved = await config(root);
  if (!saved.autoReport?.enabled) return { skipped: 'disabled' };
  const directory = resolve(root, '.project-hub');
  const release = await lock(directory);
  if (!release) return { skipped: 'worker_active' };
  let uploaded = 0;
  try {
    const queue = resolve(directory, 'queue');
    await mkdir(queue, { recursive: true, mode: 0o700 });
    const entries = await Promise.all((await readdir(queue)).filter(n => /^[0-9a-f]{40,64}\.json$/.test(n)).map(async n => ({ path: resolve(queue, n), event: await json(resolve(queue, n)) })));
    entries.sort((a, b) => a.event.queuedAt.localeCompare(b.event.queuedAt));
    for (const { path, event } of entries.slice(0, 20)) {
      if (event.projectId !== saved.projectId) throw new Error('队列项目 ID 不匹配');
      if (event.keyIdentity !== createHash('sha256').update(saved.apiKey).digest('hex')) throw new Error('待上报记录属于旧 Key；不向新身份自动迁移');
      const remote = await transport.get(saved, saved.projectId); // query failure never means absent
      const baseline = remote ? null : await json(resolve(directory, 'report.json'), null);
      const merged = merge(remote, baseline, event);
      const project = sanitize(merged.project, saved.apiKey);
      if (!merged.duplicate) {
        const result = await transport.report(saved, project);
        if (result?.id !== saved.projectId) throw new Error('上传未返回匹配项目 ID');
      }
      await atomic(resolve(directory, 'sent', `${event.commit.sha}.json`), { commit: event.commit.sha, acknowledgedAt: new Date().toISOString() });
      await atomic(resolve(directory, 'last-auto-report.json'), project);
      await unlink(path);
      uploaded++;
    }
    await atomic(resolve(directory, 'auto-status.json'), { status: 'ok', uploaded, checkedAt: new Date().toISOString() });
    return { uploaded, pending: (await readdir(queue)).filter(n => n.endsWith('.json')).length };
  } catch (error) {
    await atomic(resolve(directory, 'auto-status.json'), { status: 'pending_retry', uploaded, error: String(error.message).replaceAll(saved.apiKey, '[REDACTED]'), checkedAt: new Date().toISOString() });
    throw error;
  } finally { await release(); }
}
export async function status(root) {
  const saved = await config(root);
  let pending = 0;
  try { pending = (await readdir(resolve(root, '.project-hub/queue'))).filter(n => n.endsWith('.json')).length; }
  catch (e) { if (e.code !== 'ENOENT') throw e; }
  return { enabled: Boolean(saved.autoReport?.enabled), projectId: saved.projectId, keyConfigured: true,
    pending, lastAttempt: await json(resolve(root, '.project-hub/auto-status.json'), null) };
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  const [command, ...args] = process.argv.slice(2);
  const option = name => { const i = args.indexOf(name); return i < 0 ? undefined : args[i + 1]; };
  const root = resolve(option('--project') || process.cwd());
  try {
    let result;
    if (command === 'enable') result = await enable(root);
    else if (command === 'disable') result = await disable(root);
    else if (command === 'prepare') result = await prepare(root, resolve(option('--input') || ''));
    else if (command === 'enqueue') result = await enqueue(root);
    else if (command === 'retry') result = await flush(root);
    else if (command === 'status') result = await status(root);
    else throw new Error('用法：auto-report.mjs enable|disable|prepare|enqueue|retry|status --project <仓库根目录> [--input <摘要JSON>]');
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(`project-report: ${error.message}`);
    // post-commit always leaves the already-created commit intact.
    if (command !== 'enqueue') process.exitCode = 1;
  }
}
