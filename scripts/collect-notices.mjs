import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'

const lock = JSON.parse(await readFile('package-lock.json', 'utf8'))
const inventory = []
const sections = []
const upstream = {
  '@vue/devtools-api': 'https://raw.githubusercontent.com/vuejs/vue-devtools/v6.6.4/LICENSE',
  'std-env': 'https://raw.githubusercontent.com/unjs/std-env/v4.3.0/LICENCE',
}
for (const [location, entry] of Object.entries(lock.packages)) {
  if (!location) continue
  const name = location.split('node_modules/').at(-1)
  let files
  try { files = await readdir(location) } catch (error) { if (error.code !== 'ENOENT') throw error }
  const record = { name, version: entry.version, license: entry.license, development: Boolean(entry.dev), optional: Boolean(entry.optional), installed: Boolean(files), notices: [] }
  inventory.push(record)
  if (!files) continue
  let notices = await Promise.all(files.filter(file => /^(license|licence|copying|notice)(\.|$|-)/i.test(file)).sort().map(async file => ({ source: `${location}/${file}`, text: await readFile(`${location}/${file}`, 'utf8') })))
  if (!notices.length && name.startsWith('@rolldown/binding-')) {
    notices = [{ source: 'node_modules/rolldown/LICENSE', text: await readFile('node_modules/rolldown/LICENSE', 'utf8') }]
  }
  if (!notices.length && upstream[name]) {
    const response = await fetch(upstream[name])
    if (!response.ok) throw new Error(`${name}: upstream license HTTP ${response.status}`)
    notices = [{ source: upstream[name], text: await response.text() }]
  }
  if (!notices.length) throw new Error(`License text missing: ${name}`)
  sections.push(`## ${name} ${entry.version} (${entry.license})\n\n${entry.dev ? '開發／建置相依' : '直接或間接執行相依'}\n`)
  for (const notice of notices) {
    const sha256 = createHash('sha256').update(notice.text).digest('hex')
    record.notices.push({ source: notice.source, sha256 })
    sections.push(`來源：${notice.source}\n\n\`\`\`text\n${notice.text.trim()}\n\`\`\`\n`)
  }
}
const decoderHeader = (await readFile('node_modules/three/examples/jsm/libs/meshopt_decoder.module.js', 'utf8')).split('\n').slice(0, 5).join('\n')
const meshoptLicense = await readFile('node_modules/meshoptimizer/LICENSE.md', 'utf8')
sections.unshift(`## 網站內含 Meshopt 解碼器\n\nThree.js 附帶的解碼器建置自 meshoptimizer 1.1；建模工具另使用 package-lock 中的版本。以下保留解碼器原始標頭與 MIT 全文。\n\n\`\`\`text\n${decoderHeader}\n\n${meshoptLicense.trim()}\n\`\`\`\n`)
const heading = '# 第三方授權聲明\n\n本文件保留已安裝的直接、間接與開發相依授權全文，包括套件附帶的第三方聲明。實際網站執行相依為 Vue、Vue Router、Three.js、three-mesh-bvh 及其打包相依；開發工具未隨網站執行。未安裝的平台選用套件只列於盤點，不宣稱已審查其二進位內容。\n\n依據 package-lock.json 與套件內授權檔產生；升級相依後執行 `node scripts/collect-notices.mjs` 重新盤點。技術授權來源網址為必要通知，不屬於車廠參考資料。\n\n'
await writeFile('THIRD_PARTY_NOTICES.md', heading + sections.join('\n'))
await mkdir('docs/evidence', { recursive: true })
await writeFile('docs/evidence/dependency-licenses.json', JSON.stringify({ lockSha256: createHash('sha256').update(await readFile('package-lock.json')).digest('hex'), packages: inventory }, null, 2) + '\n')
console.log(`Recorded ${inventory.length} locked dependencies; ${inventory.filter(item => item.installed).length} installed packages with license texts.`)
