import type { VehicleDefinition } from '../types/vehicle'

const asset = (id: string): VehicleDefinition['asset'] => ({
  version: '1.1.0', modelUrl: `models/${id}/1.1.0/vehicle.glb`,
  manifestUrl: `models/${id}/1.1.0/manifest.json`, posterUrl: `previews/${id}.webp`, status: 'verified',
})
const capabilities = (): VehicleDefinition['capabilities'] => ({ doors: ['frontLeft', 'frontRight', 'rearLeft', 'rearRight'], trunk: true, headlights: true, signals: true, steering: true })

export const vehicles: VehicleDefinition[] = [
  {
    id: 'sedan-01', name: '都會轎車',
    bodyStyle: 'sedan', color: '#546175', length: 4.63, width: 1.78, height: 1.435, wheelbase: 2.7,
    tagline: '熟悉的經典，從每個角度重新認識。',
    asset: asset('sedan-01'), capabilities: capabilities(),
  },
  {
    id: 'suv-01', name: '家庭休旅',
    bodyStyle: 'suv', color: '#697e7a', length: 4.69, width: 1.865, height: 1.68, wheelbase: 2.7,
    tagline: '開闊的視野，容納生活的每一面。',
    asset: asset('suv-01'), capabilities: capabilities(),
  },
  {
    id: 'sedan-02', name: '流線轎車',
    bodyStyle: 'sedan', color: '#9f172b', length: 4.66, width: 1.795, height: 1.44, wheelbase: 2.725,
    tagline: '沿著流動的光影，發現純粹的線條。',
    asset: asset('sedan-02'), capabilities: capabilities(),
  },
  {
    id: 'suv-02', name: '都會休旅',
    bodyStyle: 'suv', color: '#426a80', length: 4.755, width: 1.92, height: 1.66, wheelbase: 2.865,
    tagline: '鮮明輪廓，展開動感休旅的新視野。',
    asset: asset('suv-02'), capabilities: capabilities(),
  },
  {
    id: 'sedan-03', name: '行政轎車',
    bodyStyle: 'sedan', color: '#929da6', length: 4.751, width: 1.82, height: 1.44, wheelbase: 2.865,
    tagline: '細膩的比例，讓每一次凝視都有發現。',
    asset: asset('sedan-03'), capabilities: capabilities(),
  },
]

export function assetUrl(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`
}
