import { expect, test } from '@playwright/test'
import { createHash } from 'node:crypto'
import { hostEnvironment, measureFrames, models, openVehicle, range } from './helpers'

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name !== 'chrome-1920', '資產與效能基準固定以 Chrome 1920×1080 逐車執行')
})

for (const model of models) {
  test(`${model.id} 模型及外部相依資源合計不超過 12 MiB`, async ({ request }, testInfo) => {
    const response = await request.get(model.modelUrl)
    expect(response.ok(), model.modelUrl).toBe(true)
    const body = await response.body()
    expect(body.subarray(0, 4).toString()).toBe('glTF')
    expect(body.readUInt32LE(4)).toBe(2)
    expect(body.readUInt32LE(8)).toBe(body.byteLength)
    expect(body.readUInt32LE(16)).toBe(0x4e4f534a)
    const json = JSON.parse(body.subarray(20, 20 + body.readUInt32LE(12)).toString()) as {
      buffers?: { uri?: string }[]; images?: { uri?: string }[]
    }
    const externalUrls = [...new Set([...(json.buffers ?? []), ...(json.images ?? [])]
      .flatMap(item => item.uri && !item.uri.startsWith('data:') ? [new URL(item.uri, response.url()).href] : []))]
    const resources = [{ url: response.url(), bytes: body.byteLength }]
    for (const url of externalUrls) {
      const dependency = await request.get(url)
      expect(dependency.ok(), url).toBe(true)
      resources.push({ url, bytes: (await dependency.body()).byteLength })
    }
    const totalBytes = resources.reduce((sum, resource) => sum + resource.bytes, 0)
    const asset = { url: response.url(), bytes: body.byteLength, sha256: createHash('sha256').update(body).digest('hex') }
    await testInfo.attach(`${model.id}-asset-size.json`, { body: JSON.stringify({ vehicle: model.id, asset, limitBytes: 12 * 1024 * 1024, totalBytes, resources }, null, 2), contentType: 'application/json' })
    expect(totalBytes).toBeLessThanOrEqual(12 * 1024 * 1024)
  })

  test(`${model.id} 25 Mbps／80ms 冷載至可操作首幀不超過 8 秒`, async ({ page, context, browser }, testInfo) => {
    const session = await context.newCDPSession(page)
    await session.send('Network.enable')
    await session.send('Network.setCacheDisabled', { cacheDisabled: true })
    await session.send('Network.emulateNetworkConditions', { offline: false, latency: 80, downloadThroughput: 25_000_000 / 8, uploadThroughput: 25_000_000 / 8 })
    // Timestamp readiness in the page, without adding later assertion round-trip latency.
    await page.addInitScript(vehicleId => {
      let scheduled = false
      const ready = () => {
        const probe = document.querySelector<HTMLElement>('[data-testid="renderer-diagnostics"]')
        const canvas = document.querySelector<HTMLElement>('canvas[aria-label="車輛 3D 場景"]')
        const control = document.querySelector<HTMLButtonElement>('[role="switch"][aria-label="頭燈與尾燈"]')
        return probe?.dataset.vehicleId === vehicleId && probe.dataset.loadState === 'ready' && canvas?.dataset.ready === 'true' && control?.matches(':enabled')
      }
      const observer = new MutationObserver(() => {
        if (scheduled || !ready()) return
        scheduled = true
        requestAnimationFrame(() => {
          if (ready()) { performance.mark('carvue-test-ready'); observer.disconnect() }
          else scheduled = false
        })
      })
      observer.observe(document, { subtree: true, childList: true, attributes: true,
        attributeFilter: ['data-vehicle-id', 'data-load-state', 'data-ready', 'disabled'] })
    }, model.id)
    const modelResponse = page.waitForResponse(response => new URL(response.url()).pathname === model.modelUrl && response.ok())
    await page.goto(`/#/vehicles/${model.id}`)
    const probe = page.getByTestId('renderer-diagnostics')
    await expect(probe).toHaveAttribute('data-vehicle-id', model.id)
    await expect(probe).toHaveAttribute('data-load-state', 'ready')
    await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveAttribute('data-ready', 'true')
    await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).toBeEnabled()
    await expect.poll(() => page.evaluate(() => performance.getEntriesByName('carvue-test-ready').length)).toBe(1)
    const measurement = await page.evaluate(() => ({
      navigationToReadyMs: performance.getEntriesByName('carvue-test-ready')[0]!.startTime,
      assertionCompletedAtMs: performance.now(),
      navigation: performance.getEntriesByType('navigation').map(entry => entry.toJSON()),
      resources: performance.getEntriesByType('resource').map(entry => entry.toJSON()),
      phases: performance.getEntriesByType('mark').filter(entry => entry.name.startsWith('carvue-load:')).map(entry => entry.toJSON()),
    }))
    const response = await modelResponse
    const body = await response.body()
    const asset = { url: response.url(), bytes: body.byteLength, sha256: createHash('sha256').update(body).digest('hex') }
    await testInfo.attach(`${model.id}-cold-load.json`, {
      body: JSON.stringify({ vehicle: model.id, asset, network: { downloadMbps: 25, latencyMs: 80, cacheDisabled: true }, browserVersion: browser.version(), host: hostEnvironment(), ...measurement }, null, 2),
      contentType: 'application/json',
    })
    expect(measurement.navigationToReadyMs).toBeLessThanOrEqual(8_000)
    expect(measurement.resources.some(entry => String(entry.name).includes(model.modelUrl))).toBe(true)
    await session.detach()
  })

  test(`${model.id} 連續互動 30 秒至少 45 FPS，原始幀間隔 p95 不超過 50ms`, async ({ page, browser }, testInfo) => {
    const modelResponse = page.waitForResponse(response => new URL(response.url()).pathname === model.modelUrl && response.ok())
    await openVehicle(page, model.id)
    const response = await modelResponse
    const body = await response.body()
    const asset = { url: response.url(), bytes: body.byteLength, sha256: createHash('sha256').update(body).digest('hex') }
    const measurement = measureFrames(page, 30_000)
    const startedAt = Date.now()
    const actions: { action: string; elapsedMs: number }[] = []
    const waitUntil = async (offset: number) => {
      const remaining = startedAt + offset - Date.now()
      if (remaining > 0) await page.waitForTimeout(remaining)
    }
    const steps = [
      { offset: 0, action: 'open-doors', run: () => page.getByRole('button', { name: '全部開啟', exact: true }).click() },
      { offset: 3_000, action: 'headlights', run: () => page.getByRole('switch', { name: '頭燈與尾燈' }).click() },
      { offset: 6_000, action: 'rear-opening', run: () => page.getByRole('switch', { name: model.rear, exact: true }).click() },
      { offset: 9_000, action: 'rear-view', run: () => page.getByRole('button', { name: '後方', exact: true }).click() },
      { offset: 12_000, action: 'steer', run: () => range(page.getByRole('slider', { name: '前輪轉向角度' }), 30) },
      { offset: 15_000, action: 'close-doors', run: () => page.getByRole('button', { name: '全部關閉', exact: true }).click() },
      { offset: 18_000, action: 'adas-play', run: async () => { await page.getByRole('tab', { name: 'ADAS 情境' }).click(); await page.getByRole('button', { name: '播放情境', exact: true }).click() } },
      { offset: 22_000, action: 'blindspot-play', run: async () => { await page.getByRole('button', { name: /盲點鄰車/ }).click(); await page.getByRole('button', { name: '雙黃燈', exact: true }).click(); await page.getByRole('button', { name: '播放情境', exact: true }).click() } },
      { offset: 26_000, action: 'parking-play', run: async () => { await page.getByRole('button', { name: /倒車障礙物/ }).click(); await page.getByRole('button', { name: '播放情境', exact: true }).click() } },
    ]
    for (const step of steps) {
      await waitUntil(step.offset)
      await step.run()
      actions.push({ action: step.action, elapsedMs: Date.now() - startedAt })
    }
    const result = await measurement
    await testInfo.attach(`${model.id}-performance-30s.json`, { body: JSON.stringify({ vehicle: model.id, asset, browserVersion: browser.version(), host: hostEnvironment(), actions, ...result }, null, 2), contentType: 'application/json' })
    expect(result.elapsedMs).toBeGreaterThanOrEqual(30_000)
    expect(result.elapsedMs).toBeLessThan(35_000)
    expect(result.viewport).toMatchObject({ width: 1920, height: 1080 })
    expect(result.samples.every(sample => sample.vehicle === model.id)).toBe(true)
    expect(result.droppedSamples).toBe(0)
    expect(result.frameIntervalsMs.length).toBeGreaterThan(1_000)
    expect(result.meanFPS).toBeGreaterThanOrEqual(45)
    expect(result.p95FrameIntervalMs).toBeLessThanOrEqual(50)
    expect(actions.every(action => action.elapsedMs < 30_000)).toBe(true)
  })
}
