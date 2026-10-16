import type { Group, MeshStandardMaterial, Object3D } from 'three'

export type DoorId = 'frontLeft' | 'frontRight' | 'rearLeft' | 'rearRight'
export type Signal = 'off' | 'left' | 'right' | 'hazard'
export type PartId = DoorId | 'trunk'
export type HotspotAction = PartId | 'headlights'
export type VectorTuple = [number, number, number]

export interface VehicleDefinition {
  id: string
  name: string
  bodyStyle: 'sedan' | 'suv'
  color: string
  length: number
  width: number
  height: number
  tagline: string
  wheelbase: number
  asset: {
    version: string
    modelUrl: string
    manifestUrl: string
    posterUrl: string
    status: 'development' | 'verified'
  }
  capabilities: { doors: DoorId[]; trunk: boolean; headlights: boolean; signals: boolean; steering: boolean }
}

export interface VehicleAssetManifest {
  schemaVersion: 1
  vehicleId: string
  assetVersion: string
  units: 'meter'
  forward: '+Z'
  framing: { target: VectorTuple; direction: VectorTuple; distance: number }
  joints: Record<PartId, { node: string; axis: VectorTuple; openAngle: number }>
  frontWheels: string[]
  lights: Record<'head' | 'tail' | 'left' | 'right', string[]>
  headlights: { position: VectorTuple; target: VectorTuple }[]
  hotspots: { id: HotspotAction; node: string; position: VectorTuple; label: string }[]
}

export interface VehiclePresentation {
  parts: Record<PartId, number>
  headlights: number
  steeringAngle: number
}

export function createVehiclePresentation(): VehiclePresentation {
  return { parts: { frontLeft: 0, frontRight: 0, rearLeft: 0, rearRight: 0, trunk: 0 }, headlights: 0, steeringAngle: 0 }
}

export interface VehicleState {
  headlights: boolean
  signal: Signal
  steeringAngle: number
  doors: Record<DoorId, boolean>
  trunk: boolean
}

export interface VehicleRig {
  root: Group
  joints: Record<PartId, Object3D>
  frontWheels: Object3D[]
  readonly lights: {
    head: MeshStandardMaterial[]
    tail: MeshStandardMaterial[]
    left: MeshStandardMaterial[]
    right: MeshStandardMaterial[]
  }
  update: (state: VehicleState, delta: number, elapsed: number, reducedMotion?: boolean) => void
  dispose: () => void
}

export function createVehicleState(): VehicleState {
  return {
    headlights: false,
    signal: 'off',
    steeringAngle: 0,
    doors: { frontLeft: false, frontRight: false, rearLeft: false, rearRight: false },
    trunk: false,
  }
}
