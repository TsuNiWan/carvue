import { describe, expect, it } from 'vitest'
import { Box3, BufferGeometry, Material, Mesh, MeshStandardMaterial, SpotLight } from 'three'
import { vehicles } from '../data/vehicles'
import { createVehicleState } from '../types/vehicle'
import { createVehicle } from './vehicle'

describe('procedural vehicle rig', () => {
  it.each(vehicles)('builds finite geometry and separate movable panels for $id', def => {
    const rig = createVehicle(def)
    const bounds = new Box3().setFromObject(rig.root)
    for (const value of [...bounds.min.toArray(), ...bounds.max.toArray()]) expect(Number.isFinite(value)).toBe(true)
    expect(bounds.max.y).toBeGreaterThan(def.height - 0.05)
    expect(bounds.min.y).toBeGreaterThan(-0.03)
    expect(Object.keys(rig.joints)).toHaveLength(5)
    expect(rig.frontWheels).toHaveLength(2)
    for (const joint of Object.values(rig.joints)) expect(joint.children.length).toBeGreaterThan(0)
    expect(rig.root.getObjectByName('windshield')).toBeDefined()
    expect(rig.root.getObjectByName('frontLeft-outer-panel')).toBeDefined()
    rig.dispose()
  })

  it('opens both sides outward, lifts the trunk and clamps steering angle', () => {
    const rig = createVehicle(vehicles[0]!)
    const state = createVehicleState()
    state.doors.frontLeft = true
    state.doors.frontRight = true
    state.doors.rearLeft = true
    state.trunk = true
    state.steeringAngle = 80
    rig.update(state, 1 / 60, 0, true)
    expect(rig.joints.frontLeft.rotation.y).toBeLessThan(0)
    expect(rig.joints.frontRight.rotation.y).toBeGreaterThan(0)
    expect(rig.joints.rearLeft.rotation.y).toBeLessThan(0)
    expect(rig.joints.rearRight.rotation.y).toBe(0)
    expect(rig.joints.trunk.rotation.x).toBeGreaterThan(0)
    expect(rig.frontWheels[0]!.rotation.y).toBeCloseTo(-Math.PI / 6)
    rig.dispose()
  })

  it('reverses a moving door continuously from its current angle', () => {
    const rig = createVehicle(vehicles[0]!)
    const state = createVehicleState()
    state.doors.frontLeft = true
    rig.update(state, 1 / 60, 0)
    const opened = rig.joints.frontLeft.rotation.y
    expect(opened).toBeLessThan(0)
    expect(opened).toBeGreaterThan(-Math.PI * 0.37)
    state.doors.frontLeft = false
    rig.update(state, 1 / 60, 0.02)
    expect(rig.joints.frontLeft.rotation.y).toBeGreaterThan(opened)
    expect(rig.joints.frontLeft.rotation.y).toBeLessThan(0)
    rig.dispose()
  })

  it('drives headlamps and synchronized left/right indicator phases', () => {
    const rig = createVehicle(vehicles[0]!)
    const state = createVehicleState()
    const materials = new Map<string, MeshStandardMaterial>()
    const lights: SpotLight[] = []
    rig.root.traverse(object => {
      if (object instanceof Mesh && object.material instanceof MeshStandardMaterial) materials.set(object.material.name, object.material)
      if (object instanceof SpotLight) lights.push(object)
    })
    state.headlights = true
    state.signal = 'left'
    rig.update(state, 0.016, 0.1)
    expect(materials.get('headlamp')!.emissiveIntensity).toBeGreaterThan(1)
    expect(materials.get('left-signal')!.emissiveIntensity).toBeGreaterThan(1)
    expect(materials.get('right-signal')!.emissiveIntensity).toBe(0)
    expect(lights.every(light => light.intensity > 0)).toBe(true)
    state.signal = 'hazard'
    rig.update(state, 0.016, 0.1)
    expect(materials.get('left-signal')!.emissiveIntensity).toBe(materials.get('right-signal')!.emissiveIntensity)
    rig.update(state, 0.016, 0.6)
    expect(materials.get('left-signal')!.emissiveIntensity).toBe(0)
    expect(materials.get('right-signal')!.emissiveIntensity).toBe(0)
    state.headlights = false
    rig.update(state, 0.016, 0.6)
    expect(lights.every(light => light.intensity === 0)).toBe(true)
    rig.dispose()
  })

  it('disposes every owned geometry and material exactly once without sharing resources', () => {
    const a = createVehicle(vehicles[0]!)
    const b = createVehicle(vehicles[1]!)
    const resources = new Set<BufferGeometry | Material>()
    const disposed = new Map<BufferGeometry | Material, number>()
    a.root.traverse(object => {
      if (object instanceof Mesh) {
        resources.add(object.geometry)
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) resources.add(material)
      }
    })
    for (const resource of resources) resource.addEventListener('dispose', () => disposed.set(resource, (disposed.get(resource) ?? 0) + 1))
    b.root.traverse(object => {
      if (object instanceof Mesh) {
        expect(resources.has(object.geometry)).toBe(false)
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) expect(resources.has(material)).toBe(false)
      }
    })
    a.dispose()
    a.dispose()
    expect(disposed.size).toBe(resources.size)
    expect([...disposed.values()].every(count => count === 1)).toBe(true)
    expect(a.root.children).toHaveLength(0)
    expect(b.root.children.length).toBeGreaterThan(0)
    b.dispose()
  })
})
