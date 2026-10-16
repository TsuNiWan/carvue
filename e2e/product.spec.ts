import { expect, test } from '@playwright/test'
import { models, openVehicle, presentation, range, selectVehicle, waitForVehicle } from './helpers'

test('總覽提供五車網址入口且不建立 3D 場景', async ({ page }) => {
  await page.goto('/#/vehicles')
  await expect(page.getByRole('heading', { level: 1, name: '找到讓你停下目光的那一款。' })).toBeVisible()
  for (const model of models) await expect(page.getByTestId(`select-${model.id}`)).toHaveAttribute('href', `#/vehicles/${model.id}`)
  await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveCount(0)
})

test('直接車款網址可重新整理及返回總覽', async ({ page }) => {
  await page.goto('/#/vehicles')
  await page.getByTestId('select-sedan-01').click()
  await waitForVehicle(page, 'sedan-01')
  await expect(page).toHaveURL(/#\/vehicles\/sedan-01$/)
  await page.reload()
  await waitForVehicle(page, 'sedan-01')
  await expect(page).toHaveTitle(/都會轎車.*CARVUE/)
  await page.getByRole('link', { name: '所有車款', exact: true }).click()
  await expect(page).toHaveURL(/#\/vehicles$/)
  await page.goBack()
  await waitForVehicle(page, 'sedan-01')
})

test('未知車款提供明確提示與總覽入口', async ({ page }) => {
  await page.goto('/#/vehicles/not-a-real-model')
  await expect(page.getByRole('heading', { name: '找不到這款車', exact: true })).toBeVisible()
  await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: '所有車款', exact: true }).click()
  await expect(page).toHaveURL(/#\/vehicles$/)
})

test('窄螢幕保留車款資訊與桌機提示，不建立 WebGL', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const modelRequests: string[] = []
  page.on('request', request => { if (request.url().includes('.glb')) modelRequests.push(request.url()) })
  await page.goto('/#/vehicles/sedan-01')
  await expect(page.getByRole('heading', { name: '都會轎車', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '請在桌機開啟完整 3D 體驗', exact: true })).toBeVisible()
  await expect(page.locator('canvas')).toHaveCount(0)
  expect(modelRequests).toEqual([])
})

test('模型載入失敗時禁用車控，重新載入可恢復正確模型', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  let failed = false
  const modelUrl = models.find(model => model.id === 'sedan-01')!.modelUrl
  await page.route(`**${modelUrl}`, async route => {
    if (!failed) { failed = true; await route.fulfill({ status: 503, body: 'Temporarily unavailable' }) }
    else await route.continue()
  })
  await page.goto('/#/vehicles/sedan-01')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByTestId('renderer-diagnostics')).toHaveAttribute('data-load-state', 'error')
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).toBeDisabled()
  await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveAttribute('data-ready', 'false')
  await page.getByRole('button', { name: '重新載入模型', exact: true }).click()
  await waitForVehicle(page, 'sedan-01')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).toBeEnabled()
  expect(failed).toBe(true)
  expect(errors).toEqual([])
})

test('延遲的舊模型請求不會覆蓋快速切換後的車款', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await openVehicle(page)
  let release!: () => void
  let entered!: () => void
  let completed!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  const requested = new Promise<void>(resolve => { entered = resolve })
  const settled = new Promise<void>(resolve => { completed = resolve })
  const delayedModel = models.find(model => model.id === 'suv-01')!
  await page.route(`**${delayedModel.modelUrl}`, async route => {
    entered()
    await gate
    try {
      await route.continue()
    } catch (error) {
      if (!route.request().failure()?.errorText.includes('ERR_ABORTED')) throw error
    } finally {
      completed()
    }
  })
  await selectVehicle(page, 'suv-01', false)
  await requested
  await expect(page.getByTestId('renderer-diagnostics')).toHaveAttribute('data-load-state', 'loading')
  await selectVehicle(page, 'sedan-02')
  release()
  await settled
  await page.waitForTimeout(600)
  await waitForVehicle(page, 'sedan-02')
  await expect(page).toHaveURL(/#\/vehicles\/sedan-02$/)
  await expect(page.getByRole('heading', { level: 1, name: '流線轎車', exact: true })).toBeVisible()
  expect(errors).toEqual([])
})

test('車門及後廂顯示中間狀態，動畫中反向會回到關閉', async ({ page }) => {
  await openVehicle(page)
  for (const part of [
    { id: 'frontLeft' as const, control: page.getByRole('button', { name: '左前門', exact: true }) },
    { id: 'trunk' as const, control: page.getByRole('switch', { name: '後車廂', exact: true }) },
  ]) {
    await part.control.click()
    await expect.poll(async () => {
      const value = (await presentation(page)).parts[part.id]
      return value > 0.05 && value < 0.95
    }, { intervals: [30], timeout: 2_000 }).toBe(true)
    const intermediate = (await presentation(page)).parts[part.id]
    expect(intermediate).toBeGreaterThan(0)
    expect(intermediate).toBeLessThan(1)
    await part.control.click()
    await expect.poll(async () => (await presentation(page)).parts[part.id], { intervals: [50] }).toBeLessThan(0.01)
    const angles = JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute('data-door-angles'))!) as Record<string, number>
    expect(Math.abs(angles[part.id]!)).toBeLessThan(0.01)
  }
})

