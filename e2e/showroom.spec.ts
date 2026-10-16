import { expect, test } from '@playwright/test'
import { diagnostics, doors, models, openVehicle, range, selectVehicle } from './helpers'

test.beforeEach(async ({ page }) => {
  await openVehicle(page)
})

test('五車皆有實際開合鉸鏈，切車會清除先前操作', async ({ page }) => {
  for (const model of models) {
    await selectVehicle(page, model.id)
    await expect(page.getByRole('heading', { level: 1, name: model.name, exact: true })).toBeVisible()
    await expect(page.getByTestId('renderer-diagnostics')).toHaveAttribute('data-vehicle-id', model.id)
    await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).not.toBeChecked()
    await expect(page.getByRole('slider', { name: '前輪轉向角度' })).toHaveValue('0')
    for (const label of doors) {
      const button = page.getByRole('button', { name: label, exact: true })
      await expect(button).toHaveAttribute('aria-pressed', 'false')
      await button.click()
    }
    await page.getByRole('switch', { name: model.rear, exact: true }).click()
    await expect.poll(async () => {
      const angles = await diagnostics(page, 'data-door-angles')
      return ['frontLeft', 'frontRight', 'rearLeft', 'rearRight', 'trunk'].every(key => Math.abs(angles[key] ?? 0) > 0.9)
    }).toBe(true)
    await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
    await range(page.getByRole('slider', { name: '前輪轉向角度' }), 24)
  }
  await page.getByRole('button', { name: '重設展示' }).click()
  await expect.poll(async () => Object.values(await diagnostics(page, 'data-door-angles')).every(angle => Math.abs(angle) < 0.01)).toBe(true)
  await expect(page.getByRole('slider', { name: '前輪轉向角度' })).toHaveValue('0')
  await expect(page.getByRole('switch', { name: '頭燈與尾燈' })).not.toBeChecked()
})

test('照明與方向燈驅動燈組，前輪雙向轉動且門動畫可反向', async ({ page }) => {
  await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
  await expect.poll(async () => (await diagnostics(page, 'data-lights')).head).toBeGreaterThan(1)
  await expect.poll(async () => (await diagnostics(page, 'data-lights')).tail).toBeGreaterThan(1)
  await page.getByRole('switch', { name: '頭燈與尾燈' }).click()
  await expect.poll(async () => (await diagnostics(page, 'data-lights')).head).toBeLessThan(0.2)
  for (const signal of [{ label: '左轉', key: 'left', opposite: 'right' }, { label: '右轉', key: 'right', opposite: 'left' }]) {
    await page.getByRole('button', { name: signal.label, exact: true }).click()
    await expect.poll(async () => (await diagnostics(page, 'data-lights'))[signal.key]).toBeGreaterThan(1)
    await expect.poll(async () => (await diagnostics(page, 'data-lights'))[signal.opposite]).toBeLessThan(0.02)
    await expect.poll(async () => (await diagnostics(page, 'data-lights'))[signal.key]).toBeLessThan(0.02)
  }
  await page.getByRole('button', { name: '雙黃燈', exact: true }).click()
  await expect.poll(async () => {
    const lights = await diagnostics(page, 'data-lights')
    return lights.left > 1 && lights.right > 1
  }).toBe(true)
  await page.getByRole('button', { name: '關閉', exact: true }).click()
  await expect.poll(async () => {
    const lights = await diagnostics(page, 'data-lights')
    return lights.left === 0 && lights.right === 0
  }).toBe(true)
  for (const angle of [-30, 30]) {
    await range(page.getByRole('slider', { name: '前輪轉向角度' }), angle)
    await expect.poll(async () => {
      const wheels: number[] = JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute('data-steering')) ?? '[]')
      return wheels.length === 2 && wheels.every(value => Math.abs(value + angle * Math.PI / 180) < 0.02)
    }).toBe(true)
  }
  await page.getByRole('button', { name: '回正', exact: true }).click()
  await expect(page.getByRole('slider', { name: '前輪轉向角度' })).toHaveValue('0')
  await page.getByRole('button', { name: '左前門', exact: true }).click()
  await expect.poll(async () => Math.abs((await diagnostics(page, 'data-door-angles')).frontLeft)).toBeGreaterThan(0.1)
  await page.getByRole('button', { name: '左前門', exact: true }).click()
  await expect.poll(async () => Math.abs((await diagnostics(page, 'data-door-angles')).frontLeft)).toBeLessThan(0.01)
  await page.getByRole('button', { name: '全部開啟', exact: true }).click()
  for (const label of doors) await expect(page.getByRole('button', { name: label, exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: '全部關閉', exact: true }).click()
  await expect.poll(async () => Object.values(await diagnostics(page, 'data-door-angles')).every(angle => Math.abs(angle) < 0.01)).toBe(true)
})

