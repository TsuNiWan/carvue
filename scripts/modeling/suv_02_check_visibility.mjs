import { readFile, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { DoubleSide, Quaternion, Raycaster, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const file = process.argv[2] ?? 'public/models/suv-02/1.1.0/vehicle.glb';
const output = process.argv[3] ?? 'assets/source/suv-02/qa/visibility-check.json';
const bytes = await readFile(file);
const manifest = JSON.parse(await readFile('public/models/suv-02/1.1.0/manifest.json', 'utf8'));
const loaded = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
const scene = loaded.scene;
scene.traverse(object => {
  if (object.isMesh) for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
    material.side = DoubleSide;
  }
});
scene.updateMatrixWorld(true);
const raycaster = new Raycaster();
const rows = [];
const opticalRows = [];
if (process.argv[4]) {
  const opticalSamples = JSON.parse(await readFile(process.argv[4], 'utf8'));
  for (const sample of opticalSamples) {
    const normal = new Vector3(...sample.normal).normalize();
    const position = new Vector3(...sample.surface);
    raycaster.set(position.clone().addScaledVector(normal, .4), normal.clone().negate());
    const hits = raycaster.intersectObject(scene, true);
    const lens = hits.find(hit => hit.object.material.name === sample.lens);
    const blockingPaint = hits.find(hit => /^(BodyPaint|InnerPaint)$/.test(hit.object.material.name)
      && hit.distance < .46);
    opticalRows.push({ lamp: sample.lamp, logicalXY: sample.logicalXY, lensFound: Boolean(lens),
      blockingPaint: blockingPaint ? { material: blockingPaint.object.material.name, mesh: blockingPaint.object.name,
        distance: blockingPaint.distance, point: blockingPaint.point.toArray(),
        triangle: ['a', 'b', 'c'].map(key => new Vector3().fromBufferAttribute(
          blockingPaint.object.geometry.getAttribute('position'), blockingPaint.face[key])
          .applyMatrix4(blockingPaint.object.matrixWorld).toArray()) } : null,
      firstHits: hits.slice(0, 6).map(hit => ({ material: hit.object.material.name, distance: hit.distance })) });
  }
}
const door = scene.getObjectByName('door_frontRight');
const innerLocal = new Vector3(1, 0, 0).applyQuaternion(door.getWorldQuaternion(new Quaternion()).invert());
const samples = [];
for (const y of [.46, .70, .96]) for (const z of [-.10, .25, .60]) {
  samples.push({ y, z, local: door.worldToLocal(new Vector3(-.77, y, z)) });
}
for (const [key, definition] of Object.entries(manifest.joints)) {
  const node = scene.getObjectByName(definition.node);
  node.quaternion.multiply(new Quaternion().setFromAxisAngle(new Vector3(...definition.axis), definition.openAngle * .5));
}
scene.updateMatrixWorld(true);
const direction = new Vector3(0, .72, 0).sub(new Vector3(-Math.sqrt(.5) * 24, 8.16, -Math.sqrt(.5) * 24)).normalize();
const innerWorld = innerLocal.applyQuaternion(door.getWorldQuaternion(new Quaternion()));
const innerRows = [];
for (const sample of samples) {
  const target = door.localToWorld(sample.local.clone());
  raycaster.set(target.clone().addScaledVector(direction, -20), direction);
  const hits = raycaster.intersectObject(door, true).filter(hit => !/Glass/.test(hit.object.material.name));
  rows.push({ sample: { y: sample.y, z: sample.z }, target: target.toArray(),
    hits: hits.slice(0, 8).map(hit => ({ material: hit.object.material.name, distance: hit.distance,
      point: hit.point.toArray(), normalDotRay: hit.face.normal.clone().transformDirection(hit.object.matrixWorld).dot(direction) })) });
  raycaster.set(target.clone().addScaledVector(innerWorld, .5), innerWorld.clone().negate());
  const innerHits = raycaster.intersectObject(door, true).filter(hit => !/Glass/.test(hit.object.material.name));
  innerRows.push({ sample: { y: sample.y, z: sample.z }, hits: innerHits.slice(0, 5).map(hit => ({
    material: hit.object.material.name, distance: hit.distance, point: hit.point.toArray() })) });
}
const record = { sha256: createHash('sha256').update(bytes).digest('hex'), file,
  scope: 'CPU rays through the half-rear orthographic view, restricted to the front-right door. Both material sides are included to distinguish occlusion from face culling.',
  opticalSamples: opticalRows, doorSamples: rows, innerDirectionWorld: innerWorld.toArray(),
  outwardNormalTowardHalfRearCamera: innerWorld.clone().negate().dot(direction.clone().negate()),
  innerFaceSamples: innerRows };
await writeFile(output, JSON.stringify(record, null, 2) + '\n');
console.log(JSON.stringify({ sha256: record.sha256, samples: rows.map(row => ({ ...row.sample,
  nearestMaterial: row.hits[0]?.material, nearestNormalDotRay: row.hits[0]?.normalDotRay })),
  innerFaceSamples: innerRows.map(row => ({ ...row.sample, nearestMaterial: row.hits[0]?.material })),
  outwardNormalTowardHalfRearCamera: record.outwardNormalTowardHalfRearCamera,
  opticalFailures: opticalRows.filter(row => !row.lensFound || row.blockingPaint),
  opticalSampleCount: opticalRows.length }, null, 2));
if (process.argv.includes('--assert-optics')) {
  assert.ok(opticalRows.length > 0, 'Optical samples must be provided before checking aperture visibility');
  assert.ok(opticalRows.every(row => row.lensFound && !row.blockingPaint),
    'Every sampled lamp ray must find its cover without body paint blocking its internal optical volume');
}
