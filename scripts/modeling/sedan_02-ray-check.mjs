import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { Raycaster, Vector3 } from 'three'

const file = readFileSync('assets/source/sedan-02/vehicle.raw.glb')
const gltf = await new GLTFLoader().parseAsync(file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength), '')
gltf.scene.updateMatrixWorld(true)
const samples = []
for (const side of [-1, 1]) {
  for (const x of [.45, .55, .64, .68, .72, .755, .79]) {
    for (const y of [.875, .90, .925, .95, .967]) {
      const ray = new Raycaster(new Vector3(side * x, y, -2.6), new Vector3(0, 0, 1), 0, .5)
      const hits = ray.intersectObject(gltf.scene, true).slice(0, 6)
      samples.push({ x: side * x, y, hits: hits.map(hit => ({
        object: hit.object.name, material: hit.object.material.name,
        position: hit.point.toArray(), normal: hit.normal?.toArray(),
        faceNormal: hit.face.normal.clone().transformDirection(hit.object.matrixWorld).toArray(),
        distance: hit.distance,
      })) })
    }
  }
}
// Test rear-facing optical faces, not concealed shell returns below the aperture.
const opticalSamples = samples.filter(sample => sample.hits.some(hit => hit.material === 'TailLensRed' && hit.faceNormal[2] < -.5))
const occlusions = opticalSamples.filter(sample => {
  const lens = sample.hits.find(hit => hit.material === 'TailLensRed' && hit.faceNormal[2] < -.5)
  return lens && sample.hits.some(hit => hit.material === 'BodyPaint' && hit.distance < lens.distance - .0005)
})
writeFileSync('assets/source/sedan-02/qa/tail-ray-check.json', JSON.stringify({
  checkedAt: new Date().toISOString(), rawSha256: createHash('sha256').update(file).digest('hex'),
  method: 'Positive Z rays against rear-facing optical faces with incidence within 60 degrees; shell returns are excluded. UV carrier visibility is checked separately during authoring.',
  passed: occlusions.length === 0, occlusionCount: occlusions.length,
  opticalSampleCount: opticalSamples.length,
  shellOnlySamples: samples.filter(sample => sample.hits.some(hit => hit.material === 'TailLensRed') && !opticalSamples.includes(sample)).map(({ x, y }) => ({ x, y })),
  samples,
}, null, 2))
console.log(occlusions.map(sample => ({
  x: sample.x, y: sample.y, hits: sample.hits.map(hit => `${hit.material}: ${hit.position[2].toFixed(6)}`),
})))
assert.ok(opticalSamples.length >= 40, 'The exported optical faces must cover the reference ray grid')
if (occlusions.length) process.exitCode = 1
