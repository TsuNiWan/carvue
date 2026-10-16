import { createHash } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { hostEnvironment, models, openVehicle, presentation } from './helpers'

for (const model of models) test(`${model.id} 同版 WebGL 造型與開合審查證據`, async ({ page, browser, request }, testInfo) => {
  test.skip(testInfo.project.name !== 'chrome-1920', '造型證據以 Chrome 1920×1080 固定取景；功能另做四環境回歸')
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const modelResponse = page.waitForResponse(response => new URL(response.url()).pathname === model.modelUrl && response.ok())
  await openVehicle(page, model.id)
  const response = await modelResponse
  const body = await response.body()
  const sha256 = createHash('sha256').update(body).digest('hex')
  const manifestResponse = await request.get(model.manifestUrl)
  expect(manifestResponse.ok()).toBe(true)
  const manifest = await manifestResponse.json()
  const directory = path.resolve(`artifacts/product/vehicle-review/${model.id}`, sha256.slice(0, 12))
  await mkdir(directory, { recursive: true })
  await page.getByRole('button', { name: '關閉操作提示', exact: true }).click()
  const captures: object[] = []

  async function capture(name: string, view: string, hideHotspots = true, yawSteps = 0) {
    await page.getByRole('button', { name: view, exact: true }).click()
    // Let the documented 400 ms camera motion finish before capturing geometry.
    await page.waitForTimeout(550)
    for (let step = 0; step < yawSteps; step++) await page.getByLabel('車輛 3D 場景', { exact: true }).press('ArrowLeft')
    if (yawSteps) await page.waitForTimeout(100)
    const filename = `${name}.png`
    await page.screenshot({ path: path.join(directory, filename), fullPage: true,
      style: hideHotspots ? '.vehicle-hotspot { visibility: hidden !important; }' : undefined })
    captures.push({ filename, view, yawSteps, hideHotspots, presentation: await presentation(page),
      camera: JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute('data-camera')) ?? '[]') })
    await testInfo.attach(filename, { path: path.join(directory, filename), contentType: 'image/png' })
  }

  await capture('01-product-lights-off', '自由')
  await capture('02-front-lights-off', '前方')
  await capture('03-rear-lights-off', '後方')
  await capture('03b-rear-quarter-lights-off', '後方', true, 6)
  await capture('04-side', '側面')
  await capture('05-high-view', '俯視')
  for (let angle = 0; angle < 8; angle++) await capture(`closed-${angle * 45}`, '前方', true, Math.round(angle * Math.PI / 4 / 0.12))
  await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
  await expect.poll(async () => (await presentation(page)).headlights).toBe(1)
  await capture('06-product-lights-on', '自由')
  await capture('07-front-lights-on', '前方')
  await capture('08-rear-lights-on', '後方')
  await page.getByRole('button', { name: '全部開啟', exact: true }).click()
  await page.getByRole('switch', { name: model.rear, exact: true }).click()
  await expect.poll(async () => Object.values((await presentation(page)).parts).every(value => value === 1)).toBe(true)
  await capture('09-open-product', '自由')
  await capture('10-open-rear', '後方')
  await capture('10b-open-rear-quarter', '後方', true, 6)
  await capture('11-open-high', '俯視')
  await page.getByRole('button', { name: '重設展示', exact: true }).click()
  await expect.poll(async () => Object.values((await presentation(page)).parts).every(value => value === 0)).toBe(true)
  await capture('12-interactive-hotspots', '自由', false)
  expect(errors).toEqual([])
  const report = { capturedAt: new Date().toISOString(), vehicleId: model.id, asset: { sha256, bytes: body.length },
    manifest, browserVersion: browser.version(), host: hostEnvironment(), viewport: page.viewportSize(), captures, errors,
    visualApproval: 'Manual inspection required; successful capture is not visual approval.' }
  await writeFile(path.join(directory, 'review.json'), JSON.stringify(report, null, 2))
  await testInfo.attach('review.json', { path: path.join(directory, 'review.json'), contentType: 'application/json' })
})
