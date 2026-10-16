import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { vehicles } from '../../src/data/vehicles.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const id = process.argv[2] ?? 'sedan-01';
const vehicle = vehicles.find(vehicle => vehicle.id === id);
assert.ok(vehicle, `Unknown vehicle: ${id}`);
const assetPath = path.join(root, 'public/models', id, '1.1.0');
const manifest = JSON.parse(await readFile(path.join(assetPath, 'manifest.json'), 'utf8'));
const buffer = await readFile(path.join(assetPath, 'vehicle.glb'));
assert.equal(buffer.toString('ascii', 0, 4), 'glTF');
assert.equal(buffer.readUInt32LE(4), 2);
assert.equal(buffer.readUInt32LE(8), buffer.length);
const document = JSON.parse(buffer.subarray(20, 20 + buffer.readUInt32LE(12)).toString());
const identities = document.nodes.filter(node => node.extras?.vehicleId === id);
assert.equal(identities.length, 1, 'The model must have exactly one identified vehicle root');
assert.equal(identities[0].extras.assetVersion, manifest.assetVersion);
assert.equal(manifest.vehicleId, id);
for (const joint of Object.values(manifest.joints)) {
  assert.equal(document.nodes.filter(node => node.name === joint.node).length, 1);
  assert.ok(Number.isFinite(joint.openAngle) && Math.abs(joint.openAngle) > 0);
  assert.ok(Math.abs(Math.hypot(...joint.axis) - 1) < 1e-6);
}
for (const group of Object.values(manifest.lights)) {
  for (const name of group) {
    const material = document.materials.find(material => material.name === name);
    assert.ok(material, `Missing light material: ${name}`);
    assert.ok(material.emissiveFactor?.some(channel => channel > 0), `${name} must retain a nonzero emission color`);
  }
}
assert.equal(manifest.frontWheels.length, 2);
assert.ok(buffer.length <= 12 * 1024 * 1024, 'The complete embedded asset must be at most 12 MiB');
assert.equal(document.images?.length ?? 0, 0, 'The authored vehicle does not embed manufacturer photographs');
const loaded = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength), '');
loaded.scene.updateMatrixWorld(true);
const bounds = new Box3().setFromObject(loaded.scene);
const size = bounds.getSize(new Vector3());
assert.ok(Math.abs(bounds.min.y) <= .025, 'Y must be up, with wheels at ground level');
assert.ok(Math.abs(size.y - vehicle.height) <= .045, 'Overall height must match the vehicle within 45 mm');
assert.ok(Math.abs(size.z - vehicle.length) <= .08, 'Overall length must match the vehicle within 80 mm');
assert.ok(size.x >= vehicle.width - .03 && size.x <= vehicle.width + .45, 'Width includes the exterior mirrors');
const wheelbases = {};
for (const side of ['Left', 'Right']) {
  const wheel = loaded.scene.getObjectByName(`wheel_front${side}`);
  const rear = loaded.scene.getObjectByName(`wheel_rear${side}`);
  assert.ok(wheel && rear, `Missing ${side} axle reference nodes`);
  const position = wheel.getWorldPosition(new Vector3());
  const rearPosition = rear.getWorldPosition(new Vector3());
  assert.ok(position.z > 1, 'The front axle must face +Z');
  assert.ok(side === 'Left' ? position.x > 0 : position.x < 0, 'The left side must face +X');
  wheelbases[side] = position.z - rearPosition.z;
  assert.ok(Math.abs(wheelbases[side] - vehicle.wheelbase) <= .02, 'Wheelbase must match the vehicle within 20 mm');
}
let triangles = 0;
let meshes = 0;
loaded.scene.traverse(object => {
  if (!object.isMesh) return;
  meshes++;
  const positions = object.geometry.getAttribute('position');
  assert.ok(Array.from(positions.array).every(Number.isFinite));
  triangles += (object.geometry.index?.count ?? positions.count) / 3;
});
const report = { vehicleId: id, assetVersion: manifest.assetVersion, sha256: createHash('sha256').update(buffer).digest('hex'), bytes: buffer.length, meshes, triangles, min: bounds.min.toArray(), max: bounds.max.toArray(), dimensionsWithMirrors: size.toArray(), wheelbases, referenceDimensions: { length: vehicle.length, width: vehicle.width, height: vehicle.height, wheelbase: vehicle.wheelbase }, checkedAt: new Date().toISOString(), checks: ['GLB structure', 'model and manifest identity', 'joint nodes and axes', 'light emission colors', 'self-contained asset budget', 'coordinate convention', 'vehicle dimensions and wheelbase', 'finite geometry'], visualApproval: 'pending human review' };
await writeFile(path.join(root, 'assets/source', id, 'asset-validation.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
