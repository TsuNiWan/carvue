import { expect, test, type Page } from '@playwright/test'
import { selectVehicle } from './helpers'

async function ready(page: Page) {
  await page.goto('/#/vehicles/sedan-01')
  await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveAttribute('data-ready', 'true')
  await expect.poll(async () => Number(await page.getByTestId('renderer-diagnostics').getAttribute('data-frames'))).toBeGreaterThan(2)
}

test('WebGL 初始化失敗時提供可讀提示，切車與切情境不產生未處理例外', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, contextId: string, ...args: unknown[]) {
      if (contextId === 'webgl' || contextId === 'webgl2' || contextId === 'experimental-webgl') return null
      return Reflect.apply(original, this, [contextId, ...args])
    } as typeof original
  })
  await page.goto('/#/vehicles/sedan-01')
  const alert = page.getByRole('alert')
  await expect(alert).toContainText('無法啟動 3D 顯示')
  await expect(alert).toContainText('WebGL 2')
  await expect(page.locator('.viewer-status')).toContainText('尚未就緒')
  await expect(page.locator('.viewer-status')).not.toContainText('互動展示已就緒')
  expect(await page.evaluate(() => Boolean(document.createElement('canvas').getContext('2d')))).toBe(true)
  await selectVehicle(page, 'suv-01', false)
  await expect(page.getByRole('heading', { name: '家庭休旅', exact: true })).toBeVisible()
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  await page.getByRole('button', { name: /盲點鄰車/ }).click()
  await expect(page.getByRole('button', { name: '播放情境', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: '俯視', exact: true }).click()
  await page.getByRole('tab', { name: '車輛控制' }).click()
  await selectVehicle(page, 'suv-02', false)
  await expect(alert).toBeVisible()
  await expect(page.locator('.viewer-status')).toContainText('尚未就緒')
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).toBeDisabled()
  expect(errors).toEqual([])
})

test('WebGL context 遺失後繪製及情境停止，visibility 事件不會重新啟動', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await ready(page)
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  await page.getByRole('button', { name: '播放情境', exact: true }).click()
  const progress = page.getByRole('slider', { name: '情境進度' })
  await expect.poll(async () => Number(await progress.inputValue())).toBeGreaterThan(2)
  const canvas = page.getByLabel('車輛 3D 場景', { exact: true })
  const supported = await canvas.evaluate(element => {
    const context = (element as HTMLCanvasElement).getContext('webgl2')
    const extension = context?.getExtension('WEBGL_lose_context')
    if (!extension) return false
    extension.loseContext()
    return true
  })
  expect(supported, '此驗證必須實際觸發 WEBGL_lose_context，不能以略過當作通過').toBe(true)
  await expect(page.getByRole('alert')).toContainText('3D 顯示暫時中斷')
  await expect(canvas).toHaveAttribute('data-ready', 'false')
  await expect(page.locator('.viewer-status')).toContainText('尚未就緒')
  const probe = page.getByTestId('renderer-diagnostics')
  const frames = await probe.getAttribute('data-frames')
  const pausedProgress = await progress.inputValue()
  // Exercise only the page's event guard; no desktop or browser visibility changes.
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
  await page.waitForTimeout(800)
  await expect(probe).toHaveAttribute('data-frames', frames!)
  await expect(progress).toHaveValue(pausedProgress)
  await selectVehicle(page, 'sedan-02', false)
  await page.getByRole('button', { name: '側面', exact: true }).click()
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
  await page.waitForTimeout(800)
  await expect(probe).toHaveAttribute('data-frames', frames!)
  await expect(canvas).toHaveAttribute('data-ready', 'false')
  await expect(page.getByRole('alert')).toBeVisible()
  expect(errors).toEqual([])
})

test('減少動態偏好下車門仍完成開合，視角按鈕與鍵盤仍可使用', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await ready(page)
  const probe = page.getByTestId('renderer-diagnostics')
  await page.getByRole('button', { name: '全部開啟', exact: true }).click()
  await page.getByRole('switch', { name: '後車廂', exact: true }).click()
  await expect.poll(async () => {
    const angles: Record<string, number> = JSON.parse((await probe.getAttribute('data-door-angles'))!)
    return ['frontLeft', 'frontRight', 'rearLeft', 'rearRight', 'trunk'].every(key => Math.abs(angles[key]!) > 0.5)
  }).toBe(true)
  await page.getByRole('button', { name: '全部關閉', exact: true }).click()
  await page.getByRole('switch', { name: '後車廂', exact: true }).click()
  await expect.poll(async () => {
    const angles: Record<string, number> = JSON.parse((await probe.getAttribute('data-door-angles'))!)
    return Object.keys(angles).length === 5 && Object.values(angles).every(value => Math.abs(value) < 0.001)
  }).toBe(true)
  const original = await probe.getAttribute('data-camera')
  await page.getByRole('button', { name: '俯視', exact: true }).click()
  await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(original)
  const topCamera = await probe.getAttribute('data-camera')
  const canvas = page.getByLabel('車輛 3D 場景', { exact: true })
  await canvas.focus()
  await canvas.press('Home')
  await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(topCamera)
  const homeCamera = await probe.getAttribute('data-camera')
  await canvas.press('ArrowRight')
  await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(homeCamera)
})


