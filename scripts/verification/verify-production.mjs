import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { preview } from 'vite'
import { chromium, expect } from '@playwright/test'

const batch = process.argv[2] ?? 'm4-production'
assert.match(batch, /^[a-z0-9-]+$/)
const output = path.resolve('artifacts/product', batch)
const final = process.argv.includes('--final')
await mkdir(output, { recursive: true })
const ids = ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']
const report = { startedAt: new Date().toISOString(), final, http: [], journeys: [], layouts: [], errors: [] }
const digest = bytes => createHash('sha256').update(bytes).digest('hex')
const files = (await readdir('dist', { recursive: true, withFileTypes: true })).filter(entry => entry.isFile()).map(entry => path.relative('dist', path.join(entry.parentPath, entry.name)).replaceAll('\\', '/'))
const contentTypes = { '.html': /text\/html/, '.js': /javascript/, '.css': /text\/css/, '.glb': /model\/gltf-binary|application\/octet-stream/, '.json': /application\/json/, '.webp': /image\/webp/, '.svg': /image\/svg\+xml/ }

async function inspectLayout(page, label) {
  const result = await page.evaluate(() => {
    const text = []
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    while (walker.nextNode()) {
      const node = walker.currentNode
      const element = node.parentElement
      if (!node.textContent.trim() || !element || element.namespaceURI !== 'http://www.w3.org/1999/xhtml' || element.closest('.sr-only,script,style')) continue
      const bounds = element.getBoundingClientRect()
      const style = getComputedStyle(element)
      if (bounds.width && bounds.height && style.visibility !== 'hidden' && Number(style.opacity) > 0) text.push({ text: node.textContent.trim().slice(0, 60), fontSize: parseFloat(style.fontSize) })
    }
    const controls = [...document.querySelectorAll('button, summary, .range-input, .sensor-grid label, .vehicle-information a')].flatMap(element => {
      const bounds = element.getBoundingClientRect()
      if (!bounds.width || !bounds.height) return []
      return [{ label: element.getAttribute('aria-label') ?? element.textContent.trim().slice(0, 50), height: bounds.height }]
    })
    const controlText = [...document.querySelectorAll('.door-actions button,.range-legend button,.vehicle-information summary,.vehicle-information a,.back-link,.model-switcher > summary,.view-controls button,.segmented button,.door-button > span,.scenario-list strong,.panel-tabs button,.primary-button')].flatMap(element => {
      const bounds = element.getBoundingClientRect()
      return bounds.width && bounds.height ? [{ label: element.textContent.trim().slice(0, 50), fontSize: parseFloat(getComputedStyle(element).fontSize) }] : []
    })
    return { width: innerWidth, height: innerHeight, bodyFont: parseFloat(getComputedStyle(document.body).fontSize), overflowX: document.documentElement.scrollWidth > innerWidth, overflowY: Boolean(document.querySelector('.showroom-workspace')) && document.documentElement.scrollHeight > innerHeight, text, controls, controlText }
  })
  assert.ok(result.bodyFont >= 16, 'Main text must be at least 16px')
  assert.equal(result.overflowX, false, 'Horizontal overflow')
  assert.equal(result.overflowY, false, 'Desktop detail page overflow')
  assert.deepEqual(result.text.filter(item => item.fontSize < 12), [], 'Text below 12px')
  assert.deepEqual(result.controls.filter(item => item.height < 43.9), [], 'Control target below 44px')
  assert.deepEqual(result.controlText.filter(item => item.fontSize < 14), [], 'Control text below 14px')
  report.layouts.push({ label, ...result })
}

