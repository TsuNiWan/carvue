import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { createServer } from 'vite'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { Quaternion, Vector3, SpotLight } from 'three'

const output = 'artifacts/product/m4-rig-integration'
const report = { recordedAt: new Date().toISOString(), scope: 'Actual delivery GLBs and application rig logic; CPU poses and materials, not GPU rendering.', vehicles: [], errors: [] }
const server = await createServer({
  configFile: false, cacheDir: `${output}/vite-cache`,
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, watch: null, hmr: false, preTransformRequests: false }, appType: 'custom',
})
const near = (actual, expected, message) => assert.ok(Math.abs(actual - expected) < 1e-6, `${message}: ${actual} != ${expected}`)
try {
  const { createAssetRig, validateManifest, partIds } = await server.ssrLoadModule('/src/three/assetRig.ts')
  const { createVehicleState } = await server.ssrLoadModule('/src/types/vehicle.ts')
  for (const vehicle of ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']) {
    let rig
    const entry = { vehicle, reversals: [], lighting: [], steering: [] }
    try {
      const bytes = await readFile(`public/models/${vehicle}/1.1.0/vehicle.glb`)
      const manifest = JSON.parse(await readFile(`public/models/${vehicle}/1.1.0/manifest.json`, 'utf8'))
      entry.sha256 = createHash('sha256').update(bytes).digest('hex')
      validateManifest(manifest, vehicle, '1.1.0')
      const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')
      rig = createAssetRig(gltf.scene, manifest)
      const closed = Object.fromEntries(partIds.map(part => [part, rig.joints[part].quaternion.clone()]))
      const wheelClosed = rig.frontWheels.map(wheel => wheel.quaternion.clone())
      const reset = () => { const state = createVehicleState(); rig.update(state, 10, 0); return state }
      const set = (state, part, value) => { if (part === 'trunk') state.trunk = value; else state.doors[part] = value }
      for (const reduced of [false, true]) for (const part of partIds) for (const fraction of [0.25, 0.5, 0.75]) {
        const duration = part === 'trunk' ? 1.4 : 1.1
        const state = reset()
        set(state, part, true)
        while (rig.presentation.parts[part] < fraction) rig.update(state, 0.001, 0, reduced)
        const reached = rig.presentation.parts[part]
        const pose = rig.joints[part].quaternion.clone()
        assert.ok(reached < fraction + 0.004)
        set(state, part, false)
        rig.update(state, 0, 0, reduced)
        near(rig.joints[part].quaternion.angleTo(pose), 0, 'Opening reversal continuity')
        rig.update(state, duration * reached / 2, 0, reduced)
        near(rig.presentation.parts[part], reached / 2, 'Remaining travel midpoint')
        rig.update(state, duration * reached / 2 + 1e-8, 0, reduced)
        near(rig.presentation.parts[part], 0, 'Closed progress')
        near(rig.joints[part].quaternion.angleTo(closed[part]), 0, 'Exact imported closed pose')
        set(state, part, true)
        rig.update(state, duration, 0, reduced)
        const open = rig.joints[part].quaternion.clone()
        set(state, part, false)
        while (rig.presentation.parts[part] > fraction) rig.update(state, 0.001, 0, reduced)
        const closingProgress = rig.presentation.parts[part]
        const closingPose = rig.joints[part].quaternion.clone()
        set(state, part, true)
        rig.update(state, 0, 0, reduced)
        near(rig.joints[part].quaternion.angleTo(closingPose), 0, 'Closing reversal continuity')
        rig.update(state, duration * (1 - closingProgress) + 1e-8, 0, reduced)
        near(rig.joints[part].quaternion.angleTo(open), 0, 'Exact reopened pose')
        entry.reversals.push({ part, reduced, fraction, reached, closingProgress, closed: true, reopened: true })
      }
      for (const reduced of [false, true]) {
        const state = reset()
        const half = reduced ? 0.05 : 0.125
        state.headlights = true
        rig.update(state, half, 0, reduced)
        for (const material of rig.lights.head) near(material.emissiveIntensity, 1.6, 'Headlight midpoint')
        for (const material of rig.lights.tail) near(material.emissiveIntensity, 1.1, 'Tail light midpoint')
        const spots = rig.root.children.filter(child => child instanceof SpotLight)
        assert.equal(spots.length, 2)
        for (const light of spots) near(light.intensity, 8, 'Scene light midpoint')
        state.headlights = false
        rig.update(state, 0, 0, reduced)
        near(rig.presentation.headlights, 0.5, 'Lamp reversal continuity')
        rig.update(state, half, 0, reduced)
        for (const material of [...rig.lights.head, ...rig.lights.tail]) near(material.emissiveIntensity, 0, 'Lamp off')
        for (const light of spots) near(light.intensity, 0, 'Scene light off')
        entry.lighting.push({ reduced, midpoint: 0.5, spots: spots.length, reversedToOff: true })
      }
      for (const signal of ['left', 'right', 'hazard', 'off']) {
        const state = reset()
        state.signal = signal
        for (const elapsed of [0.025, 0.1, 0.425, 0.6]) {
          rig.update(state, 0, elapsed)
          const amplitude = elapsed === 0.6 ? 0 : elapsed === 0.1 ? 3.4 : 1.7
          for (const bank of ['left', 'right']) for (const material of rig.lights[bank]) near(material.emissiveIntensity, signal === bank || signal === 'hazard' ? amplitude : 0, 'Independent signal bank')
        }
      }
      for (const reduced of [false, true]) for (const angle of [-30, 0, 30]) {
        const state = reset()
        state.steeringAngle = angle
        rig.update(state, 0.16, 0, reduced)
        near(rig.presentation.steeringAngle, angle, 'Steering target')
        rig.frontWheels.forEach((wheel, index) => {
          const expected = wheelClosed[index].clone().multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), -angle * Math.PI / 180))
          near(wheel.quaternion.angleTo(expected), 0, 'Wheel local-axis pose')
        })
        entry.steering.push({ reduced, angle, bothWheelsPassed: true })
      }
      entry.status = 'passed'
    } catch (error) {
      entry.status = 'failed'
      report.errors.push({ vehicle, message: error.stack ?? String(error) })
    } finally { rig?.dispose() }
    report.vehicles.push(entry)
    console.log(JSON.stringify({ vehicle, status: entry.status, reversalCases: entry.reversals.length, lightingCases: entry.lighting.length, steeringCases: entry.steering.length }))
  }
} finally {
  await server.close()
  await mkdir(output, { recursive: true })
  await writeFile(`${output}/results.json`, JSON.stringify(report, null, 2))
}
assert.equal(report.errors.length, 0, JSON.stringify(report.errors))