test('頭尾燈具備中間亮度，熱點與面板狀態一致', async ({ page }, testInfo) => {
  await openVehicle(page)
  // Capture every DOM update inside the browser; driver round trips can miss a 250 ms fade.
  await page.evaluate(() => {
    const probe = document.querySelector<HTMLElement>('[data-testid="renderer-diagnostics"]')!
    const observer = new MutationObserver(() => {
      const value = JSON.parse(probe.dataset.presentation!).headlights as number
      const lights = JSON.parse(probe.dataset.lights!) as { head: number; tail: number }
      const status = document.querySelector('[aria-label="頭燈與尾燈"]')!.closest('.switch-row')!.querySelector('small')!.textContent
      performance.mark('carvue-test-lamp', { detail: { value, ...lights, status } })
      if (value === 1) observer.disconnect()
    })
    observer.observe(probe, { attributes: true, attributeFilter: ['data-presentation'] })
  })
  await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
  await expect.poll(async () => (await presentation(page)).headlights).toBe(1)
  const samples = await page.evaluate(() => performance.getEntriesByName('carvue-test-lamp').map(entry => ({
    time: entry.startTime, ...(entry as PerformanceMark).detail as { value: number; head: number; tail: number; status: string },
  })))
  await testInfo.attach('headlight-fade.json', { body: JSON.stringify(samples, null, 2), contentType: 'application/json' })
  const intermediate = samples.filter(sample => sample.value > 0 && sample.value < 1)
  expect(intermediate.length, '必須觀察到實際中間亮度，僅完成開關不能證明漸變').toBeGreaterThan(0)
  for (const sample of intermediate) {
    expect(sample.head).toBeCloseTo(sample.value * 3.2)
    expect(sample.tail).toBeCloseTo(sample.value * 2.2)
    expect(sample.status).toBe('點亮中')
  }
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' }).locator('..').locator('small')).toHaveText('已點亮')
  await page.getByRole('button', { name: '重設展示', exact: true }).click()
  const hotspot = page.getByRole('button', { name: '左前門熱點', exact: true })
  await expect(hotspot).toBeVisible()
  await hotspot.click()
  await expect(page.getByRole('button', { name: '左前門', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect.poll(async () => (await presentation(page)).parts.frontLeft).toBe(1)
})

test('重設視角保留車控，重設展示保留情境種類並恢復全部狀態', async ({ page }) => {
  await openVehicle(page)
  await page.getByRole('button', { name: '左前門', exact: true }).click()
  await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
  await range(page.getByRole('slider', { name: '前輪轉向角度' }), 24)
  await page.getByRole('button', { name: '俯視', exact: true }).click()
  await page.getByRole('button', { name: '重設視角', exact: true }).click()
  await expect(page.getByRole('button', { name: '左前門', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).toBeChecked()
  await expect(page.getByRole('slider', { name: '前輪轉向角度' })).toHaveValue('24')
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  await page.getByRole('button', { name: /盲點鄰車/ }).click()
  await page.getByRole('button', { name: '右側', exact: true }).click()
  await page.getByRole('checkbox', { name: 'LiDAR', exact: true }).check()
  await page.getByRole('checkbox', { name: '雷達', exact: true }).uncheck()
  await range(page.getByRole('slider', { name: '情境進度' }), 40)
  await page.getByRole('button', { name: '重設展示', exact: true }).click()
  await expect(page.getByRole('tab', { name: 'ADAS 情境' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('button', { name: /盲點鄰車/ })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: '左側', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('slider', { name: '情境進度' })).toHaveValue('0')
  await expect(page.getByRole('button', { name: '播放情境', exact: true })).toBeVisible()
  await expect(page.getByRole('checkbox', { name: 'LiDAR', exact: true })).not.toBeChecked()
  for (const sensor of ['雷達', '攝影機', '超音波']) await expect(page.getByRole('checkbox', { name: sensor, exact: true })).toBeChecked()
  await page.getByRole('tab', { name: '車輛控制' }).click()
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).not.toBeChecked()
  await expect(page.getByRole('slider', { name: '前輪轉向角度' })).toHaveValue('0')
  await expect.poll(async () => Object.values((await presentation(page)).parts).every(value => value === 0)).toBe(true)
  await expect(page).toHaveURL(/#\/vehicles\/sedan-01$/)
})
