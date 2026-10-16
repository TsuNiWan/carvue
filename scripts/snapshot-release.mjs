import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

const [directory, phase] = process.argv.slice(2)
assert.ok(directory && ['before', 'after'].includes(phase), 'Usage: node scripts/snapshot-release.mjs artifacts/product/<batch> before|after')
const output = path.resolve(directory)
const relative = path.relative(path.resolve('artifacts/product'), output)
assert.ok(relative && !relative.startsWith('..') && !path.isAbsolute(relative), 'Snapshot directory must be inside artifacts/product')
const models = ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']
const files = ['index.html', 'package.json', 'package-lock.json', 'vite.config.ts', 'playwright.config.ts', 'tsconfig.json', 'scripts/snapshot-release.mjs']
for (const folder of ['src', 'e2e', 'scripts/modeling']) {
  for (const file of await readdir(folder, { recursive: true })) {
    if (/\.(ts|vue|css|mjs|py)$/.test(file)) files.push(`${folder}/${file.replaceAll('\\', '/')}`)
  }
}
for (const id of models) {
  files.push(`public/models/${id}/1.1.0/vehicle.glb`, `public/models/${id}/1.1.0/manifest.json`, `public/previews/${id}.webp`)
  for (const name of ['vehicle.blend', 'vehicle.raw.glb', 'build-report.json', 'compression-report.json']) files.push(`assets/source/${id}/${name}`)
}
const hashes = {}
await mkdir(output, { recursive: true })
for (const file of files.sort()) {
  const bytes = await readFile(file)
  hashes[file] = { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }
  if (phase === 'before' && file.startsWith('public/')) {
    const archived = path.join(output, 'frozen', file)
    await mkdir(path.dirname(archived), { recursive: true })
    await writeFile(archived, bytes)
  }
}
const snapshot = {
  recordedAt: new Date().toISOString(), phase, hashes,
  host: { platform: os.platform(), release: os.release(), arch: os.arch(), cpu: os.cpus()[0]?.model, logicalCpus: os.cpus().length, totalMemoryBytes: os.totalmem() },
  models: Object.fromEntries(models.map(id => [id, hashes[`public/models/${id}/1.1.0/vehicle.glb`]])),
}
if (phase === 'after') {
  const before = JSON.parse(await readFile(path.join(output, 'before.json'), 'utf8'))
  snapshot.changedFiles = [...new Set([...Object.keys(before.hashes), ...Object.keys(hashes)])].filter(file => before.hashes[file]?.sha256 !== hashes[file]?.sha256)
  snapshot.frozen = snapshot.changedFiles.length === 0
}
await writeFile(path.join(output, `${phase}.json`), JSON.stringify(snapshot, null, 2))
console.log(JSON.stringify({ phase, files: files.length, models: snapshot.models, changedFiles: snapshot.changedFiles, frozen: snapshot.frozen }))
assert.notEqual(snapshot.frozen, false, 'Release files changed during verification')
