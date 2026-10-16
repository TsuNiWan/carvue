import { Color, Group, MathUtils, Mesh, MeshStandardMaterial, Object3D, Quaternion, SpotLight, Texture, Vector3, type BufferGeometry, type Material } from 'three'
import { acceleratedRaycast, disposeBoundsTree, MeshBVH } from 'three-mesh-bvh'
import { createVehiclePresentation, type VehicleAssetManifest, type VehiclePresentation, type VehicleRig, type PartId, type VehicleState } from '../types/vehicle'
import { indicatorEnvelope, Transition } from './transition'

export const partIds: PartId[] = ['frontLeft', 'frontRight', 'rearLeft', 'rearRight', 'trunk']
const mechanismDuration = { door: 1.1, trunk: 1.4 }
export interface AssetRig extends VehicleRig {
  presentation: VehiclePresentation
  framing: VehicleAssetManifest['framing']
  hotspots: { id: VehicleAssetManifest['hotspots'][number]['id']; anchor: Object3D; position: Vector3; label: string }[]
}

export function disposeObject(root: Object3D): void {
  const geometries = new Set<BufferGeometry>()
  const materials = new Set<Material>()
  const textures = new Set<Texture>()
  const images = new Set<{ close?: () => void }>()
  root.traverse(object => {
    if (!(object instanceof Mesh)) return
    geometries.add(object.geometry)
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      materials.add(material)
      for (const value of Object.values(material)) if (value instanceof Texture) textures.add(value)
    }
  })
  for (const texture of textures) {
    if (Array.isArray(texture.image)) texture.image.forEach(image => images.add(image))
    else if (texture.image) images.add(texture.image)
    texture.dispose()
  }
  images.forEach(image => image.close?.())
  materials.forEach(material => material.dispose())
  geometries.forEach(geometry => { disposeBoundsTree.call(geometry); geometry.dispose() })
  root.clear()
}

export function validateManifest(value: unknown, vehicleId: string, version: string): asserts value is VehicleAssetManifest {
  const manifest = value as VehicleAssetManifest
  const vector = (input: unknown): input is [number, number, number] => Array.isArray(input) && input.length === 3 && input.every(Number.isFinite)
  if (!manifest || manifest.schemaVersion !== 1 || manifest.vehicleId !== vehicleId || manifest.assetVersion !== version || manifest.units !== 'meter' || manifest.forward !== '+Z') throw new Error('Invalid model identity or coordinate convention.')
  if (!manifest.framing || !vector(manifest.framing.target) || !vector(manifest.framing.direction) || Math.hypot(...manifest.framing.direction) < 0.001 || !Number.isFinite(manifest.framing.distance) || manifest.framing.distance <= 0) throw new Error('Invalid model camera framing.')
  for (const id of partIds) {
    const joint = manifest.joints?.[id]
    if (!joint || !joint.node || !vector(joint.axis) || new Vector3(...joint.axis).length() < 0.99 || !Number.isFinite(joint.openAngle) || Math.abs(joint.openAngle) < 0.1) throw new Error(`Invalid joint: ${id}`)
  }
  if (manifest.frontWheels?.length !== 2 || manifest.frontWheels.some(node => typeof node !== 'string')) throw new Error('Two front wheel pivots are required.')
  for (const group of ['head', 'tail', 'left', 'right'] as const) if (!Array.isArray(manifest.lights?.[group]) || !manifest.lights[group].length || manifest.lights[group].some(name => typeof name !== 'string')) throw new Error(`Missing light group: ${group}`)
  if (manifest.headlights?.length !== 2 || manifest.headlights.some(light => !vector(light.position) || !vector(light.target))) throw new Error('Two headlight positions are required.')
  if (!Array.isArray(manifest.hotspots) || manifest.hotspots.some(hotspot => ![...partIds, 'headlights'].includes(hotspot.id) || !hotspot.node || !hotspot.label || !vector(hotspot.position))) throw new Error('Invalid model hotspots.')
}