test('三情境警示可重現，播放暫停與前後拖曳一致', async ({ page }) => {
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  const progress = page.getByRole('slider', { name: '情境進度' })
  const status = page.getByRole('status')
  await expect(status).toContainText('前方區域正常')
  await range(progress, 30)
  await expect(status).toContainText('偵測到行人')
  await range(progress, 50)
  await expect(status).toContainText('行人進入車前區域')
  await page.getByRole('checkbox', { name: '攝影機', exact: true }).uncheck()
  await expect(status).toContainText('行人進入車前區域')
  await range(progress, 0)
  await expect(status).toContainText('前方區域正常')
  await page.getByRole('button', { name: '播放情境', exact: true }).click()
  await expect.poll(async () => Number(await progress.inputValue())).toBeGreaterThan(2)
  await page.getByRole('button', { name: '暫停情境', exact: true }).click()
  const paused = await progress.inputValue()
  await page.waitForTimeout(350)
  await expect(progress).toHaveValue(paused)
  await page.getByRole('button', { name: '播放情境', exact: true }).click()
  await range(progress, 50)
  await expect(page.getByRole('button', { name: '播放情境', exact: true })).toBeVisible()
  await expect(status).toContainText('行人進入車前區域')
  await page.getByRole('button', { name: /盲點鄰車/ }).click()
  await expect(progress).toHaveValue('0')
  await range(progress, 40)
  await expect(status).toContainText('左側盲點有車')
  await page.getByRole('button', { name: '右轉', exact: true }).click()
  await expect(status).toContainText('左側盲點有車')
  await page.getByRole('button', { name: '左轉', exact: true }).click()
  await expect(status).toContainText('左側變換車道風險')
  await page.getByRole('button', { name: '右側', exact: true }).click()
  await expect(status).toContainText('右側盲點有車')
  await page.getByRole('button', { name: '雙黃燈', exact: true }).click()
  await expect(status).toContainText('右側變換車道風險')
  await page.getByRole('button', { name: '倒車障礙物', exact: false }).click()
  await range(progress, 0)
  await expect(status).toContainText('後方距離充足')
  await range(progress, 70)
  await expect(status).toContainText('注意後方障礙物')
  await range(progress, 100)
  await expect(status).toContainText('停止：障礙物過近')
  await page.getByRole('button', { name: '重新播放', exact: true }).click()
  await expect.poll(async () => Number(await progress.inputValue())).toBeLessThan(50)
  await page.getByRole('button', { name: '重設情境', exact: true }).click()
  await expect(progress).toHaveValue('0')
  await page.getByRole('button', { name: '播放情境', exact: true }).click()
  await page.getByRole('tab', { name: '車輛控制' }).click()
  await page.getByRole('tab', { name: 'ADAS 情境' }).click()
  await expect(page.getByRole('button', { name: '播放情境', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '重設展示' }).click()
  await expect(progress).toHaveValue('0')
})

test('桌機布局不溢出，滑鼠、視角按鈕與鍵盤實際改變攝影機', async ({ page }) => {
  const canvas = page.getByLabel('車輛 3D 場景', { exact: true })
  const probe = page.getByTestId('renderer-diagnostics')
  const before = await probe.getAttribute('data-camera')
  const box = (await canvas.boundingBox())!
  await page.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.55)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width * 0.75, box.y + box.height * 0.55, { steps: 12 })
  await page.mouse.up()
  await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(before)
  const dragged = await probe.getAttribute('data-camera')
  await page.mouse.wheel(0, -240)
  await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(dragged)
  for (const name of ['前方', '後方', '側面', '俯視']) {
    const current = await probe.getAttribute('data-camera')
    await page.getByRole('button', { name, exact: true }).click()
    await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(current)
  }
  await page.getByRole('button', { name: '重設視角', exact: true }).click()
  await page.waitForTimeout(900)
  const keyboardCamera = await probe.getAttribute('data-camera')
  await canvas.focus()
  await canvas.press('ArrowLeft')
  await expect(canvas).toBeFocused()
  await expect.poll(() => probe.getAttribute('data-camera')).not.toBe(keyboardCamera)
  await page.getByRole('tab', { name: '車輛控制' }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('tab', { name: 'ADAS 情境' })).toBeFocused()
  await expect(page.getByRole('tab', { name: 'ADAS 情境' })).toHaveAttribute('aria-selected', 'true')
  await page.getByRole('button', { name: /盲點鄰車/ }).click()
  await page.getByRole('checkbox', { name: '超音波', exact: true }).scrollIntoViewIfNeeded()
  await expect(page.getByRole('checkbox', { name: '超音波', exact: true })).toBeInViewport()
  const overflow = await page.evaluate(() => ({
    horizontal: document.documentElement.scrollWidth > innerWidth,
    vertical: document.documentElement.scrollHeight > innerHeight,
  }))
  expect(overflow).toEqual({ horizontal: false, vertical: false })
})

