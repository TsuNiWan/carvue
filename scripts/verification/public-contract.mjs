import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { vehicles } from '../../src/data/vehicles.ts'

const ids = ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']
assert.deepEqual(vehicles.map(vehicle => vehicle.id), ids)
assert.deepEqual((await readdir('public/models')).sort(), [...ids].sort())
for (const vehicle of vehicles) {
  for (const field of ['brand', 'trim', 'market', 'modelYear', 'sources', 'referenceDate', 'specificationVersion']) {
    assert.equal(field in vehicle, false, `Unexpected real-vehicle field: ${field}`)
  }
  assert.equal(vehicle.asset.version, '1.1.0')
  const bytes = await readFile(`public/${vehicle.asset.modelUrl}`)
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString())
  assert.equal(json.images?.length ?? 0, 0, 'No photographic textures may ship')
  assert.equal(json.nodes.find(node => node.name === 'VehicleRoot')?.extras?.vehicleId, vehicle.id)
  assert.ok(!JSON.stringify(json).includes('https://'), 'No reference URLs in model metadata')
}
const view = await readFile('src/views/VehicleDetailView.vue', 'utf8')
assert.ok(!view.includes('selected.sources'))
assert.ok(!view.includes('target="_blank"'))
console.log('Public model identity, metadata and information-panel contracts passed.')

assert.ok(!view.includes('外觀設計權利'), 'Rights review belongs in project documentation')
