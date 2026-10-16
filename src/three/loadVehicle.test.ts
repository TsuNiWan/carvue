import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BufferGeometry, Group, Mesh, MeshStandardMaterial, Texture } from 'three'
import { createVehicleState, type VehicleAssetManifest, type VehicleDefinition } from '../types/vehicle'
import { disposeObject, partIds, type AssetRig } from './assetRig'
import { loadVehicle } from './loadVehicle'

const { parseAsync } = vi.hoisted(() => ({ parseAsync: vi.fn() }))
vi.mock('three/addons/loaders/GLTFLoader.js', () => ({
  GLTFLoader: class { parseAsync = parseAsync; setMeshoptDecoder() { return this } },
}))

const fetchMock = vi.fn<typeof fetch>()
const roots: Group[] = []
const vehicle: VehicleDefinition = {
  id: 'fixture-car', name: 'Fixture car', bodyStyle: 'sedan', color: '#ffffff',
  length: 4.6, width: 1.8, height: 1.4, wheelbase: 2.7, tagline: '',
  asset: { version: '2.0.0', modelUrl: 'models/fixture-car/2.0.0/vehicle.glb', manifestUrl: 'models/fixture-car/2.0.0/manifest.json', posterUrl: 'previews/fixture-car.webp', status: 'development' },
  capabilities: { doors: ['frontLeft', 'frontRight', 'rearLeft', 'rearRight'], trunk: true, headlights: true, signals: true, steering: true },
}

function fixture() {
  const root = new Group()
  root.name = 'VehicleRoot'
  root.userData = { vehicleId: vehicle.id, assetVersion: vehicle.asset.version }
  roots.push(root)
  const manifest: VehicleAssetManifest = {
    schemaVersion: 1, vehicleId: vehicle.id, assetVersion: vehicle.asset.version, units: 'meter', forward: '+Z',
    framing: { target: [0, 0.6, 0], direction: [1.2, 0.76, 1.65], distance: 7.5 },
    joints: {
      frontLeft: { node: 'frontLeft', axis: [0, 1, 0], openAngle: -1.1 },
      frontRight: { node: 'frontRight', axis: [0, 1, 0], openAngle: 1.1 },
      rearLeft: { node: 'rearLeft', axis: [0, 1, 0], openAngle: -1.1 },
      rearRight: { node: 'rearRight', axis: [0, 1, 0], openAngle: 1.1 },
      trunk: { node: 'trunk', axis: [1, 0, 0], openAngle: 1.2 },
    },
    frontWheels: ['wheelLeft', 'wheelRight'],
    lights: { head: ['head'], tail: ['tail'], left: ['left'], right: ['right'] },
    headlights: [{ position: [0.6, 0.7, 2], target: [0.6, 0, 8] }, { position: [-0.6, 0.7, 2], target: [-0.6, 0, 8] }],
    hotspots: [{ id: 'frontLeft', node: 'frontLeft', position: [0, 0, 0], label: '左前門' }],
  }
  for (const name of [...partIds, ...manifest.frontWheels]) {
    const pivot = new Group()
    pivot.name = name
    root.add(pivot)
  }
  const geometry = new BufferGeometry()
  const texture = new Texture()
  const image = { close: vi.fn() }
  texture.image = image
  const materials = ['head', 'tail', 'left', 'right'].map(name => {
    const material = new MeshStandardMaterial({ map: texture })
    material.name = name
    root.add(new Mesh(geometry, material))
    return material
  })
  root.add(new Mesh(geometry, materials[0]))
  const disposed = {
    geometry: vi.spyOn(geometry, 'dispose'),
    texture: vi.spyOn(texture, 'dispose'),
    materials: materials.map(material => vi.spyOn(material, 'dispose')),
    image: image.close,
  }
  return { root, manifest, disposed }
}

function manifestResponse(manifest: VehicleAssetManifest) {
  return new Response(JSON.stringify(manifest), { headers: { 'Content-Type': 'application/json' } })
}

function streamedResponse(chunks = [[1, 2], [3, 4, 5, 6]], contentLength: number | null = 6) {
  return new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new Uint8Array(chunk))
      controller.close()
    },
  }), { headers: contentLength === null ? {} : { 'Content-Length': String(contentLength) } })
}

function respond(manifest: VehicleAssetManifest, model = streamedResponse()) {
  fetchMock.mockResolvedValueOnce(manifestResponse(manifest)).mockResolvedValueOnce(model)
}

