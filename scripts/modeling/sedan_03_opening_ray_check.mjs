import { readFileSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrthographicCamera, Quaternion, Raycaster, Vector2, Vector3 } from 'three'

const file = readFileSync('assets/source/sedan-03/vehicle.raw.glb')
const gltf = await new GLTFLoader().parseAsync(file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength), '')
const manifest = JSON.parse(readFileSync('public/models/sedan-03/1.1.0/manifest.json', 'utf8'))
const joint = manifest.joints.rearRight
gltf.scene.getObjectByName(joint.node).quaternion.multiply(new Quaternion().setFromAxisAngle(new Vector3(...joint.axis), joint.openAngle))
gltf.scene.updateMatrixWorld(true)
const camera = new OrthographicCamera(-3, 3, 3 * 900 / 1400, -3 * 900 / 1400, .1, 1000)
camera.position.set(-24 / Math.SQRT2, 8.16, -24 / Math.SQRT2)
camera.lookAt(0, .72, 0)
camera.updateMatrixWorld(true)
const samples = []
let selected = null
for (const x of [632, 640, 648, 656, 664, 672]) {
  for (const y of [560, 568, 576, 584, 592, 600]) {
    const ray = new Raycaster()
    ray.setFromCamera(new Vector2(2 * x / 1400 - 1, 1 - 2 * y / 900), camera)
    const hits = ray.intersectObject(gltf.scene, true).slice(0, 4)
    if (x === 648 && y === 576) selected = hits[0]
    samples.push({ pixel: [x, y], hits: hits.map(hit => ({ object: hit.object.name,
      material: hit.object.material.name, point: hit.point.toArray(),
      normal: hit.face.normal.clone().transformDirection(hit.object.matrixWorld).toArray() })) })
  }
}
const geometry = selected.object.geometry
const positions = geometry.attributes.position
const indices = geometry.index.array
const adjacency = Array.from({ length: positions.count }, () => [])
for (let i = 0; i < indices.length; i += 3) {
  const a = indices[i], b = indices[i + 1], c = indices[i + 2]
  adjacency[a].push(b, c)
  adjacency[b].push(a, c)
  adjacency[c].push(a, b)
}
const component = new Set([selected.face.a])
const queue = [selected.face.a]
for (let i = 0; i < queue.length; i++) {
  for (const neighbor of adjacency[queue[i]]) {
    if (!component.has(neighbor)) { component.add(neighbor); queue.push(neighbor) }
  }
}
const points = [...component].map(index => new Vector3().fromBufferAttribute(positions, index).applyMatrix4(selected.object.matrixWorld))
const radiusErrors = points.map(p => Math.abs(Math.hypot(p.y - .3266, p.z + 1.4325) - .382))
const componentResult = { selectedPixel: [648, 576], object: selected.object.name,
  material: selected.object.material.name, connectedVertices: component.size,
  bounds: { min: ['x', 'y', 'z'].map(axis => Math.min(...points.map(p => p[axis]))),
    max: ['x', 'y', 'z'].map(axis => Math.max(...points.map(p => p[axis]))) },
  maximumAnalyticWheelhouseRadiusError: Math.max(...radiusErrors),
  sourceMatch: 'build_sedan_03.py WheelhouseLiner, fixed root, radius 0.382 m; inspect measured bounds and source clearances separately',
  interpretation: 'The sampled arc belongs to the connected fixed wheelhouse sheet around the complete upper rear wheel. Connectivity alone does not prove sufficient body clearance; use the same-version source clearance and rendered evidence.' }
const result = { rawSha256: createHash('sha256').update(file).digest('hex'),
  pose: 'rearRight fully open', image: 'open-rearRight.png', component: componentResult, samples }
writeFileSync('assets/source/sedan-03/qa/opening-ray-check.json', JSON.stringify(result, null, 2))
console.log(componentResult)