export function createAssetRig(root: Group, manifest: VehicleAssetManifest): AssetRig {
  const identity = root.getObjectByName('VehicleRoot')?.userData
  if (identity?.vehicleId !== manifest.vehicleId || identity?.assetVersion !== manifest.assetVersion) throw new Error('Model identity does not match its manifest.')
  const node = (name: string) => {
    const object = root.getObjectByName(name)
    if (!object) throw new Error(`Model node is missing: ${name}`)
    return object
  }
  const joints = Object.fromEntries(partIds.map(id => [id, node(manifest.joints[id].node)])) as Record<PartId, Object3D>
  const frontWheels = manifest.frontWheels.map(node)
  if (new Set([...Object.values(joints), ...frontWheels]).size !== 7) throw new Error('Movable components must have independent pivots.')
  const materialMap = new Map<string, Set<MeshStandardMaterial>>()
  root.traverse(object => {
    if (!(object instanceof Mesh)) return
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    // Blended glazing must not cast an opaque silhouette onto other windows.
    object.castShadow = materials.some(material => !material.transparent)
    object.receiveShadow = true
    if (object.geometry.getAttribute('position')?.count) {
      // Keep render indices and material groups unchanged; only accelerate queries.
      object.geometry.boundsTree ??= new MeshBVH(object.geometry, { indirect: true })
      object.raycast = acceleratedRaycast
    }
    for (const material of materials) {
      if (material instanceof MeshStandardMaterial) {
        // Dark glazing occludes farther glass; clear lamp covers remain blended.
        if (material.transparent) material.depthWrite = material.opacity >= 0.5
        if (!materialMap.has(material.name)) materialMap.set(material.name, new Set())
        materialMap.get(material.name)!.add(material)
      }
    }
  })
  const lightMaterials = (names: string[]) => [...new Set(names.flatMap(name => {
    const material = materialMap.get(name)
    if (!material) throw new Error(`Light material is missing: ${name}`)
    return [...material]
  }))]
  const lights = { head: lightMaterials(manifest.lights.head), tail: lightMaterials(manifest.lights.tail), left: lightMaterials(manifest.lights.left), right: lightMaterials(manifest.lights.right) }
  const claimed = new Set<MeshStandardMaterial>()
  for (const [id, materials] of Object.entries(lights)) for (const material of materials) {
    if (claimed.has(material)) throw new Error('Light groups must use independent materials.')
    claimed.add(material)
    if (material.emissive.equals(new Color(0))) material.emissive.set(id === 'head' ? '#eff5ff' : id === 'tail' ? '#ff1810' : '#ff9e16')
    // Keep unlit diffusers distinct from emitted light under the studio lighting.
    if (id === 'head') material.color.multiplyScalar(0.2)
    material.emissiveIntensity = 0
  }
  const hotspots = manifest.hotspots.map(hotspot => ({ id: hotspot.id, anchor: node(hotspot.node), position: new Vector3(...hotspot.position), label: hotspot.label }))
  const closed = new Map([...Object.values(joints), ...frontWheels].map(object => [object, object.quaternion.clone()]))
  const axes = Object.fromEntries(partIds.map(id => [id, new Vector3(...manifest.joints[id].axis).normalize()])) as Record<PartId, Vector3>
  const transitions = Object.fromEntries(partIds.map(id => [id, new Transition()])) as Record<PartId, Transition>
  const headTransition = new Transition()
  const steeringTransition = new Transition()
  const rotation = new Quaternion()
  const wheelAxis = new Vector3(0, 1, 0)
  const presentation = createVehiclePresentation()
  const spots = manifest.headlights.map(definition => {
    const light = new SpotLight('#eff5ff', 0, 13, Math.PI / 5, 0.65, 1.5)
    light.position.fromArray(definition.position)
    light.target.position.fromArray(definition.target)
    root.add(light, light.target)
    return light
  })
  let disposed = false
  return {
    root, joints, frontWheels, lights, hotspots, presentation, framing: manifest.framing,
    update(state: VehicleState, delta: number, elapsed: number, reducedMotion = false) {
      for (const id of partIds) {
        const target = id === 'trunk' ? state.trunk : state.doors[id]
        // Deliberate mechanism demonstrations retain their travel time for either preference.
        const progress = transitions[id].update(Number(target), delta, id === 'trunk' ? mechanismDuration.trunk : mechanismDuration.door)
        presentation.parts[id] = progress
        joints[id].quaternion.copy(closed.get(joints[id])!).multiply(rotation.setFromAxisAngle(axes[id], manifest.joints[id].openAngle * progress))
      }
      const steering = steeringTransition.update(MathUtils.clamp(state.steeringAngle, -30, 30), delta, reducedMotion ? 0.1 : 0.16, 60)
      presentation.steeringAngle = steering
      for (const wheel of frontWheels) wheel.quaternion.copy(closed.get(wheel)!).multiply(rotation.setFromAxisAngle(wheelAxis, -MathUtils.degToRad(steering)))
      const brightness = headTransition.update(Number(state.headlights), delta, reducedMotion ? 0.1 : 0.25)
      presentation.headlights = brightness
      lights.head.forEach(material => { material.emissiveIntensity = brightness * 3.2 })
      lights.tail.forEach(material => { material.emissiveIntensity = brightness * 2.2 })
      spots.forEach(light => { light.intensity = brightness * 16 })
      const blink = indicatorEnvelope(elapsed) * 3.4
      lights.left.forEach(material => { material.emissiveIntensity = state.signal === 'left' || state.signal === 'hazard' ? blink : 0 })
      lights.right.forEach(material => { material.emissiveIntensity = state.signal === 'right' || state.signal === 'hazard' ? blink : 0 })
    },
    dispose() { if (disposed) return; disposed = true; disposeObject(root) },
  }
}
