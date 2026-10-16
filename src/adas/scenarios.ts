export type ScenarioId = 'pedestrian' | 'blindSpot' | 'parking'
export type Side = 'left' | 'right'
export type TurnSignal = 'off' | 'left' | 'right' | 'hazard'

export interface ScenarioState {
  id: ScenarioId
  progress: number
  playing: boolean
  side: Side
}

export interface ScenarioFrame {
  actor: { x: number; z: number; kind: 'pedestrian' | 'car' | 'obstacle' }
  level: 'safe' | 'notice' | 'danger'
  title: string
  description: string
  distance: number
  activeSensor: 'camera' | 'radar' | 'ultrasonic'
}

export const scenarioDefinitions: { id: ScenarioId; title: string; subtitle: string; duration: number }[] = [
  { id: 'pedestrian', title: '前方行人', subtitle: '觀察行人穿越車頭時的偵測與警示', duration: 10 },
  { id: 'blindSpot', title: '盲點鄰車', subtitle: '比較左右盲點與方向燈連動警示', duration: 12 },
  { id: 'parking', title: '倒車障礙物', subtitle: '觀察後方障礙物接近時的距離提示', duration: 10 },
]

// Distances are illustrative meters, not specifications for any vehicle.
export const scenarioZones = {
  cameraHalfWidth: 3,
  cameraDepth: 8,
  pedestrianDangerHalfWidth: 1.2,
  pedestrianDangerDepth: 4,
  blindLateralMin: 1.3,
  blindLateralMax: 4,
  blindRearExtension: 3,
  blindFrontZ: 0.5,
  parkingNoticeDistance: 3,
  parkingDangerDistance: 1,
  parkingStopDistance: 0.45,
} as const

const epsilon = 1e-8
const clampProgress = (progress: number) => Math.min(1, Math.max(0, progress))
const inRange = (value: number, min: number, max: number) => value >= min - epsilon && value <= max + epsilon

export function createScenarioState(): ScenarioState {
  return { id: 'pedestrian', progress: 0, playing: false, side: 'left' }
}

export function evaluateScenario(state: ScenarioState, signal: TurnSignal, vehicleLength: number): ScenarioFrame {
  const progress = clampProgress(state.progress)
  const halfLength = vehicleLength / 2

  if (state.id === 'pedestrian') {
    const actor = { x: -6 + progress * 12, z: halfLength + 3, kind: 'pedestrian' as const }
    const frontDistance = actor.z - halfLength
    const detected = inRange(Math.abs(actor.x), 0, scenarioZones.cameraHalfWidth)
      && inRange(frontDistance, 0, scenarioZones.cameraDepth)
    const danger = detected && inRange(Math.abs(actor.x), 0, scenarioZones.pedestrianDangerHalfWidth)
      && inRange(frontDistance, 0, scenarioZones.pedestrianDangerDepth)
    return {
      actor,
      level: danger ? 'danger' : detected ? 'notice' : 'safe',
      title: danger ? '行人進入車前區域' : detected ? '偵測到行人' : '前方區域正常',
      description: danger ? '行人位於車頭正前方，顯示危險警示。' : detected ? '行人進入攝影機示意範圍，請留意前方。' : '行人目前在攝影機示意範圍之外。',
      distance: Math.hypot(actor.x, frontDistance),
      activeSensor: 'camera',
    }
  }

  if (state.id === 'blindSpot') {
    const actor = {
      x: state.side === 'left' ? 2.5 : -2.5,
      z: -halfLength - 8 + progress * (vehicleLength + 16),
      kind: 'car' as const,
    }
    const detected = inRange(Math.abs(actor.x), scenarioZones.blindLateralMin, scenarioZones.blindLateralMax)
      && inRange(actor.z, -halfLength - scenarioZones.blindRearExtension, scenarioZones.blindFrontZ)
    const danger = detected && (signal === state.side || signal === 'hazard')
    const sideLabel = state.side === 'left' ? '左側' : '右側'
    const longitudinalGap = Math.max(0, Math.abs(actor.z) - halfLength)
    return {
      actor,
      level: danger ? 'danger' : detected ? 'notice' : 'safe',
      title: danger ? `${sideLabel}變換車道風險` : detected ? `${sideLabel}盲點有車` : `${sideLabel}盲點正常`,
      description: danger ? '盲點內有鄰車，且同側方向燈已開啟，加強警示。' : detected ? '鄰車進入後側盲點示意區域。' : '鄰車目前在盲點示意區域之外。',
      distance: Math.hypot(actor.x, longitudinalGap),
      activeSensor: 'radar',
    }
  }

  const distance = 6 - progress * (6 - scenarioZones.parkingStopDistance)
  const danger = distance <= scenarioZones.parkingDangerDistance + epsilon
  const detected = distance <= scenarioZones.parkingNoticeDistance + epsilon
  return {
    actor: { x: 0, z: -halfLength - distance, kind: 'obstacle' },
    level: danger ? 'danger' : detected ? 'notice' : 'safe',
    title: danger ? '停止：障礙物過近' : detected ? '注意後方障礙物' : '後方距離充足',
    description: danger ? '障礙物進入停止提示範圍；展示終點保留間距。' : detected ? '後方距離縮短，超音波示意區域顯示注意。' : '障礙物尚未進入超音波示意警示範圍。',
    distance,
    activeSensor: 'ultrasonic',
  }
}

export function advanceScenario(state: ScenarioState, delta: number): ScenarioState {
  if (!state.playing) return state
  const duration = scenarioDefinitions.find((definition) => definition.id === state.id)!.duration
  const progress = clampProgress(state.progress + Math.max(0, delta) / duration)
  return { ...state, progress, playing: progress < 1 }
}

export function resetScenario(state: ScenarioState): ScenarioState {
  return { ...state, progress: 0, playing: false }
}
