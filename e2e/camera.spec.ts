import { expect, test } from '@playwright/test'
import { openVehicle } from './helpers'

test('預設視角動畫中按下並拖曳，滑鼠立即接管鏡頭', async ({ page }) => {
  await openVehicle(page)
  const canvas = page.getByLabel('車輛 3D 場景', { exact: true })
  const box = (await canvas.boundingBox())!
  const start = { x: box.x + box.width * 0.22, y: box.y + box.height * 0.72 }
  await page.mouse.move(start.x, start.y)
  await page.getByRole('button', { name: '後方', exact: true }).click()
  await page.mouse.move(start.x, start.y)
  await page.mouse.down()
  await expect(page.getByRole('button', { name: '自由', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.mouse.move(start.x + box.width * 0.16, start.y, { steps: 6 })
  await page.mouse.up()
  await page.waitForTimeout(500)
  const camera: number[] = JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute('data-camera'))!)
  expect(Math.abs(camera[0]!)).toBeGreaterThan(0.3)
  await expect(page.getByRole('button', { name: '後方', exact: true })).toHaveAttribute('aria-pressed', 'false')
})

test('頁面隱藏時暫停情境與繪製，恢復後情境保持暫停', async ({ page }) => {
  await openVehicle(page)
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  await page.getByRole('button', { name: '播放情境', exact: true }).click()
  const progress = page.getByRole('slider', { name: '情境進度' })
  await expect.poll(async () => Number(await progress.inputValue())).toBeGreaterThan(2)
  // Exercise the DOM visibility contract without changing the user's desktop.
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  const probe = page.getByTestId('renderer-diagnostics')
  const frames = await probe.getAttribute('data-frames')
  const paused = await progress.inputValue()
  await page.waitForTimeout(350)
  await expect(probe).toHaveAttribute('data-frames', frames!)
  await expect(progress).toHaveValue(paused)
  await page.evaluate(() => {
    Reflect.deleteProperty(document, 'hidden')
    for (let event = 0; event < 3; event++) document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect.poll(() => probe.getAttribute('data-frames')).not.toBe(frames)
  await expect(page.getByRole('button', { name: '播放情境', exact: true })).toBeVisible()
  await expect(progress).toHaveValue(paused)
})
