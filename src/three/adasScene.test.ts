import { describe, expect, it } from 'vitest'
import { BufferGeometry, Material, Mesh, Vector3 } from 'three'
import { vehicles } from '../data/vehicles'
import { createScenarioState, evaluateScenario, type ScenarioId, type ScenarioState } from '../adas/scenarios'
import { createAdasScene } from './adasScene'

const sensorsOn = { camera: true, radar: true, lidar: true, ultrasonic: true }
const sensorsOff = { camera: false, radar: false, lidar: false, ultrasonic: false }
const vehicle = vehicles[0]!
const actorNames = { pedestrian: 'actor-pedestrian', blindSpot: 'actor-car', parking: 'actor-obstacle' }

describe('ADAS scene integration', () => {
  it('winds every neighbor body triangle outward so exterior faces are visible', () => {
    const scene = createAdasScene(vehicle)
    try {
      const body = scene.root.getObjectByName('neighbor-body')!.children.find((object) => object instanceof Mesh) as Mesh<BufferGeometry>
      const geometry = body.geometry
      const positions = geometry.getAttribute('position')
      const indices = geometry.getIndex()!
      const interior = new Vector3(0, 0.7, 0)
      let leftTriangles = 0
      let rightTriangles = 0
      for (let i = 0; i < indices.count; i += 3) {
        const a = new Vector3().fromBufferAttribute(positions, indices.getX(i))
        const b = new Vector3().fromBufferAttribute(positions, indices.getX(i + 1))
        const c = new Vector3().fromBufferAttribute(positions, indices.getX(i + 2))
        const normal = b.clone().sub(a).cross(c.clone().sub(a)).normalize()
        const center = a.clone().add(b).add(c).divideScalar(3)
        expect(normal.dot(center.clone().sub(interior))).toBeGreaterThan(0)
        if (a.x === b.x && b.x === c.x) {
          expect(Math.sign(normal.x)).toBe(Math.sign(center.x))
          if (center.x < 0) leftTriangles++
          else rightTriangles++
        }
      }
      expect(leftTriangles).toBeGreaterThan(0)
      expect(rightTriangles).toBeGreaterThan(0)
    } finally { scene.dispose() }
  })

  it.each<ScenarioId>(['pedestrian', 'blindSpot', 'parking'])('positions %s identically during forward and reverse scrubbing', (id) => {
    const scene = createAdasScene(vehicle)
    try {
      const actor = scene.root.getObjectByName(actorNames[id])!
      const snapshot = (progress: number) => {
        const state: ScenarioState = { ...createScenarioState(), id, progress }
        const frame = evaluateScenario(state, 'off', vehicle.length)
        scene.update(frame, state, sensorsOn, 0)
        scene.root.updateMatrixWorld(true)
        expect(actor.position.x).toBeCloseTo(frame.actor.x)
        expect(actor.position.z).toBeCloseTo(frame.actor.z)
        expect(actor.visible).toBe(true)
        const positions: number[][] = []
        actor.traverse((object) => positions.push(object.matrixWorld.toArray()))
        return positions
      }
      const forward = [0, 0.25, 0.5, 0.75, 1].map(snapshot)
      const backward = [1, 0.75, 0.5, 0.25, 0].map(snapshot)
      expect(backward.reverse()).toEqual(forward)
    } finally { scene.dispose() }
  })

  it('hides all sensor layers without hiding or moving the active actor', () => {
    const scene = createAdasScene(vehicle)
    try {
      const state: ScenarioState = { ...createScenarioState(), id: 'blindSpot', progress: 0.4, side: 'right' }
      const frame = evaluateScenario(state, 'right', vehicle.length)
      scene.update(frame, state, sensorsOn, 0)
      const actor = scene.root.getObjectByName('actor-car')!
      const position = actor.position.clone()
      const beforeColor = (scene.root.getObjectByName('neighbor-body')!.children[0] as Mesh).material as Material & { color: { getHex(): number } }
      const color = beforeColor.color.getHex()
      scene.update(frame, state, sensorsOff, 0)
      for (const id of Object.keys(sensorsOff)) expect(scene.root.getObjectByName(`sensor-${id}`)!.visible).toBe(false)
      expect(actor.visible).toBe(true)
      expect(actor.position).toEqual(position)
      expect(beforeColor.color.getHex()).toBe(color)
      expect(scene.labels.map((label) => label.id)).toEqual(['actor'])
      expect(scene.root.getObjectByName('actor-pedestrian')!.visible).toBe(false)
      expect(scene.root.getObjectByName('actor-obstacle')!.visible).toBe(false)
    } finally { scene.dispose() }
  })

  it('disposes each unique geometry and shared material exactly once and clears scene references', () => {
    const scene = createAdasScene(vehicle)
    const state = createScenarioState()
    scene.update(evaluateScenario(state, 'off', vehicle.length), state, sensorsOn, 0)
    const resources = new Set<BufferGeometry | Material>()
    scene.root.traverse((object) => {
      const drawable = object as Mesh
      if (drawable.geometry) resources.add(drawable.geometry)
      if (drawable.material) {
        const materials = Array.isArray(drawable.material) ? drawable.material : [drawable.material]
        materials.forEach((material) => resources.add(material))
      }
    })
    const counts = new Map<BufferGeometry | Material, number>()
    for (const resource of resources) {
      counts.set(resource, 0)
      resource.addEventListener('dispose', () => counts.set(resource, counts.get(resource)! + 1))
    }
    expect(resources.size).toBeGreaterThan(20)
    scene.dispose()
    expect(scene.root.children).toHaveLength(0)
    expect(scene.labels).toHaveLength(0)
    expect([...counts.values()].every((count) => count === 1)).toBe(true)
    scene.dispose()
    expect([...counts.values()].every((count) => count === 1)).toBe(true)
  })
})
