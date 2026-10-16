import { expect, test } from '@playwright/test'
import { hostEnvironment, models, openVehicle, selectVehicle } from './helpers'

test('五車互動連續 30 分鐘沒有例外、停止繪製或累積 GPU 資源', async ({ page, browser }, testInfo) => {
  test.skip(process.env.CARVUE_SOAK !== '1' || testInfo.project.name !== 'chrome-1920', '以獨立 test:soak 命令明確選擇 30 分鐘長測')
  test.setTimeout(32 * 60_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await openVehicle(page)
  const probe = page.getByTestId('renderer-diagnostics')
  const read = async () => ({
    frames: Number(await probe.getAttribute('data-frames')),
    geometries: Number(await probe.getAttribute('data-geometries')),
    textures: Number(await probe.getAttribute('data-textures')),
    vehicle: await probe.getAttribute('data-vehicle-id'),
    state: await probe.getAttribute('data-load-state'),
  })
  const baselines: Record<string, { geometries: number; textures: number }> = {}
  const coldBaselines: typeof baselines = {}
  for (const model of models) {
    await selectVehicle(page, model.id)
    await page.waitForTimeout(500)
    const cold = await read()
    coldBaselines[model.id] = { geometries: cold.geometries, textures: cold.textures }
    // Three uploads ADAS geometry only after it has actually been rendered.
    // Compare repeated workloads against the same initialized resource set.
    await page.getByRole('tab', { name: 'ADAS 情境' }).click()
    await page.getByRole('button', { name: '播放情境', exact: true }).click()
    await page.waitForTimeout(2_000)
    await page.getByRole('button', { name: '重設展示', exact: true }).click()
    await page.getByRole('tab', { name: '車輛控制' }).click()
    await page.waitForTimeout(500)
    const snapshot = await read()
    baselines[model.id] = { geometries: snapshot.geometries, textures: snapshot.textures }
  }
  const startedAt = new Date().toISOString()
  const start = Date.now()
  let previousFrames = 0
  let cycle = 0
  const samples: ({ elapsedMs: number; cycle: number } & Awaited<ReturnType<typeof read>>)[] = []
  try {
    while (Date.now() - start < 30 * 60_000) {
      const model = models[cycle % models.length]!
      await selectVehicle(page, model.id)
      await page.getByRole('button', { name: '全部開啟', exact: true }).click()
      await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
      await page.getByRole('switch', { name: model.rear, exact: true }).click()
      await page.getByRole('button', { name: cycle % 2 ? '後方' : '側面', exact: true }).click()
      await page.waitForTimeout(1_200)
      await page.getByRole('tab', { name: 'ADAS 情境' }).click()
      await page.getByRole('button', { name: '播放情境', exact: true }).click()
      await page.waitForTimeout(2_000)
      await page.getByRole('button', { name: '重設展示', exact: true }).click()
      await page.getByRole('tab', { name: '車輛控制' }).click()
      await page.waitForTimeout(500)
      const snapshot = await read()
      samples.push({ elapsedMs: Date.now() - start, cycle, ...snapshot })
      expect(snapshot.state).toBe('ready')
      expect(snapshot.frames).toBeGreaterThan(previousFrames)
      expect(snapshot.geometries).toBe(baselines[model.id]!.geometries)
      expect(snapshot.textures).toBe(baselines[model.id]!.textures)
      expect(errors).toEqual([])
      previousFrames = snapshot.frames
      cycle++
    }
  } finally {
    await testInfo.attach('soak-30m.json', { body: JSON.stringify({ requestedDurationMs: 30 * 60_000, elapsedMs: Date.now() - start, startedAt, endedAt: new Date().toISOString(), browserVersion: browser.version(), host: hostEnvironment(), coldBaselines, baselines, samples, errors }, null, 2), contentType: 'application/json' })
  }
  expect(Date.now() - start).toBeGreaterThanOrEqual(30 * 60_000)
  expect(samples.length).toBeGreaterThanOrEqual(100)
})
