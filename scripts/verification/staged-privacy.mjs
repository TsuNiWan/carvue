import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'

const all = process.argv.includes('--all')
const history = process.argv.includes('--history')
assert.ok(!(all && history), 'Choose either --all or --history')
let entries
if (history) {
  const objects = execFileSync('git', ['rev-list', '--objects', 'HEAD']).toString().trim().split('\n').map(line => ({ object: line.slice(0, 40), path: line.slice(41) }))
  const types = execFileSync('git', ['cat-file', '--batch-check=%(objecttype)'], { input: objects.map(item => item.object).join('\n') + '\n' }).toString().trim().split('\n')
  entries = objects.filter((item, index) => types[index] === 'blob')
} else {
  entries = execFileSync('git', all ? ['ls-files', '-z'] : ['diff', '--cached', '--name-only', '--diff-filter=ACM', '-z']).toString().split('\0').filter(Boolean).map(path => ({ path }))
}
assert.ok(entries.length, 'Stage or commit the intended release files before scanning')
const forbidden = /^(?:tools|node_modules|artifacts|dist|test-results|playwright-report|\.cache|\.codex|\.agents|\.aws)\/|(?:^|\/)(?:\.env(?:\..*)?|id_rsa|id_ed25519|credentials|\.npmrc)$/i
const patterns = [
  ['Windows personal directory', /[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\x00\r\n]+/i],
  ['Relative personal directory', /(?:^|[\x00\s])Users[\\/][a-z0-9._-]+[\\/](?:Documents|Desktop|Pictures|AppData)/i],
  ['Unix home directory', /\/(?:Users|home)\/[a-z0-9._-]+\//i],
  ['Private key', /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/],
  ['GitHub token', /(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})/],
  ['Cloud access key', /(?:AKIA|ASIA)[A-Z0-9]{16}/],
  ['Authenticated URL', /https?:\/\/[^\s/@]+:[^\s/@]+@/i],
  ['OpenAI key', /sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}/],
  ['Slack token', /xox[baprs]-[A-Za-z0-9-]{20,}/],
]
const issues = []
const files = []
for (const { path, object } of entries) {
  if (forbidden.test(path)) issues.push({ path, category: 'Excluded release path' })
  const bytes = execFileSync('git', object ? ['cat-file', 'blob', object] : ['show', `:${path}`], { maxBuffer: 128 * 1024 * 1024 })
  if (bytes.length > 100 * 1024 * 1024) issues.push({ path, category: 'File exceeds GitHub size limit' })
  for (const [category, pattern] of patterns) {
    if ([bytes.toString('utf8'), bytes.toString('utf16le')].some(text => pattern.test(text))) issues.push({ path, category })
  }
  files.push({ path, object, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') })
}
if (history) {
  const metadata = execFileSync('git', ['log', 'HEAD', '--format=%an%n%ae%n%cn%n%ce%n%B']).toString()
  for (const [category, pattern] of patterns) if (pattern.test(metadata)) issues.push({ path: '<commit metadata>', category })
}
const report = { checkedAt: new Date().toISOString(), scope: `${history ? 'All blobs and commit metadata reachable from publishable HEAD' : all ? 'Entire Git index' : 'Changed staged files'}: exact bytes, including binary files; UTF-8 and UTF-16LE patterns. Screenshots require separate visual inspection.`, files, issues }
await mkdir('artifacts/product', { recursive: true })
await writeFile(`artifacts/product/${history ? 'history' : 'staged'}-privacy.json`, JSON.stringify(report, null, 2))
console.log(JSON.stringify({ files: files.length, bytes: files.reduce((sum, file) => sum + file.bytes, 0), issues }))
assert.deepEqual(issues, [], 'Resolve staged privacy findings before committing or pushing')
