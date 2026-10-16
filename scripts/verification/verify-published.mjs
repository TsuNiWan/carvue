import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { chromium, expect } from '@playwright/test'

const base = new URL(process.argv[2])
assert.equal(base.protocol, 'https:')
assert.ok(base.pathname.endsWith('/'), 'Use a trailing slash for the deployed project URL')
const ids = ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']
const report = { checkedAt: new Date().toISOString(), url: base.href, resources: [], journeys: [], errors: [] }
const hash = bytes => createHash('sha256').update(bytes).digest('hex')
await mkdir('artifacts/product/published', { recursive: true })
for (const file of ['index.html', 'LICENSE', 'ASSET_RIGHTS.md', 'THIRD_PARTY_NOTICES.md', ...ids.map(id => `models/${id}/1.1.0/vehicle.glb`)]) {
  const response = await fetch(new URL(file, base))
  assert.equal(response.status, 200, file)
  const bytes = Buffer.from(await response.arrayBuffer())
  const expected = await readFile(`dist/${file}`)
  // Git normalizes text line endings across the Windows workspace and Linux CI.
  const comparable = data => file.endsWith('.glb') ? data : Buffer.from(data.toString('utf8').replaceAll('\r\n', '\n'))
  assert.equal(hash(comparable(bytes)), hash(comparable(expected)), `Published content differs: ${file}`)
  report.resources.push({ file, bytes: bytes.length, sha256: hash(bytes), comparison: file.endsWith('.glb') ? 'exact bytes' : 'LF-normalized text', status: response.status })
}
const browser = await chromium.launch({ channel: 'chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
  page.on('pageerror', error => report.errors.push(error.message))
  page.on('response', response => { if (response.status() >= 400) report.errors.push(`${response.status()} ${response.url()}`) })
  for (const id of ids) {
    await page.goto(`${base.href}#/vehicles/${id}`)
    await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveAttribute('data-ready', 'true', { timeout: 30_000 })
    await expect(page.getByTestId('renderer-diagnostics')).toHaveCount(0)
    await page.getByRole('button', { name: '全部開啟', exact: true }).click()
    await page.getByRole('switch', { name: id.startsWith('suv') ? '後尾門' : '後車廂', exact: true }).click()
    await expect(page.locator('.door-button small')).toHaveText(['已開啟', '已開啟', '已開啟', '已開啟'])
    await expect(page.locator('.trunk-row small')).toHaveText('已開啟')
    assert.ok(!/外觀設計權利|實車參考重建|品牌識別/.test(await page.locator('body').innerText()))
    await page.getByRole('link', { name: '所有車款', exact: true }).click()
    await expect(page.locator('.vehicle-card')).toHaveCount(5)
    await expect.poll(() => page.locator('.vehicle-card img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0))).toBe(true)
    report.journeys.push({ id, directRoute: true, doorsAndTrunk: true, returnToCollection: true })
  }
  report.browserVersion = browser.version()
  await page.screenshot({ path: 'artifacts/product/published/collection.png', fullPage: true })
  assert.deepEqual(report.errors, [])
  report.status = 'passed'
} finally {
  await browser.close()
  await writeFile('artifacts/product/published/results.json', JSON.stringify(report, null, 2))
}
console.log(JSON.stringify(report))
