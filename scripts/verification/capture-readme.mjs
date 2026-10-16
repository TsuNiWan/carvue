import { mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { chromium, expect } from '@playwright/test'

const base = process.env.CARVUE_BASE_URL ?? 'http://127.0.0.1:5173/'
const output = 'docs/images'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const records = []
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const capture = async name => {
    const bytes = await page.screenshot({ path: `${output}/${name}.png`, fullPage: true })
    records.push({ name, sha256: createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length })
  }
  await page.goto(`${base}#/vehicles`)
  await expect(page.locator('.vehicle-card')).toHaveCount(5)
  await page.locator('img').evaluateAll(async images => {
    images.forEach(image => { image.loading = 'eager' })
    await Promise.all(images.map(image => image.decode()))
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  })
  await capture('collection')
  await page.getByTestId('select-sedan-01').click()
  await expect(page.locator('canvas')).toHaveAttribute('data-ready', 'true', { timeout: 20_000 })
  await page.getByRole('button', { name: '關閉操作提示', exact: true }).click()
  await page.waitForTimeout(500)
  await capture('showroom')
  await page.getByRole('button', { name: '全部開啟', exact: true }).click()
  await page.getByRole('switch', { name: '後車廂', exact: true }).click()
  await page.waitForTimeout(1600)
  await capture('open-parts')
  await page.getByRole('button', { name: '重設展示', exact: true }).click()
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  await page.getByRole('slider', { name: '情境進度' }).fill('50')
  await page.getByRole('slider', { name: '情境進度' }).dispatchEvent('input')
  await page.waitForTimeout(1600)
  await capture('safety')
  expect(errors).toEqual([])
  await writeFile('docs/evidence/readme-capture.json', JSON.stringify({ browser: browser.version(), viewport: page.viewportSize(), records, errors }, null, 2))
} finally { await browser.close() }
