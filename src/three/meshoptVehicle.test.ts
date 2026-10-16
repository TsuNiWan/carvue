import { afterEach, expect, it, vi } from 'vitest'
import { Document, NodeIO } from '@gltf-transform/core'
import { EXTMeshoptCompression } from '@gltf-transform/extensions'
import { MeshoptEncoder } from 'meshoptimizer'
import { Mesh } from 'three'
import { vehicles } from '../data/vehicles'
import { createVehicleState, type VehicleAssetManifest } from '../types/vehicle'
import { loadVehicle } from './loadVehicle'

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('loads a real meshopt-compressed GLB through the bundled decoder and preserves rig geometry and movement', async () => {
  const vehicle = vehicles[0]!
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
  const document = new Document()
  const buffer = document.createBuffer()
  const expectedPosition = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0])
  const positions = document.createAccessor().setType('VEC3').setArray(expectedPosition).setBuffer(buffer)
  const root = document.createNode('VehicleRoot').setExtras({ vehicleId: vehicle.id, assetVersion: vehicle.asset.version })
  document.createScene().addChild(root)
  const pivots = Object.keys(manifest.joints).map(name => document.createNode(name))
  for (const pivot of pivots) root.addChild(pivot)
  for (const name of manifest.frontWheels) root.addChild(document.createNode(name))
  for (const name of ['head', 'tail', 'left', 'right']) {
    const material = document.createMaterial(name).setEmissiveFactor([1, 1, 1])
    const primitive = document.createPrimitive().setAttribute('POSITION', positions).setMaterial(material)
    const node = document.createNode(`${name}Surface`).setMesh(document.createMesh().addPrimitive(primitive))
    pivots[0]!.addChild(node)
  }
  await MeshoptEncoder.ready
  document.createExtension(EXTMeshoptCompression).setRequired(true)
    .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE })
  const bytes = await new NodeIO().registerExtensions([EXTMeshoptCompression])
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder }).writeBinary(document)
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const json = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + view.getUint32(12, true))))
  expect(json.extensionsRequired).toContain('EXT_meshopt_compression')
  expect(json.bufferViews.some((value: { extensions?: Record<string, unknown> }) => value.extensions?.EXT_meshopt_compression)).toBe(true)

  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(new Response(JSON.stringify(manifest)))
    .mockResolvedValueOnce(new Response(new Uint8Array(bytes).buffer))
  vi.stubGlobal('window', { location: { href: 'https://example.test/#/vehicles/sedan-01' } })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubEnv('BASE_URL', '/')
  const rig = await loadVehicle(vehicle, new AbortController().signal, vi.fn())
  try {
    const mesh = rig.root.getObjectByName('headSurface') as Mesh
    expect(Array.from(mesh.geometry.getAttribute('position').array)).toEqual(Array.from(expectedPosition))
    expect(mesh.geometry.boundsTree).toBeDefined()
    const state = createVehicleState()
    state.doors.frontLeft = true
    rig.update(state, 0.55, 0.55, true)
    expect(rig.presentation.parts.frontLeft).toBeCloseTo(0.5)
    rig.update(state, 0.55, 1.1, true)
    expect(rig.presentation.parts.frontLeft).toBe(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  } finally {
    rig.dispose()
  }
})