try {
  for (const prefix of ['/', '/carvue/']) {
    const server = await preview({ configFile: 'vite.config.ts', base: prefix, preview: { host: '127.0.0.1', port: 4173, strictPort: true } })
    const base = `http://127.0.0.1:4173${prefix}`
    try {
      for (const file of files) {
        const response = await fetch(new URL(file, base))
        const bytes = Buffer.from(await response.arrayBuffer())
        const expected = await readFile(path.join('dist', file))
        assert.equal(response.status, 200, file)
        assert.equal(digest(bytes), digest(expected), file)
        const expectedType = contentTypes[path.extname(file)]
        if (expectedType) assert.match(response.headers.get('content-type') ?? '', expectedType, file)
        report.http.push({ prefix, file, bytes: bytes.length, sha256: digest(bytes), contentType: response.headers.get('content-type'), status: response.status })
      }
      const environments = prefix === '/' ? ['chrome', 'msedge'].flatMap(channel => [1280, 1920].map(width => ({ channel, width, height: width === 1280 ? 720 : 1080 }))) : [{ channel: 'chrome', width: 1920, height: 1080 }]
      for (const environment of environments) {
        const browser = await chromium.launch({ channel: environment.channel, headless: true })
        try {
          const page = await browser.newPage({ viewport: { width: environment.width, height: environment.height } })
          page.on('pageerror', error => report.errors.push({ environment, prefix, message: error.message }))
          page.on('response', response => { if (response.status() >= 400) report.errors.push({ environment, prefix, url: response.url(), status: response.status() }) })
          const label = `${prefix === '/' ? 'root' : 'subdirectory'}-${environment.channel}-${environment.width}`
          await page.goto(`${base}#/vehicles`)
          await expect(page.locator('.vehicle-card')).toHaveCount(5)
          await expect.poll(() => page.locator('.vehicle-card img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0))).toBe(true)
          await page.locator('.vehicle-card img').evaluateAll(async images => {
            await Promise.all(images.map(image => image.decode()))
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
          })
          await inspectLayout(page, `${label}-collection`)
          if (final) await expect(page.locator('.card-development')).toHaveCount(0)
          await page.screenshot({ path: `${output}/${label}-collection.png`, fullPage: true })
          for (const id of prefix === '/' ? ['sedan-01'] : ids) {
            const received = page.waitForResponse(response => new URL(response.url()).pathname === `${prefix}models/${id}/1.1.0/vehicle.glb` && response.ok())
            await page.goto(`${base}#/vehicles/${id}`)
            await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveAttribute('data-ready', 'true', { timeout: 20_000 })
            await expect(page.getByTestId('renderer-diagnostics')).toHaveCount(0)
            if (final) await expect(page.locator('.development-badge,.asset-note')).toHaveCount(0)
            const response = await received
            const actual = await response.body()
            assert.equal(digest(actual), digest(await readFile(`dist/models/${id}/1.1.0/vehicle.glb`)))
            await page.locator('.model-switcher summary').click()
            await inspectLayout(page, `${label}-${id}-switcher`)
            await page.locator('.model-switcher summary').click()
            await page.getByRole('button', { name: '全部開啟', exact: true }).click()
            await page.getByRole('switch', { name: ['suv-01', 'suv-02'].includes(id) ? '後尾門' : '後車廂', exact: true }).click()
            await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
            await page.getByRole('slider', { name: '前輪轉向角度' }).fill('30')
            await expect(page.locator('.door-button small')).toHaveText(['已開啟', '已開啟', '已開啟', '已開啟'])
            await expect(page.locator('.trunk-row small')).toHaveText('已開啟')
            await page.getByRole('button', { name: '俯視', exact: true }).click()
            await page.waitForTimeout(500)
            await page.screenshot({ path: `${output}/${label}-${id}-open.png` })
            await page.locator('.vehicle-information summary').click()
            await inspectLayout(page, `${label}-${id}-controls`)
            await page.getByRole('tab', { name: 'ADAS 情境' }).click()
            await page.getByRole('button', { name: '播放情境', exact: true }).click()
            await expect(page.getByRole('button', { name: '暫停情境', exact: true })).toBeVisible()
            await inspectLayout(page, `${label}-${id}-adas`)
            await page.getByRole('button', { name: '重設展示', exact: true }).click()
            await page.getByRole('link', { name: '所有車款', exact: true }).click()
            await expect(page.locator('.vehicle-card')).toHaveCount(5)
            report.journeys.push({ label, vehicle: id, modelSha256: digest(actual), browserVersion: browser.version(), directRoute: true, controls: true, adas: true, returnToCollection: true })
          }
          await page.setViewportSize({ width: 390, height: 844 })
          await page.goto(`${base}#/vehicles/suv-01`)
          await expect(page.getByRole('heading', { name: '請在桌機開啟完整 3D 體驗' })).toBeVisible()
          await expect(page.locator('canvas')).toHaveCount(0)
          await inspectLayout(page, `${label}-mobile`)
          await page.goto('about:blank')
        } finally { await browser.close() }
      }
    } finally { await new Promise(resolve => server.httpServer.close(resolve)) }
  }
  assert.deepEqual(report.errors, [])
  report.status = 'passed'
} catch (error) {
  report.status = 'failed'
  report.failure = error.stack ?? String(error)
  process.exitCode = 1
} finally {
  report.endedAt = new Date().toISOString()
  await writeFile(`${output}/results.json`, JSON.stringify(report, null, 2))
  console.log(JSON.stringify({ status: report.status, httpFiles: report.http.length, journeys: report.journeys.length, layouts: report.layouts.length, errors: report.errors, failure: report.failure }))
}
