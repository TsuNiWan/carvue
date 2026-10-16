import { createHash } from 'node:crypto'
import { expect, test, type Page, type TestInfo } from '@playwright/test'
import { hostEnvironment, measureFrames, models, openVehicle } from './helpers'

async function measureMechanism(page: Page, testInfo: TestInfo, part: string, name: string, target: number) {
  await page.evaluate(({ part, target, name }) => {
    const probe = document.querySelector<HTMLElement>('[data-testid="renderer-diagnostics"]')!
    const result = { part, target, clickedAt: -1, completedAt: -1, samples: [] as { time: number; value: number; status: string }[] }
    const runtime = window as typeof window & { mechanismMeasurement?: typeof result }
    runtime.mechanismMeasurement = result
    document.addEventListener('click', () => { result.clickedAt = performance.now() }, { once: true, capture: true })
    const observer = new MutationObserver(() => {
      if (result.clickedAt < 0) return
      const value = (JSON.parse(probe.dataset.presentation!) as { parts: Record<string, number> }).parts[part]!
      const control = document.querySelector(`[aria-label="${name}"]`)!
      const scope = part === 'trunk' ? control.closest('.trunk-row')! : control
      result.samples.push({ time: performance.now() - result.clickedAt, value, status: scope.querySelector('small')!.textContent! })
      if (value === target) { result.completedAt = performance.now(); observer.disconnect() }
    })
    observer.observe(probe, { attributes: true, attributeFilter: ['data-presentation'] })
  }, { part, target, name })
  let measurement
  try {
    await page.getByRole(part === 'trunk' ? 'switch' : 'button', { name, exact: true }).click()
    await page.waitForFunction(() => (window as typeof window & { mechanismMeasurement: { completedAt: number } }).mechanismMeasurement.completedAt >= 0, undefined, { timeout: 8000 })
    // The diagnostic clock and the 30 Hz Vue presentation can finish on adjacent frames.
    const status = (part === 'trunk' ? page.locator('.trunk-row') : page.getByRole('button', { name, exact: true })).locator('small')
    await expect(status).toHaveText(target ? '已開啟' : '已關閉', { timeout: 500 })
  } finally {
    measurement = await page.evaluate(() => {
      const result = (window as typeof window & { mechanismMeasurement: { clickedAt: number; completedAt: number; samples: { time: number; value: number; status: string }[] } }).mechanismMeasurement
      return { ...result, elapsedMs: result.completedAt - result.clickedAt }
    })
    await testInfo.attach(`${part}-${target}-samples.json`, { body: JSON.stringify(measurement, null, 2), contentType: 'application/json' })
  }
  return measurement
}

async function hotspotProjection(page: Page) {
  return page.locator('[data-hotspot]').evaluateAll(elements => elements.map(element => ({
    id: (element as HTMLElement).dataset.hotspot,
    x: Math.round(element.getBoundingClientRect().x),
    y: Math.round(element.getBoundingClientRect().y),
  })))
}

for (const model of models) for (const preference of ['no-preference', 'reduce'] as const) {
  test(`${model.id} ${preference} 四門及後廂實際開關時長符合 1100／1400ms`, async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: preference })
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === model.modelUrl && response.ok())
    await openVehicle(page, model.id)
    const response = await responsePromise
    const body = await response.body()
    const asset = { url: response.url(), bytes: body.length, sha256: createHash('sha256').update(body).digest('hex') }
    const measurements = []
    try {
      for (const [part, name] of [['frontLeft', '左前門'], ['frontRight', '右前門'], ['rearLeft', '左後門'], ['rearRight', '右後門'], ['trunk', model.rear]]) {
        const expectedMs = part === 'trunk' ? 1400 : 1100
        for (const target of [1, 0]) {
          const result = await measureMechanism(page, testInfo, part!, name!, target)
          measurements.push({ part, target, expectedMs, ...result })
          expect(result.elapsedMs).toBeGreaterThanOrEqual(expectedMs - 100)
          expect(result.elapsedMs).toBeLessThanOrEqual(expectedMs + 250)
          expect(result.samples.filter(sample => sample.value > 0.05 && sample.value < 0.95).length).toBeGreaterThanOrEqual(5)
          expect(result.samples.filter(sample => sample.value > 0 && sample.value < 1).every(sample => sample.status === (target ? '開啟中' : '關閉中'))).toBe(true)
        }
      }
    } finally {
      await testInfo.attach(`${model.id}-${preference}-wallclock.json`, { body: JSON.stringify({ asset, preference, measurements }, null, 2), contentType: 'application/json' })
    }
  })
}