test('連續切車 20 次後 GPU 資源數量返回基準且仍持續繪製', async ({ page }, testInfo) => {
  const probe = page.getByTestId('renderer-diagnostics')
  const read = () => probe.evaluate(element => ({
    vehicle: element.getAttribute('data-vehicle-id'),
    state: element.getAttribute('data-load-state'),
    geometries: Number(element.getAttribute('data-geometries')),
    textures: Number(element.getAttribute('data-textures')),
    frames: Number(element.getAttribute('data-frames')),
  }))
  type Snapshot = Awaited<ReturnType<typeof read>>
  let baseline: Snapshot | null = null
  let final: Snapshot | null = null
  let finalReadError: string | null = null
  const switches: ({ iteration: number; requestedVehicle: string } & Snapshot)[] = []
  try {
    // Warm every model before recording the baseline to exclude lazy allocations.
    for (const model of models) {
      await selectVehicle(page, model.id)
      await expect(probe).toHaveAttribute('data-vehicle-id', model.id)
    }
    await selectVehicle(page, 'sedan-01')
    await expect(probe).toHaveAttribute('data-vehicle-id', 'sedan-01')
    baseline = await read()
    const { geometries, textures, frames } = baseline
    expect(geometries).toBeGreaterThan(0)
    for (let index = 0; index < 20; index++) {
      const model = models[(index + 1) % models.length]!
      await selectVehicle(page, model.id)
      await expect(probe).toHaveAttribute('data-vehicle-id', model.id)
      switches.push({ iteration: index + 1, requestedVehicle: model.id, ...await read() })
    }
    await expect.poll(async () => Number(await probe.getAttribute('data-geometries'))).toBe(geometries)
    await expect.poll(async () => Number(await probe.getAttribute('data-textures'))).toBe(textures)
    await expect.poll(async () => Number(await probe.getAttribute('data-frames'))).toBeGreaterThan(frames)
  } finally {
    try { final = await read() }
    catch (error) { finalReadError = String(error) }
    await testInfo.attach('vehicle-switch-20.json', {
      body: JSON.stringify({ baseline, switches, final, finalReadError }, null, 2),
      contentType: 'application/json',
    })
  }
})

