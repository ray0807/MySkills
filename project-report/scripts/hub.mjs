import { randomBytes } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, basename } from 'node:path';
import { createInterface } from 'node:readline/promises';

const reminder = '请立即复制并保存这个 API Key；其他项目和工作安排助手使用同一个 Key。换 Key 就换用户，旧数据不会迁移。';
const [command, ...args] = process.argv.slice(2);
const option = name => { const i = args.indexOf(name); return i < 0 ? undefined : args[i + 1]; };
const root = resolve(option('--project') || process.cwd());
const directory = resolve(root, '.project-hub');
const file = resolve(directory, 'config.json');
const defaultUrl = 'https://project.boomclaws.com';

async function readConfig() {
  try { return JSON.parse(await readFile(file, 'utf8')); }
  catch (e) { if (e.code === 'ENOENT') return null; throw e; }
}
async function ignoreConfig() {
  const ignore = resolve(root, '.gitignore');
  let content = '';
  try { content = await readFile(ignore, 'utf8'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  if (!content.split(/\r?\n/).includes('.project-hub/')) await writeFile(ignore, `${content}${content && !content.endsWith('\n') ? '\n' : ''}.project-hub/\n`);
}
async function setup() {
  const existing = await readConfig();
  if (existing && !args.includes('--replace')) throw new Error('已有 Key；明确更换时才使用 --replace。换 Key 就换用户，旧数据不会迁移。');
  const url = defaultUrl;
  let key;
  if (command === 'generate') key = randomBytes(32).toString('base64url');
  else {
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    try { key = await rl.question('请输入已有 API Key（仅在本机终端输入）：'); } finally { rl.close(); }
  }
  if (!key || key.length < 24 || key.length > 256 || !/^[\x21-\x7e]+$/.test(key)) throw new Error('Key 必须为 24–256 个不含空格的可打印 ASCII 字符');
  const projectId = existing?.projectId || basename(root).replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 128) || 'project';
  await ignoreConfig();
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const autoReport = existing?.autoReport && existing.apiKey !== key
    ? { ...existing.autoReport, enabled: false, reason: 'API Key changed; re-enable after confirming identity' }
    : existing?.autoReport;
  await writeFile(file, `${JSON.stringify({ ...existing, url, apiKey: key, projectId, ...(autoReport ? { autoReport } : {}) }, null, 2)}\n`, { mode: 0o600 });
  if (command === 'generate') console.log(`API Key: ${key}`);
  console.log(reminder);
  console.log(`已保存到 ${file}，可以从该文件复制。`);
}
async function rpc(config, endpoint, method, params, id) {
  const response = await fetch(`${defaultUrl}${endpoint}`, {
    method: 'POST', redirect: 'error', signal: AbortSignal.timeout(30000),
    headers: { Authorization: `Bearer ${config.apiKey}`, 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-11-25' },
    body: JSON.stringify({ jsonrpc: '2.0', id, method, params })
  });
  if (!response.ok) throw new Error(`MCP HTTP ${response.status}，未确认上传成功`);
  const result = await response.json();
  if (result.error) throw new Error(`MCP 调用失败：${result.error.message}`);
  return result.result;
}
async function invoke() {
  const config = await readConfig();
  if (!config) throw new Error('当前项目没有 Key，请选择输入已有 Key（set）或生成新 Key（generate）');
  const endpoint = command === 'report' ? '/mcp/report' : '/mcp/query';
  let tool;
  if (command === 'report') {
    const project = JSON.parse(await readFile(resolve(directory, 'report.json'), 'utf8'));
    if (project.id !== config.projectId) throw new Error('快照 ID 与 config.json 的 projectId 不一致');
    tool = { name: 'report_project', arguments: { project } };
  } else tool = { name: 'get_project', arguments: { id: config.projectId } };
  await rpc(config, endpoint, 'initialize', { protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'project-report-skill', version: '0.1.0' } }, 1);
  const result = await rpc(config, endpoint, 'tools/call', tool, 2);
  if (result.isError) {
    const text = result.content?.find(c => c.type === 'text')?.text;
    if (command === 'get' && text && JSON.parse(text).error === 'Project not found') { console.log(JSON.stringify({ exists: false, projectId: config.projectId })); return; }
    throw new Error('MCP 工具返回错误，未确认上传成功');
  }
  const text = result.content.find(c => c.type === 'text').text;
  if (command === 'report') {
    const saved = JSON.parse(text);
    console.log(JSON.stringify({ uploaded: true, projectId: saved.id, name: saved.name, updatedAt: saved.updatedAt }));
  } else console.log(text);
}
try {
  if (args.includes('--url') && option('--url') !== defaultUrl) throw new Error(`服务地址固定为 ${defaultUrl}，无需设置域名`);
  if (['generate', 'set'].includes(command)) await setup();
  else if (['get', 'report'].includes(command)) await invoke();
  else throw new Error('用法：hub.mjs generate|set|get|report --project <目录> [--replace]');
} catch (e) { console.error(e.message); process.exitCode = 1; }
