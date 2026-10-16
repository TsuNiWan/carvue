import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'

const [input, output] = process.argv.slice(2)
assert.ok(input && output, 'Usage: node scripts/modeling/pack-model.mjs source.glb packed.glb')
assert.notEqual(path.resolve(input), path.resolve(output), 'Keep the uncompressed export as a separate source asset.')
await Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready])
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder,
})
const source = await readFile(input)
const document = await io.readBinary(source)
assert.equal(document.getRoot().listExtensionsUsed().some(extension => extension.extensionName === 'EXT_meshopt_compression'), false, 'Input must be the original uncompressed export.')
const originalJSON = (await io.writeJSON(document)).json
const meshes = document.getRoot().listMeshes()

// Omit quantize/reorder/filter transforms: retain the original attribute precision.
document.createExtension(EXTMeshoptCompression).setRequired(true)
  .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE })
const packed = await io.writeBinary(document)
const decoded = await io.readBinary(packed)
const decodedJSON = (await io.writeJSON(decoded)).json
for (const key of ['nodes', 'scenes', 'materials']) assert.deepEqual(decodedJSON[key], originalJSON[key], `${key} changed during packing`)
const decodedMeshes = decoded.getRoot().listMeshes()
assert.equal(decodedMeshes.length, meshes.length)
let primitives = 0
let attributes = 0
let triangles = 0
for (let index = 0; index < meshes.length; index++) {
  const original = meshes[index].listPrimitives()
  const actual = decodedMeshes[index].listPrimitives()
  assert.equal(actual.length, original.length)
  for (let primitive = 0; primitive < original.length; primitive++) {
    const before = original[primitive]
    const after = actual[primitive]
    assert.equal(after.getMode(), before.getMode())
    assert.equal(after.getMaterial()?.getName(), before.getMaterial()?.getName())
    assert.deepEqual(after.listSemantics(), before.listSemantics())
    for (const semantic of before.listSemantics()) {
      assert.deepEqual(after.getAttribute(semantic).getArray(), before.getAttribute(semantic).getArray(), `${meshes[index].getName()}/${semantic} changed`)
      attributes++
    }
    const beforeIndices = before.getIndices()?.getArray()
    const afterIndices = after.getIndices()?.getArray()
    assert.equal(afterIndices?.length, beforeIndices?.length)
    if (beforeIndices && before.getMode() === 4) {
      // The triangle codec may rotate each triangle's corners without changing winding.
      for (let i = 0; i < beforeIndices.length; i += 3) {
        const a = Array.from(beforeIndices.slice(i, i + 3))
        const b = Array.from(afterIndices.slice(i, i + 3))
        assert.ok([0, 1, 2].some(offset => a.every((value, corner) => value === b[(corner + offset) % 3])), 'Triangle shape or winding changed')
      }
      triangles += beforeIndices.length / 3
    } else assert.deepEqual(afterIndices, beforeIndices)
    primitives++
  }
}
await mkdir(path.dirname(path.resolve(output)), { recursive: true })
await writeFile(output, packed)
const hash = bytes => createHash('sha256').update(bytes).digest('hex')
const report = {
  source: { path: input, bytes: source.length, sha256: hash(source) },
  packed: { path: output, bytes: packed.length, sha256: hash(packed) },
  ratio: packed.length / source.length, meshes: meshes.length, primitives, attributes, triangles,
  checks: ['Exact vertex attributes', 'Triangle corners and winding', 'Scene nodes and transforms', 'Material definitions', 'Joint names and identity extras'],
  checkedAt: new Date().toISOString(),
}
await writeFile(`${output}.compression.json`, JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
