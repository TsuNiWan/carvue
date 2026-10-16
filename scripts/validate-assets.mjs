import { readFile, stat, mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { createHash } from 'node:crypto'

const project = fileURLToPath(new URL('../', import.meta.url))
const ids = process.argv.filter(argument => argument.startsWith('--vehicle=')).map(argument => argument.slice(10))
const vehicles = ids.length ? ids : ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']
const version = process.argv.find(argument => argument.startsWith('--version='))?.slice(10) ?? '1.1.0'
const report = { checkedAt: new Date().toISOString(), limitBytes: 12 * 1024 * 1024, vehicles: [], errors: [] }
const requireValue = (condition, message) => { if (!condition) throw new Error(message) }
for (const id of vehicles) {
  try {
    requireValue(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id), 'Invalid vehicle ID.')
    requireValue(/^\d+\.\d+\.\d+$/.test(version), 'Invalid asset version. Use a numeric major.minor.patch version.')
    const directory = path.join(project, 'public/models', id, version)
    const data = await readFile(path.join(directory, 'vehicle.glb'))
    const manifest = JSON.parse(await readFile(path.join(directory, 'manifest.json'), 'utf8'))
    requireValue(data.length > 20 && data.toString('ascii', 0, 4) === 'glTF' && data.readUInt32LE(4) === 2 && data.readUInt32LE(8) === data.length, 'Invalid GLB container.')
    requireValue(data.readUInt32LE(16) === 0x4e4f534a, 'Missing GLB JSON chunk.')
    const gltf = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)).toString('utf8'))
    const nodes = new Map(gltf.nodes.map(node => [node.name, node]))
    const materials = new Set(gltf.materials.map(material => material.name))
    const identity = nodes.get('VehicleRoot')?.extras
    requireValue(manifest.vehicleId === id && manifest.assetVersion === version && manifest.units === 'meter' && manifest.forward === '+Z', 'Manifest identity/convention mismatch.')
    requireValue(identity?.vehicleId === id && identity.assetVersion === manifest.assetVersion, 'GLB identity mismatch.')
    const vector = value => Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)
    requireValue(manifest.framing && vector(manifest.framing.target) && vector(manifest.framing.direction) && Math.hypot(...manifest.framing.direction) > 0.001 && Number.isFinite(manifest.framing.distance) && manifest.framing.distance > 0, 'Invalid camera framing.')
    const pivots = []
    for (const part of ['frontLeft', 'frontRight', 'rearLeft', 'rearRight', 'trunk']) {
      const joint = manifest.joints[part]
      requireValue(joint && nodes.has(joint.node) && nodes.get(joint.node).children?.length, `Missing movable part ${part}.`)
      requireValue(Array.isArray(joint.axis) && joint.axis.length === 3 && joint.axis.every(Number.isFinite) && Math.abs(Math.hypot(...joint.axis) - 1) < 0.0001 && Math.abs(joint.openAngle) > 0.1, `Invalid hinge ${part}.`)
      pivots.push(joint.node)
    }
    requireValue(manifest.frontWheels.length === 2 && manifest.frontWheels.every(name => nodes.has(name)), 'Missing front wheel pivots.')
    requireValue(new Set([...pivots, ...manifest.frontWheels]).size === 7, 'Pivots must be independent.')
    for (const bank of ['head', 'tail', 'left', 'right']) requireValue(manifest.lights[bank]?.length && manifest.lights[bank].every(name => materials.has(name)), `Missing ${bank} lamp material.`)
    requireValue(manifest.hotspots.every(hotspot => nodes.has(hotspot.node)), 'Invalid hotspot anchor.')
    const external = [...new Set([...(gltf.images ?? []), ...(gltf.buffers ?? [])].flatMap(item => item.uri && !item.uri.startsWith('data:') ? [item.uri] : []))]
    let bytes = data.length
    for (const uri of external) {
      const resource = path.resolve(directory, decodeURIComponent(uri))
      requireValue(resource.startsWith(directory + path.sep), 'Asset dependency must be bundled in its model directory.')
      bytes += (await stat(resource)).size
    }
    requireValue(bytes <= report.limitBytes, 'Vehicle exceeds the 12 MiB asset budget.')
    requireValue((await stat(path.join(project, 'public/previews', `${id}.webp`))).size > 0, 'Missing generated preview.')
    const triangles = (gltf.meshes ?? []).flatMap(mesh => mesh.primitives).reduce((total, primitive) => total + (gltf.accessors[primitive.indices ?? primitive.attributes.POSITION]?.count ?? 0) / 3, 0)
    report.vehicles.push({ id, version: manifest.assetVersion, bytes, triangles, nodes: gltf.nodes.length, materials: gltf.materials.length, sha256: createHash('sha256').update(data).digest('hex'), external })
    process.stdout.write(`${id}: ${bytes.toLocaleString('en-US')} bytes, ${Math.round(triangles).toLocaleString('en-US')} triangles, contract passed\n`)
  } catch (error) {
    report.errors.push({ id, message: error.message })
    process.stderr.write(`${id}: ${error.message}\n`)
  }
}
if (process.argv.includes('--report')) {
  const directory = path.join(project, 'artifacts/product')
  await mkdir(directory, { recursive: true })
  await writeFile(path.join(directory, 'asset-validation.json'), JSON.stringify(report, null, 2))
}
if (report.errors.length) process.exitCode = 1