function expectDisposedOnce(disposed: ReturnType<typeof fixture>['disposed']) {
  expect(disposed.geometry).toHaveBeenCalledTimes(1)
  expect(disposed.texture).toHaveBeenCalledTimes(1)
  expect(disposed.image).toHaveBeenCalledTimes(1)
  for (const material of disposed.materials) expect(material).toHaveBeenCalledTimes(1)
}

beforeEach(() => {
  parseAsync.mockReset()
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('window', { location: { href: 'https://example.test/showroom/#/vehicles/fixture-car' } })
  vi.stubEnv('BASE_URL', '/showroom/')
})

afterEach(() => {
  for (const root of roots.splice(0)) disposeObject(root)
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('vehicle asset loading lifecycle', () => {
  it('assembles streamed bytes, keeps deployment base paths, and hands resource ownership to the returned rig', async () => {
    const { root, manifest, disposed } = fixture()
    respond(manifest)
    parseAsync.mockResolvedValue({ scene: root })
    const controller = new AbortController()
    const progress = vi.fn()
    const rig = await loadVehicle(vehicle, controller.signal, progress)

    expect(fetchMock).toHaveBeenCalledWith('/showroom/models/fixture-car/2.0.0/manifest.json', { signal: controller.signal })
    expect(String(fetchMock.mock.calls[1]![0])).toBe('https://example.test/showroom/models/fixture-car/2.0.0/vehicle.glb')
    expect(fetchMock.mock.calls[1]![1]?.signal).toBe(controller.signal)
    expect(new Uint8Array(parseAsync.mock.calls[0]![0])).toEqual(new Uint8Array([1, 2, 3, 4, 5, 6]))
    expect(parseAsync.mock.calls[0]![1]).toBe('https://example.test/showroom/models/fixture-car/2.0.0/')
    const fractions = progress.mock.calls.map(([fraction]) => fraction as number)
    expect(fractions[0]).toBeGreaterThan(0)
    expect(fractions[0]).toBeLessThan(fractions[1]!)
    expect(fractions.at(-1)).toBeLessThan(1)
    expect(fractions.at(-1)).toBeGreaterThanOrEqual(0.95)
    expect(fractions.every((fraction, index) => index === 0 || fraction >= fractions[index - 1]!)).toBe(true)
    expect(rig.root).toBe(root)
    expect(disposed.geometry).not.toHaveBeenCalled()
    const state = createVehicleState()
    state.doors.frontLeft = true
    rig.update(state, 2.5, 2.5)
    expect(rig.presentation.parts.frontLeft).toBe(1)
    rig.dispose()
    rig.dispose()
    expectDisposedOnce(disposed)
  })

  it('reports finite preparation progress when the server omits Content-Length', async () => {
    const { root, manifest } = fixture()
    respond(manifest, streamedResponse([[1, 2], [3]], null))
    parseAsync.mockResolvedValue({ scene: root })
    const progress = vi.fn()
    const rig = await loadVehicle(vehicle, new AbortController().signal, progress)
    expect(parseAsync).toHaveBeenCalledOnce()
    expect(progress).toHaveBeenCalled()
    expect(progress.mock.calls.every(([fraction]) => Number.isFinite(fraction) && fraction >= 0 && fraction < 1)).toBe(true)
    rig.dispose()
  })

  it('accepts arrayBuffer-only responses without requiring a readable stream', async () => {
    const { root, manifest } = fixture()
    const response = new Response(null)
    vi.spyOn(response, 'arrayBuffer').mockResolvedValue(new Uint8Array([7, 8, 9]).buffer)
    respond(manifest, response)
    parseAsync.mockResolvedValue({ scene: root })
    const rig = await loadVehicle(vehicle, new AbortController().signal, vi.fn())
    expect(response.arrayBuffer).toHaveBeenCalledOnce()
    expect(new Uint8Array(parseAsync.mock.calls[0]![0])).toEqual(new Uint8Array([7, 8, 9]))
    rig.dispose()
  })

  it.each(['vehicleId', 'assetVersion'] as const)('rejects a mismatched manifest %s before parsing the model', async key => {
    const { manifest } = fixture()
    manifest[key] = 'wrong-identity'
    respond(manifest)
    await expect(loadVehicle(vehicle, new AbortController().signal, vi.fn())).rejects.toThrow(/identity/)
    expect(parseAsync).not.toHaveBeenCalled()
  })

  it.each(['manifest', 'model'])('rejects an unsuccessful %s HTTP response without parsing', async failedAsset => {
    const { manifest } = fixture()
    fetchMock.mockResolvedValueOnce(failedAsset === 'manifest' ? new Response(null, { status: 404 }) : manifestResponse(manifest))
    fetchMock.mockResolvedValueOnce(failedAsset === 'model' ? new Response(null, { status: 503 }) : streamedResponse())
    await expect(loadVehicle(vehicle, new AbortController().signal, vi.fn())).rejects.toThrow(/download/)
    expect(parseAsync).not.toHaveBeenCalled()
  })

  it('does not start parsing when aborted during the model download', async () => {
    const { manifest } = fixture()
    const controller = new AbortController()
    respond(manifest)
    const progress = vi.fn(() => controller.abort())
    await expect(loadVehicle(vehicle, controller.signal, progress)).rejects.toMatchObject({ name: 'AbortError' })
    expect(parseAsync).not.toHaveBeenCalled()
  })

  it('releases parsed resources when a request is aborted while GLTF parsing is still pending', async () => {
    const { root, manifest, disposed } = fixture()
    const controller = new AbortController()
    respond(manifest)
    let finish!: (gltf: { scene: Group }) => void
    parseAsync.mockReturnValue(new Promise<{ scene: Group }>(resolve => { finish = resolve }))
    const loading = loadVehicle(vehicle, controller.signal, vi.fn())
    const rejected = expect(loading).rejects.toMatchObject({ name: 'AbortError' })
    await vi.waitFor(() => expect(parseAsync).toHaveBeenCalledOnce())
    controller.abort()
    finish({ scene: root })
    await rejected
    expectDisposedOnce(disposed)
    expect(root.children).toHaveLength(0)
  })

  it('releases a parsed scene when its movable-part contract is invalid', async () => {
    const { root, manifest, disposed } = fixture()
    root.remove(root.getObjectByName('frontLeft')!)
    respond(manifest)
    parseAsync.mockResolvedValue({ scene: root })
    await expect(loadVehicle(vehicle, new AbortController().signal, vi.fn())).rejects.toThrow(/node.*frontLeft/)
    expectDisposedOnce(disposed)
    expect(root.children).toHaveLength(0)
  })

  it.each(['vehicleId', 'assetVersion'] as const)('rejects a parsed model with the wrong %s and releases its resources', async key => {
    const { root, manifest, disposed } = fixture()
    root.userData[key] = 'wrong-model'
    respond(manifest)
    parseAsync.mockResolvedValue({ scene: root })
    await expect(loadVehicle(vehicle, new AbortController().signal, vi.fn())).rejects.toThrow(/identity/)
    expectDisposedOnce(disposed)
    expect(root.children).toHaveLength(0)
  })

  it('allows a clean retry after GLTF parsing fails', async () => {
    const { root, manifest, disposed } = fixture()
    respond(manifest)
    const parseError = new Error('Invalid GLB data')
    parseAsync.mockRejectedValueOnce(parseError)
    await expect(loadVehicle(vehicle, new AbortController().signal, vi.fn())).rejects.toBe(parseError)
    respond(manifest)
    parseAsync.mockResolvedValueOnce({ scene: root })
    const rig = await loadVehicle(vehicle, new AbortController().signal, vi.fn())
    expect(parseAsync).toHaveBeenCalledTimes(2)
    expect(rig.root).toBe(root)
    expect(disposed.geometry).not.toHaveBeenCalled()
    rig.dispose()
    expectDisposedOnce(disposed)
  })

  it('bounds load phase marks across repeated loads without clearing external readiness marks', async () => {
    performance.mark('carvue-test-ready')
    try {
      for (let index = 0; index < 3; index++) {
        const { root, manifest } = fixture()
        respond(manifest)
        parseAsync.mockResolvedValueOnce({ scene: root })
        const rig = await loadVehicle(vehicle, new AbortController().signal, vi.fn())
        performance.mark('carvue-load:first-render-start')
        performance.mark('carvue-load:first-render-end')
        rig.dispose()
      }
      const names = performance.getEntriesByType('mark').filter(entry => entry.name.startsWith('carvue-load:')).map(entry => entry.name)
      expect(names).toHaveLength(6)
      expect(new Set(names).size).toBe(names.length)
      expect(performance.getEntriesByName('carvue-test-ready')).toHaveLength(1)
    } finally {
      performance.clearMarks('carvue-test-ready')
      for (const entry of performance.getEntriesByType('mark')) {
        if (entry.name.startsWith('carvue-load:')) performance.clearMarks(entry.name)
      }
    }
  })

  it('waits for preparation before handing out ownership of the loaded rig', async () => {
    const { root, manifest, disposed } = fixture()
    respond(manifest)
    parseAsync.mockResolvedValueOnce({ scene: root })
    let finish!: () => void
    const prepare = vi.fn((_rig: AssetRig) => new Promise<void>(resolve => { finish = resolve }))
    const resolved = vi.fn()
    const loading = loadVehicle(vehicle, new AbortController().signal, vi.fn(), prepare).then(rig => { resolved(); return rig })
    await vi.waitFor(() => expect(prepare).toHaveBeenCalledOnce())
    expect(resolved).not.toHaveBeenCalled()
    expect(prepare.mock.calls[0]![0].root).toBe(root)
    expect(disposed.geometry).not.toHaveBeenCalled()
    finish()
    const rig = await loading
    expect(resolved).toHaveBeenCalledOnce()
    rig.dispose()
    expectDisposedOnce(disposed)
  })

  it('disposes a rig when preparation rejects instead of handing out a partial result', async () => {
    const { root, manifest, disposed } = fixture()
    respond(manifest)
    parseAsync.mockResolvedValueOnce({ scene: root })
    const error = new Error('Shader preparation failed')
    await expect(loadVehicle(vehicle, new AbortController().signal, vi.fn(), async () => { throw error })).rejects.toBe(error)
    expectDisposedOnce(disposed)
    expect(root.children).toHaveLength(0)
  })

  it('disposes an aborted pending preparation while the newer prepared rig remains usable', async () => {
    const older = fixture()
    const newer = fixture()
    respond(older.manifest)
    parseAsync.mockResolvedValueOnce({ scene: older.root })
    const controller = new AbortController()
    let finishOld!: () => void
    const prepareOld = vi.fn(() => new Promise<void>(resolve => { finishOld = resolve }))
    const oldLoading = loadVehicle(vehicle, controller.signal, vi.fn(), prepareOld)
    const rejected = expect(oldLoading).rejects.toMatchObject({ name: 'AbortError' })
    await vi.waitFor(() => expect(prepareOld).toHaveBeenCalledOnce())
    controller.abort()
    expectDisposedOnce(older.disposed)
    expect(older.root.children).toHaveLength(0)
    respond(newer.manifest)
    parseAsync.mockResolvedValueOnce({ scene: newer.root })
    const current = await loadVehicle(vehicle, new AbortController().signal, vi.fn(), async () => {})
    finishOld()
    await rejected
    expectDisposedOnce(older.disposed)
    expect(newer.disposed.geometry).not.toHaveBeenCalled()
    const state = createVehicleState()
    state.trunk = true
    current.update(state, 1.4, 1.4)
    expect(current.presentation.parts.trunk).toBe(1)
    current.dispose()
    expectDisposedOnce(newer.disposed)
  })

  it('disposes only an aborted older parse while a newer request remains usable', async () => {
    const older = fixture()
    const newer = fixture()
    const oldController = new AbortController()
    let finishOld!: (gltf: { scene: Group }) => void
    parseAsync.mockReturnValueOnce(new Promise<{ scene: Group }>(resolve => { finishOld = resolve }))
    respond(older.manifest)
    const oldLoading = loadVehicle(vehicle, oldController.signal, vi.fn())
    const oldRejected = expect(oldLoading).rejects.toMatchObject({ name: 'AbortError' })
    await vi.waitFor(() => expect(parseAsync).toHaveBeenCalledOnce())
    oldController.abort()
    respond(newer.manifest)
    parseAsync.mockResolvedValueOnce({ scene: newer.root })
    const currentRig = await loadVehicle(vehicle, new AbortController().signal, vi.fn())
    finishOld({ scene: older.root })
    await oldRejected
    expectDisposedOnce(older.disposed)
    expect(newer.disposed.geometry).not.toHaveBeenCalled()
    const state = createVehicleState()
    state.headlights = true
    currentRig.update(state, 0.25, 0.25)
    expect(currentRig.presentation.headlights).toBe(1)
    currentRig.dispose()
    expectDisposedOnce(newer.disposed)
  })
})