for (const model of models) {
  test(`${model.id} 持續滑鼠拖曳 30 秒至少 45 FPS，原始幀間隔 p95 不超過 50ms`, async ({ page, browser }, testInfo) => {
    test.skip(testInfo.project.name !== 'chrome-1920', '拖曳效能固定以 Chrome 1920×1080 逐車執行')
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === model.modelUrl && response.ok())
    await openVehicle(page, model.id)
    const response = await responsePromise
    const body = await response.body()
    const asset = { url: response.url(), bytes: body.length, sha256: createHash('sha256').update(body).digest('hex') }
    const canvas = await page.getByLabel('車輛 3D 場景', { exact: true }).boundingBox()
    expect(canvas).not.toBeNull()
    const { x, y, width, height } = canvas!
    const before = await page.getByTestId('renderer-diagnostics').getAttribute('data-camera')
    await page.mouse.move(x + width * 0.5, y + height * 0.6)
    await page.mouse.down()
    const measurement = measureFrames(page, 30_000)
    const startedAt = Date.now()
    const pointerMoves: number[] = []
    try {
      while (Date.now() - startedAt < 30_000) {
        const elapsed = Date.now() - startedAt
        await page.mouse.move(x + width * (0.5 + Math.sin(elapsed / 1000 * 1.8) * 0.3), y + height * (0.6 + Math.sin(elapsed / 1000 * 0.9) * 0.13))
        pointerMoves.push(elapsed)
        await page.waitForTimeout(16)
      }
    } finally {
      await page.mouse.up()
    }
    const result = await measurement
    await testInfo.attach(`${model.id}-pointer-drag-30s.json`, {
      body: JSON.stringify({ asset, browserVersion: browser.version(), host: hostEnvironment(), pointerMoves, ...result }, null, 2), contentType: 'application/json',
    })
    expect(pointerMoves.length).toBeGreaterThan(300)
    expect(result.droppedSamples).toBe(0)
    expect(result.meanFPS).toBeGreaterThanOrEqual(45)
    expect(result.p95FrameIntervalMs).toBeLessThanOrEqual(50)
    expect(await page.getByTestId('renderer-diagnostics').getAttribute('data-camera')).not.toBe(before)
    await expect.poll(() => page.locator('[data-hotspot]').count()).toBeGreaterThan(0)
  })
}

test('sedan-01 減少動態的預設視角及鍵盤旋轉會更新熱點投影與遮擋', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await openVehicle(page)
  await expect.poll(() => page.locator('[data-hotspot]').count()).toBeGreaterThan(0)
  for (const view of ['前方', '後方', '側面']) {
    const before = await hotspotProjection(page)
    await page.getByRole('button', { name: view, exact: true }).click()
    await expect.poll(() => hotspotProjection(page)).not.toEqual(before)
  }
  const before = await hotspotProjection(page)
  const canvas = page.getByLabel('車輛 3D 場景', { exact: true })
  await canvas.focus()
  await canvas.press('ArrowRight')
  await expect.poll(() => hotspotProjection(page)).not.toEqual(before)
})

for (const interruption of ['context-loss', 'unmount'] as const) {
  test(`sedan-01 預編譯 pending 的 ${interruption} 會終止 Three 內部輪詢`, async ({ page }, testInfo) => {
    await page.addInitScript(() => {
      const pending = new Set<number>()
      const probe = { active: 0, scheduled: 0, completions: 0 }
      ;(window as typeof window & { compileProbe: typeof probe }).compileProbe = probe
      const schedule = window.setTimeout.bind(window)
      const query = WebGL2RenderingContext.prototype.getProgramParameter
      WebGL2RenderingContext.prototype.getProgramParameter = function (program, parameter) {
        // Keep the real extension pending until its material is disposed.
        if (parameter === 0x91b1) { probe.completions++; return false }
        return query.call(this, program, parameter)
      }
      window.setTimeout = ((handler: TimerHandler, timeout = 0, ...args: unknown[]) => {
        if (typeof handler !== 'function' || handler.name !== 'checkMaterialsReady') return schedule(handler, timeout, ...args)
        const timer = schedule(() => {
          pending.delete(timer)
          probe.active = pending.size
          handler(...args)
        }, timeout)
        pending.add(timer)
        probe.active = pending.size
        probe.scheduled++
        return timer
      }) as typeof window.setTimeout
    })
    await page.goto('/#/vehicles/sedan-01')
    const probe = () => page.evaluate(() => (window as typeof window & { compileProbe: { active: number; scheduled: number; completions: number } }).compileProbe)
    await expect.poll(async () => (await probe()).completions).toBeGreaterThan(0)
    await expect.poll(async () => (await probe()).active).toBeGreaterThan(0)
    expect(await page.getByLabel('車輛 3D 場景', { exact: true }).getAttribute('data-ready')).toBe('false')
    if (interruption === 'context-loss') {
      await page.locator('canvas').evaluate(canvas => (canvas as HTMLCanvasElement).getContext('webgl2')!.getExtension('WEBGL_lose_context')!.loseContext())
      await expect(page.getByTestId('renderer-diagnostics')).toHaveAttribute('data-load-state', 'error')
    } else {
      await page.getByRole('link', { name: '所有車款', exact: true }).click()
      await expect(page.locator('canvas')).toHaveCount(0)
    }
    await expect.poll(async () => (await probe()).active).toBe(0)
    const settled = await probe()
    await page.waitForTimeout(150)
    expect((await probe()).scheduled).toBe(settled.scheduled)
    await testInfo.attach(`precompile-${interruption}.json`, { body: JSON.stringify({ interruption, settled, afterWait: await probe() }, null, 2), contentType: 'application/json' })
  })
}
