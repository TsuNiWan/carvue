import { describe, expect, it, vi } from 'vitest'
import { BoxGeometry, Group, Mesh, MeshStandardMaterial, Quaternion, Raycaster, Texture, Vector3 } from 'three'
import { createVehicleState, type VehicleAssetManifest } from '../types/vehicle'
import { createAssetRig, disposeObject, partIds, validateManifest } from './assetRig'

function fixture() {
  const root = new Group()
  root.name = 'VehicleRoot'
  root.userData = { vehicleId: 'test', assetVersion: '1' }
  const manifest: VehicleAssetManifest = {
    schemaVersion: 1, vehicleId: 'test', assetVersion: '1', units: 'meter', forward: '+Z',
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
  for (const name of [...partIds, ...manifest.frontWheels]) { const pivot = new Group(); pivot.name = name; root.add(pivot) }
  for (const name of ['head', 'tail', 'left', 'right']) {
    const material = new MeshStandardMaterial()
    material.name = name
    root.add(new Mesh(new BoxGeometry(0.1, 0.1, 0.1), material))
  }
  return { root, manifest }
}

describe('GLB vehicle contract', () => {
  it('rejects a mismatched vehicle, invalid axis, missing lights and absent pivots', () => {
    const { root, manifest } = fixture()
    expect(() => validateManifest(manifest, 'test', '1')).not.toThrow()
    expect(() => validateManifest(manifest, 'other', '1')).toThrow(/identity/)
    expect(() => validateManifest({ ...manifest, forward: '-Z' }, 'test', '1')).toThrow(/coordinate/)
    expect(() => validateManifest({ ...manifest, framing: { ...manifest.framing, distance: 0 } }, 'test', '1')).toThrow(/framing/)
    const bad = structuredClone(manifest)
    bad.joints.frontLeft.axis = [0, 0, 0]
    expect(() => validateManifest(bad, 'test', '1')).toThrow(/joint/)
    expect(() => validateManifest({ ...manifest, lights: {} }, 'test', '1')).toThrow(/light/)
    manifest.joints.frontLeft.node = 'missing'
    expect(() => createAssetRig(root, manifest)).toThrow(/node/)
    disposeObject(root)
  })

  it('preserves nonzero closed poses while articulating around local axes', () => {
    const { root, manifest } = fixture()
    root.getObjectByName('frontLeft')!.rotation.z = 0.25
    const closed = root.getObjectByName('frontLeft')!.quaternion.clone()
    const rig = createAssetRig(root, manifest)
    const state = createVehicleState()
    state.doors.frontLeft = true
    rig.update(state, 1.1, 1.1)
    const open = closed.clone().multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), -1.1))
    expect(rig.joints.frontLeft.quaternion.angleTo(open)).toBeLessThan(1e-6)
    state.doors.frontLeft = false
    rig.update(state, 1.1, 2.2)
    expect(rig.joints.frontLeft.quaternion.angleTo(closed)).toBeLessThan(1e-6)
    rig.dispose()
  })

  it.each(partIds.flatMap(id => [0.25, 0.5, 0.75].map(fraction => [id, fraction] as const)))('reverses %s at %s of its travel without jumping and closes exactly', (id, fraction) => {
    const { root, manifest } = fixture()
    const rig = createAssetRig(root, manifest)
    const state = createVehicleState()
    if (id === 'trunk') state.trunk = true
    else state.doors[id] = true
    for (let step = 0; step < 3000 && rig.presentation.parts[id] < fraction; step++) rig.update(state, 0.001, step * 0.001)
    const pose = rig.joints[id].quaternion.clone()
    const progress = rig.presentation.parts[id]
    expect(progress).toBeGreaterThanOrEqual(fraction)
    expect(progress).toBeLessThan(fraction + 0.004)
    if (id === 'trunk') state.trunk = false
    else state.doors[id] = false
    rig.update(state, 0, 0)
    expect(rig.joints[id].quaternion.angleTo(pose)).toBeLessThan(1e-6)
    rig.update(state, 0.016, 0.016)
    expect(rig.presentation.parts[id]).toBeLessThan(progress)
    const remainingTime = (id === 'trunk' ? 1.4 : 1.1) * progress - 0.016
    rig.update(state, remainingTime + 0.00001, 1)
    expect(rig.presentation.parts[id]).toBe(0)
    expect(rig.joints[id].quaternion.angleTo(new Quaternion())).toBeLessThan(1e-6)
    rig.dispose()
  })

  it.each(partIds.flatMap(id => [false, true].map(reducedMotion => [id, reducedMotion] as const)))('keeps %s at half travel halfway through opening and closing with reducedMotion=%s', (id, reducedMotion) => {
    const { root, manifest } = fixture()
    const rig = createAssetRig(root, manifest)
    const state = createVehicleState()
    const halfDuration = id === 'trunk' ? 0.7 : 0.55
    if (id === 'trunk') state.trunk = true
    else state.doors[id] = true
    rig.update(state, halfDuration, halfDuration, reducedMotion)
    expect(rig.presentation.parts[id]).toBeCloseTo(0.5)
    rig.update(state, halfDuration, halfDuration * 2, reducedMotion)
    expect(rig.presentation.parts[id]).toBe(1)
    if (id === 'trunk') state.trunk = false
    else state.doors[id] = false
    rig.update(state, halfDuration, halfDuration * 3, reducedMotion)
    expect(rig.presentation.parts[id]).toBeCloseTo(0.5)
    rig.update(state, halfDuration, halfDuration * 4, reducedMotion)
    expect(rig.presentation.parts[id]).toBe(0)
    rig.dispose()
  })

  it('fades actual lamps and spotlights together, including mid-fade reversal', () => {
    const { root, manifest } = fixture()
    const rig = createAssetRig(root, manifest)
    const state = createVehicleState()
    state.headlights = true
    rig.update(state, 0.125, 0)
    expect(rig.presentation.headlights).toBeCloseTo(0.5)
    expect(rig.lights.head[0]!.emissiveIntensity).toBeCloseTo(1.6)
    expect(rig.lights.tail[0]!.emissiveIntensity).toBeCloseTo(1.1)
    state.headlights = false
    rig.update(state, 0, 0)
    expect(rig.presentation.headlights).toBeCloseTo(0.5)
    rig.update(state, 0.125, 0)
    expect(rig.lights.head[0]!.emissiveIntensity).toBe(0)
    rig.dispose()
  })

  it('keeps independent indicator banks and synchronized hazard envelopes', () => {
    const { root, manifest } = fixture()
    const rig = createAssetRig(root, manifest)
    const state = createVehicleState()
    state.signal = 'left'
    rig.update(state, 0.016, 0.1)
    expect(rig.lights.left[0]!.emissiveIntensity).toBeCloseTo(3.4)
    expect(rig.lights.right[0]!.emissiveIntensity).toBe(0)
    state.signal = 'hazard'
    rig.update(state, 0.016, 0.425)
    expect(rig.lights.left[0]!.emissiveIntensity).toBeCloseTo(1.7)
    expect(rig.lights.right[0]!.emissiveIntensity).toBeCloseTo(1.7)
    rig.update(state, 0.016, 0.6)
    expect(rig.lights.left[0]!.emissiveIntensity).toBe(0)
    rig.dispose()
  })

  it('shortens auxiliary fades for reduced motion while preserving mechanism travel and clamping steering', () => {
    const { root, manifest } = fixture()
    const rig = createAssetRig(root, manifest)
    const state = createVehicleState()
    state.trunk = true
    state.headlights = true
    state.steeringAngle = 90
    rig.update(state, 0.05, 0.05, true)
    expect(rig.presentation.parts.trunk).toBeLessThan(0.01)
    expect(rig.presentation.headlights).toBeCloseTo(0.5)
    expect(rig.presentation.steeringAngle).toBe(30)
    rig.update(state, 0.05, 0.1, true)
    expect(rig.presentation.parts.trunk).toBeLessThan(0.02)
    expect(rig.presentation.headlights).toBe(1)
    rig.update(state, 1.3, 1.4, true)
    expect(rig.presentation.parts.trunk).toBe(1)
    rig.dispose()
  })

  it('preserves exact ray hits for opaque, glass and moving meshes without changing global raycasts or render indices', () => {
    const { root, manifest } = fixture()
    const geometry = new BoxGeometry(0.5, 1, 0.15, 3, 3, 3)
    const indices = Array.from(geometry.index!.array)
    const opaque = new Mesh(geometry, new MeshStandardMaterial())
    const glass = new Mesh(geometry, new MeshStandardMaterial({ transparent: true, opacity: 0.3 }))
    opaque.position.x = 0.75
    glass.position.x = -0.75
    root.getObjectByName('frontLeft')!.add(opaque)
    root.getObjectByName('frontRight')!.add(glass)
    const originalRaycast = Mesh.prototype.raycast
    const rig = createAssetRig(root, manifest)
    const accelerated = opaque.raycast
    const state = createVehicleState()
    state.doors.frontLeft = true
    state.doors.frontRight = true
    const raycaster = new Raycaster()
    for (const delta of [0, 0.55, 0.55]) {
      rig.update(state, delta, 0)
      root.updateMatrixWorld(true)
      for (const mesh of [opaque, glass]) {
        const target = mesh.getWorldPosition(new Vector3())
        raycaster.set(target.clone().add(new Vector3(0, 0, 3)), new Vector3(0, 0, -1))
        mesh.raycast = originalRaycast
        const expected = raycaster.intersectObject(mesh).map(hit => ({ distance: hit.distance, point: hit.point.toArray(), face: hit.faceIndex })).sort((a, b) => a.face! - b.face!)
        mesh.raycast = accelerated
        expect(raycaster.intersectObject(mesh).map(hit => ({ distance: hit.distance, point: hit.point.toArray(), face: hit.faceIndex })).sort((a, b) => a.face! - b.face!)).toEqual(expected)
      }
    }
    expect(Mesh.prototype.raycast).toBe(originalRaycast)
    expect(Array.from(geometry.index!.array)).toEqual(indices)
    expect(geometry.boundsTree).toBeDefined()
    rig.dispose()
    expect(geometry.boundsTree).toBeNull()
  })

  it('releases shared geometry, materials, textures and decoded images only once', () => {
    const root = new Group()
    const geometry = new BoxGeometry()
    const texture = new Texture()
    const bitmap = { close: vi.fn() }
    texture.image = bitmap
    const material = new MeshStandardMaterial({ map: texture, roughnessMap: texture })
    root.add(new Mesh(geometry, material), new Mesh(geometry, material))
    const geometryDispose = vi.spyOn(geometry, 'dispose')
    const materialDispose = vi.spyOn(material, 'dispose')
    const textureDispose = vi.spyOn(texture, 'dispose')
    disposeObject(root)
    disposeObject(root)
    expect(geometryDispose).toHaveBeenCalledTimes(1)
    expect(materialDispose).toHaveBeenCalledTimes(1)
    expect(textureDispose).toHaveBeenCalledTimes(1)
    expect(bitmap.close).toHaveBeenCalledTimes(1)
  })
})
