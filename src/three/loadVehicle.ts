import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { assetUrl } from '../data/vehicles'
import type { VehicleDefinition } from '../types/vehicle'
import { createAssetRig, disposeObject, validateManifest, type AssetRig } from './assetRig'

export async function loadVehicle(vehicle: VehicleDefinition, signal: AbortSignal, progress: (fraction: number) => void, prepare?: (rig: AssetRig) => Promise<unknown>): Promise<AssetRig> {
  if (import.meta.env.DEV) {
    for (const entry of performance.getEntriesByType('mark')) {
      if (entry.name.startsWith('carvue-load:')) performance.clearMarks(entry.name)
    }
  }
  const mark = (stage: string) => {
    if (import.meta.env.DEV && !signal.aborted) performance.mark(`carvue-load:${stage}`, { detail: { vehicleId: vehicle.id } })
  }
  mark('fetch-start')
  const modelUrl = new URL(assetUrl(vehicle.asset.modelUrl), window.location.href)
  const responses = await Promise.all([
    fetch(assetUrl(vehicle.asset.manifestUrl), { signal }),
    fetch(modelUrl, { signal }),
  ])
  if (!responses.every(response => response.ok)) throw new Error('Unable to download vehicle assets.')
  const manifest: unknown = await responses[0]!.json()
  validateManifest(manifest, vehicle.id, vehicle.asset.version)
  const response = responses[1]!
  const total = Number(response.headers.get('Content-Length'))
  const reader = response.body?.getReader()
  let buffer: ArrayBuffer
  if (reader) {
    const chunks: Uint8Array[] = []
    let length = 0
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(value)
      length += value.byteLength
      if (total > 0) progress(Math.min(0.9, length / total * 0.9))
    }
    const bytes = new Uint8Array(length)
    let offset = 0
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength }
    buffer = bytes.buffer
  } else buffer = await response.arrayBuffer()
  mark('bytes-ready')
  signal.throwIfAborted()
  progress(0.92)
  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(buffer, new URL('.', modelUrl).href)
  mark('parsed')
  let rig: AssetRig | undefined
  try {
    signal.throwIfAborted()
    rig = createAssetRig(gltf.scene, manifest)
    mark('rig-ready')
    if (prepare) {
      mark('precompile-start')
      const pendingRig = rig
      const release = () => pendingRig.dispose()
      signal.addEventListener('abort', release, { once: true })
      try {
        await prepare(rig)
        signal.throwIfAborted()
        mark('precompile-ready')
      } finally {
        signal.removeEventListener('abort', release)
      }
    }
    progress(0.98)
    return rig
  } catch (error) {
    if (rig) rig.dispose()
    else disposeObject(gltf.scene)
    throw error
  }
}
