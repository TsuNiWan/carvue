import os from 'node:os'
import { expect, type Locator, type Page } from '@playwright/test'
import { vehicles } from '../src/data/vehicles'

export const models = vehicles.map(vehicle => ({
  id: vehicle.id,
  name: vehicle.name,
  rear: vehicle.bodyStyle === 'suv' ? '後尾門' : '後車廂',
  modelUrl: `/${vehicle.asset.modelUrl}`,
  manifestUrl: `/${vehicle.asset.manifestUrl}`,
}))

export const doors = ['左前門', '右前門', '左後門', '右後門']

export async function diagnostics(page: Page, attribute: string): Promise<Record<string, number>> {
  return JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute(attribute)) ?? '{}')
}

export async function range(locator: Locator, value: number) {
  await locator.fill(String(value))
  await locator.dispatchEvent('input')
}

export async function waitForVehicle(page: Page, id: string) {
  const probe = page.getByTestId('renderer-diagnostics')
  await expect(probe).toHaveAttribute('data-vehicle-id', id)
  await expect(probe).toHaveAttribute('data-load-state', 'ready')
  await expect(page.getByLabel('車輛 3D 場景', { exact: true })).toHaveAttribute('data-ready', 'true')
  await expect.poll(async () => Number(await probe.getAttribute('data-frames'))).toBeGreaterThan(2)
}

export async function openVehicle(page: Page, id = 'sedan-01') {
  await page.goto(`/#/vehicles/${id}`)
  await waitForVehicle(page, id)
}

export async function selectVehicle(page: Page, id: string, wait = true) {
  const option = page.getByTestId(`select-${id}`)
  if (!await option.isVisible()) await page.locator('summary').filter({ hasText: '切換車款' }).click()
  await option.click()
  if (wait) await waitForVehicle(page, id)
}

export interface Presentation {
  parts: Record<'frontLeft' | 'frontRight' | 'rearLeft' | 'rearRight' | 'trunk', number>
  headlights: number
  steeringAngle: number
}

export async function presentation(page: Page): Promise<Presentation> {
  return JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute('data-presentation')) ?? '{}')
}

export function hostEnvironment() {
  return { platform: os.platform(), release: os.release(), arch: os.arch(), cpu: os.cpus()[0]?.model, logicalCpus: os.cpus().length, totalMemoryBytes: os.totalmem() }
}

export async function measureFrames(page: Page, durationMs: number) {
  // The frame counter includes loading renders; interval samples begin at readiness.
  await expect.poll(async () => JSON.parse((await page.getByTestId('renderer-diagnostics').getAttribute('data-frame-times')) ?? '[]').length).toBeGreaterThan(0)
  return page.evaluate(async requestedDurationMs => {
    const probe = document.querySelector<HTMLElement>('[data-testid="renderer-diagnostics"]')!
    const canvas = document.querySelector<HTMLCanvasElement>('canvas[aria-label="車輛 3D 場景"]')!
    const context = canvas.getContext('webgl2')!
    const debug = context.getExtension('WEBGL_debug_renderer_info')
    const startedAt = new Date().toISOString()
    const startTime = performance.now()
    const startFrames = Number(probe.dataset.frames)
    let previousFrames = startFrames
    let droppedSamples = 0
    const frameIntervalsMs: number[] = []
    const samples: { elapsedMs: number; frames: number; geometries: number; textures: number; vehicle: string }[] = []
    const capture = () => {
      const frames = Number(probe.dataset.frames)
      const intervals: number[] = JSON.parse(probe.dataset.frameTimes ?? '[]')
      const added = Math.max(0, frames - previousFrames)
      if (added > intervals.length) droppedSamples += added - intervals.length
      if (added) frameIntervalsMs.push(...intervals.slice(-Math.min(added, intervals.length)).filter(value => Number.isFinite(value) && value > 0))
      previousFrames = frames
      samples.push({ elapsedMs: performance.now() - startTime, frames, geometries: Number(probe.dataset.geometries), textures: Number(probe.dataset.textures), vehicle: probe.dataset.vehicleId ?? '' })
    }
    return await new Promise<{
      requestedDurationMs: number; elapsedMs: number; startedAt: string; endedAt: string;
      viewport: { width: number; height: number; devicePixelRatio: number };
      userAgent: string; gpu: string; startFrames: number; endFrames: number;
      meanFPS: number; p95FrameIntervalMs: number; droppedSamples: number;
      frameIntervalsMs: number[]; samples: typeof samples;
    }>(resolve => {
      const interval = setInterval(capture, 250)
      setTimeout(() => {
        clearInterval(interval)
        capture()
        const elapsedMs = performance.now() - startTime
        const endFrames = Number(probe.dataset.frames)
        const sorted = [...frameIntervalsMs].sort((a, b) => a - b)
        resolve({
          requestedDurationMs, elapsedMs, startedAt, endedAt: new Date().toISOString(),
          viewport: { width: innerWidth, height: innerHeight, devicePixelRatio },
          userAgent: navigator.userAgent,
          gpu: String(debug ? context.getParameter(debug.UNMASKED_RENDERER_WEBGL) : context.getParameter(context.RENDERER)),
          startFrames, endFrames, meanFPS: (endFrames - startFrames) / (elapsedMs / 1000),
          p95FrameIntervalMs: sorted[Math.max(0, Math.ceil(sorted.length * 0.95) - 1)] ?? Infinity,
          droppedSamples, frameIntervalsMs, samples,
        })
      }, requestedDurationMs)
    })
  }, durationMs)
}
