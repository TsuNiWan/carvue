import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { DoubleSide, OrthographicCamera, Raycaster, Vector2, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const file = process.argv[2] ?? 'public/models/suv-02/1.1.0/vehicle.glb';
const output = process.argv[3] ?? 'assets/source/suv-02/qa/ninth-surface-diagnosis.json';
const bytes = await readFile(file);
const { scene } = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
scene.traverse(object => { if (object.isMesh) object.material.side = DoubleSide; });
scene.updateMatrixWorld(true);
const views = [
  { name: 'headlamp', camera: [4.3, 2.3, 5.6], target: [.7, 1.04, 2.04], scale: 1.55,
    pixels: [[553,451],[276,389],[850,610],[698,457],[525,446],[591,458],[851,583]] },
  { name: 'window', camera: [4.8,2.7,-.65], target: [.72,1.40,-.62], scale: 2.70,
    pixels: [[1086,563],[1121,551],[1159,549],[1185,547],[1330,745]] },
  { name: 'tail', camera: [4.3,1.8,-5.6], target: [.7,1.05,-2.16], scale: 1.45,
    pixels: [[349,627],[338,590],[687,402],[651,389],[380,233],[675,435],[668,466],[685,370],
      [707,366],[701,377],[699,357]] },
];
const raycaster = new Raycaster();
const results = [];
for (const view of views) {
  const camera = new OrthographicCamera(-view.scale/2, view.scale/2,
    view.scale*900/1400/2, -view.scale*900/1400/2, .001, 100);
  camera.position.set(...view.camera);
  camera.lookAt(new Vector3(...view.target));
  camera.updateMatrixWorld(true);
  for (const pixel of view.pixels) {
    raycaster.setFromCamera(new Vector2(2*pixel[0]/1400-1, 1-2*pixel[1]/900), camera);
    const hits = raycaster.intersectObject(scene, true).slice(0, 6);
    results.push({ view: view.name, pixel, hits: hits.map(hit => ({
      mesh: hit.object.name, material: hit.object.material.name, point: hit.point.toArray(),
      distance: hit.distance, faceNormal: hit.face.normal.toArray(), normal: hit.normal?.toArray(),
      triangle: ['a','b','c'].map(key => new Vector3().fromBufferAttribute(
        hit.object.geometry.attributes.position, hit.face[key]).applyMatrix4(hit.object.matrixWorld).toArray()),
    })) });
  }
}
await writeFile(output, JSON.stringify({ file, sha256: createHash('sha256').update(bytes).digest('hex'), results }, null, 2));
console.log(JSON.stringify(results.map(r => ({view:r.view,pixel:r.pixel,hit:r.hits[0]})), null, 2));
