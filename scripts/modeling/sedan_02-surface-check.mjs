import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrthographicCamera, Raycaster, Vector2, Vector3 } from 'three'

const bytes = readFileSync('assets/source/sedan-02/vehicle.raw.glb')
const { scene } = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')
scene.updateMatrixWorld(true)
// These camera rays reproduce the visible holes in the eighth detail review.
const camera = new OrthographicCamera(-1.23 / 2, 1.23 / 2, .82 / 2, -.82 / 2, .01, 100)
camera.position.set(2.6, 1.55, -4.1)
camera.lookAt(new Vector3(.60, .90, -2.19))
camera.updateMatrixWorld(true)
const samples = [[725, 320], [720, 323], [730, 322]].map(([x, y]) => {
  const ray = new Raycaster()
  ray.setFromCamera(new Vector2(x / 1200 * 2 - 1, 1 - y / 800 * 2), camera)
  const hits = ray.intersectObject(scene, true).slice(0, 4)
  return { pixel: [x, y], closed: Boolean(hits[0] && hits[0].point.z < -1.89),
    hits: hits.map(hit => ({ object: hit.object.name, material: hit.object.material.name, point: hit.point.toArray() })) }
})
const report = { checkedAt: new Date().toISOString(), rawSha256: createHash('sha256').update(bytes).digest('hex'),
  method: 'Three fixed camera rays at the observed tail upper-edge hole; the first intersection must be on the exterior lamp or panel, ahead of the luggage compartment.',
  passed: samples.every(sample => sample.closed), samples }
writeFileSync('assets/source/sedan-02/qa/surface-check.json', JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
if (!process.argv.includes('--diagnose')) assert.ok(report.passed, 'The tail upper edge must not expose the luggage compartment')
