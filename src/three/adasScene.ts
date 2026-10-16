import * as THREE from 'three'
import type { VehicleDefinition } from '../types/vehicle'
import { scenarioZones, type ScenarioFrame, type ScenarioState } from '../adas/scenarios'

type SensorId = 'radar' | 'camera' | 'lidar' | 'ultrasonic'

export interface AdasScene {
  root: THREE.Group
  update(frame: ScenarioFrame, scenario: ScenarioState, sensors: Record<SensorId, boolean>, elapsed: number): void
  labels: { id: string; text: string; position: THREE.Vector3; color: string }[]
  dispose(): void
}

const palette: Record<SensorId, string> = {
  radar: '#78c6b0', camera: '#78aff0', lidar: '#b5a0e8', ultrasonic: '#eac078',
}
const warningColors = { safe: '#78c6b0', notice: '#eac078', danger: '#fa7775' }
const groundY = 0.035

function line(points: THREE.Vector3[], color: string, opacity = 0.65, dashed = false): THREE.Line {
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const options = { color, transparent: true, opacity, depthWrite: false }
  const material = dashed
    ? new THREE.LineDashedMaterial({ ...options, dashSize: 0.2, gapSize: 0.14 })
    : new THREE.LineBasicMaterial(options)
  const result = new THREE.Line(geometry, material)
  if (dashed) result.computeLineDistances()
  return result
}

function rectangle(xMin: number, xMax: number, zMin: number, zMax: number, color: string, fill = true): THREE.Group {
  const group = new THREE.Group()
  if (fill) {
    const face = new THREE.Mesh(
      new THREE.PlaneGeometry(xMax - xMin, zMax - zMin),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.075, side: THREE.DoubleSide, depthWrite: false }),
    )
    face.rotation.x = -Math.PI / 2
    face.position.set((xMin + xMax) / 2, groundY, (zMin + zMax) / 2)
    group.add(face)
  }
  const points = [[xMin, zMin], [xMax, zMin], [xMax, zMax], [xMin, zMax], [xMin, zMin]]
    .map(([x, z]) => new THREE.Vector3(x, groundY + 0.002, z))
  group.add(line(points, color, fill ? 0.45 : 0.65, !fill))
  return group
}

function ring(radius: number, color: string, opacity: number): THREE.Line {
  return line(Array.from({ length: 97 }, (_, i) => {
    const angle = i / 96 * Math.PI * 2
    return new THREE.Vector3(Math.cos(angle) * radius, groundY, Math.sin(angle) * radius)
  }), color, opacity)
}

function tint(group: THREE.Object3D, color: string): void {
  group.traverse((object) => {
    const material = (object as THREE.Mesh).material
    if (!material) return
    const materials = Array.isArray(material) ? material : [material]
    materials.forEach((entry) => {
      if ('color' in entry) (entry as THREE.MeshBasicMaterial).color.set(color)
    })
  })
}

function ghostMaterial(color: string, opacity = 0.22): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false })
}

function outlined(geometry: THREE.BufferGeometry, color: string, opacity = 0.18): THREE.Group {
  const group = new THREE.Group()
  group.add(new THREE.Mesh(geometry, ghostMaterial(color, opacity)))
  group.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 28), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.75, depthWrite: false })))
  return group
}

function carProfile(width: number): THREE.BufferGeometry {
  const profile = [
    [-2.05, 0.35], [2.05, 0.35], [2.05, 0.74], [1.35, 0.84],
    [0.65, 1.4], [-0.75, 1.4], [-1.22, 0.92], [-2.05, 0.79],
  ].map(([z, y]) => new THREE.Vector2(z, y))
  const positions: number[] = []
  for (const x of [-width / 2, width / 2]) profile.forEach((point) => positions.push(x, point.y, point.x))
  const faces: number[] = []
  const count = profile.length
  THREE.ShapeUtils.triangulateShape(profile, []).forEach(([a, b, c]) => {
    faces.push(a, b, c, c + count, b + count, a + count)
  })
  for (let i = 0; i < count; i++) {
    const next = (i + 1) % count
    faces.push(next + count, next, i, i + count, next + count, i)
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setIndex(faces)
  geometry.computeVertexNormals()
  return geometry
}

export function createAdasScene(vehicle: VehicleDefinition): AdasScene {
  const root = new THREE.Group()
  root.name = 'adas-illustration'
  const labels: AdasScene['labels'] = []
  const halfLength = vehicle.length / 2
  const sensorGroups: Record<SensorId, THREE.Group> = {
    camera: new THREE.Group(), radar: new THREE.Group(), lidar: new THREE.Group(), ultrasonic: new THREE.Group(),
  }
  for (const [id, group] of Object.entries(sensorGroups)) {
    group.name = `sensor-${id}`
    root.add(group)
  }

  sensorGroups.camera.add(rectangle(-scenarioZones.cameraHalfWidth, scenarioZones.cameraHalfWidth, halfLength, halfLength + scenarioZones.cameraDepth, palette.camera))
  sensorGroups.camera.add(rectangle(-scenarioZones.pedestrianDangerHalfWidth, scenarioZones.pedestrianDangerHalfWidth, halfLength, halfLength + scenarioZones.pedestrianDangerDepth, palette.camera, false))
  for (const x of [-scenarioZones.cameraHalfWidth, scenarioZones.cameraHalfWidth]) {
    sensorGroups.camera.add(line([new THREE.Vector3(0, 0.75, halfLength - 0.4), new THREE.Vector3(x, groundY, halfLength + scenarioZones.cameraDepth)], palette.camera, 0.2))
  }

  const rearBoundary = -halfLength - scenarioZones.blindRearExtension
  const radarLeft = rectangle(scenarioZones.blindLateralMin, scenarioZones.blindLateralMax, rearBoundary, scenarioZones.blindFrontZ, palette.radar)
  const radarRight = rectangle(-scenarioZones.blindLateralMax, -scenarioZones.blindLateralMin, rearBoundary, scenarioZones.blindFrontZ, palette.radar)
  sensorGroups.radar.add(radarLeft, radarRight)
  sensorGroups.ultrasonic.add(rectangle(-1.6, 1.6, -halfLength - scenarioZones.parkingNoticeDistance, -halfLength, palette.ultrasonic))
  sensorGroups.ultrasonic.add(rectangle(-1.6, 1.6, -halfLength - scenarioZones.parkingDangerDistance, -halfLength, palette.ultrasonic, false))
  sensorGroups.lidar.add(ring(5.7, palette.lidar, 0.3), ring(5.85, palette.lidar, 0.1))
  const lidarSweep = line([new THREE.Vector3(0, groundY, 0), new THREE.Vector3(5.7, groundY, 0)], palette.lidar, 0.25)
  sensorGroups.lidar.add(lidarSweep)

  const pedestrian = new THREE.Group()
  pedestrian.name = 'actor-pedestrian'
  const personMaterial = ghostMaterial(palette.camera, 0.7)
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.14, 12, 8), personMaterial)
  head.position.y = 1.65
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.18, 0.43, 3, 8), personMaterial)
  torso.position.y = 1.16
  pedestrian.add(head, torso)
  const legs: THREE.Group[] = []
  const arms: THREE.Group[] = []
  for (const sign of [-1, 1]) {
    const leg = new THREE.Group()
    leg.position.set(sign * 0.105, 0.92, 0)
    const limb = new THREE.Mesh(new THREE.CapsuleGeometry(0.065, 0.64, 3, 6), personMaterial)
    limb.position.y = -0.4
    leg.add(limb)
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.09, 0.25), personMaterial)
    shoe.position.set(0, -0.79, 0.04)
    leg.add(shoe)
    pedestrian.add(leg)
    legs.push(leg)
    const arm = new THREE.Group()
    arm.position.set(sign * 0.21, 1.4, 0)
    const armMesh = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.48, 3, 6), personMaterial)
    armMesh.position.y = -0.29
    arm.rotation.z = sign * 0.13
    arm.add(armMesh)
    pedestrian.add(arm)
    arms.push(arm)
  }
  pedestrian.rotation.y = Math.PI / 2

  const neighbor = new THREE.Group()
  neighbor.name = 'actor-car'
  const neighborBody = outlined(carProfile(1.65), palette.radar)
  neighborBody.name = 'neighbor-body'
  neighbor.add(neighborBody)
  for (const x of [-0.84, 0.84]) {
    for (const z of [-1.25, 1.3]) {
      const wheel = outlined(new THREE.CylinderGeometry(0.34, 0.34, 0.18, 12), palette.radar, 0.28)
      wheel.rotation.z = Math.PI / 2
      wheel.position.set(x, 0.34, z)
      neighbor.add(wheel)
    }
    const belt = line([new THREE.Vector3(x, 0.89, -1.15), new THREE.Vector3(x, 0.89, 1.3)], palette.radar, 0.6)
    const pillar = line([new THREE.Vector3(x, 0.89, -0.25), new THREE.Vector3(x, 1.39, -0.25)], palette.radar, 0.6)
    neighbor.add(belt, pillar)
  }

  const obstacle = new THREE.Group()
  obstacle.name = 'actor-obstacle'
  const barrier = outlined(new THREE.BoxGeometry(1.5, 0.65, 0.25), palette.ultrasonic, 0.3)
  barrier.position.set(0, 0.72, -0.125)
  obstacle.add(barrier)
  for (const x of [-0.57, 0.57]) {
    const post = outlined(new THREE.BoxGeometry(0.1, 0.72, 0.1), palette.ultrasonic, 0.4)
    post.position.set(x, 0.36, -0.125)
    obstacle.add(post)
  }
  for (let x = -0.58; x < 0.7; x += 0.35) {
    obstacle.add(line([new THREE.Vector3(x, 0.45, 0.005), new THREE.Vector3(x + 0.22, 0.96, 0.005)], palette.ultrasonic, 0.9))
  }
  root.add(pedestrian, neighbor, obstacle)

  const marker = ring(0.4, palette.camera, 0.85)
  root.add(marker)
  const pedestrianPath = line([new THREE.Vector3(-6, groundY, halfLength + 3), new THREE.Vector3(6, groundY, halfLength + 3)], palette.camera, 0.3, true)
  const neighborPath = line([new THREE.Vector3(0, groundY, -halfLength - 8), new THREE.Vector3(0, groundY, halfLength + 8)], palette.radar, 0.3, true)
  const parkingRuler = new THREE.Group()
  parkingRuler.add(line([new THREE.Vector3(1.95, groundY, -halfLength), new THREE.Vector3(1.95, groundY, -halfLength - 6)], palette.ultrasonic, 0.45))
  for (let distance = 0; distance <= 6; distance++) {
    parkingRuler.add(line([new THREE.Vector3(1.83, groundY, -halfLength - distance), new THREE.Vector3(2.07, groundY, -halfLength - distance)], palette.ultrasonic, 0.45))
  }
  root.add(pedestrianPath, neighborPath, parkingRuler)

  return {
    root,
    labels,
    update(frame, scenario, sensors, elapsed) {
      for (const id of Object.keys(sensorGroups) as SensorId[]) {
        sensorGroups[id].visible = sensors[id]
        tint(sensorGroups[id], palette[id])
      }
      const actorColor = frame.level === 'safe' ? palette[frame.activeSensor] : warningColors[frame.level]
      if (frame.level !== 'safe') {
        const activeGroup = scenario.id === 'blindSpot'
          ? scenario.side === 'left' ? radarLeft : radarRight
          : sensorGroups[frame.activeSensor]
        tint(activeGroup, actorColor)
      }
      pedestrian.visible = scenario.id === 'pedestrian'
      neighbor.visible = scenario.id === 'blindSpot'
      obstacle.visible = scenario.id === 'parking'
      pedestrianPath.visible = pedestrian.visible
      neighborPath.visible = neighbor.visible
      neighborPath.position.x = frame.actor.x
      parkingRuler.visible = obstacle.visible
      const actor = pedestrian.visible ? pedestrian : neighbor.visible ? neighbor : obstacle
      actor.position.set(frame.actor.x, 0, frame.actor.z)
      tint(actor, actorColor)
      marker.position.set(frame.actor.x, 0.007, frame.actor.z)
      tint(marker, actorColor)
      const gait = Math.sin(scenario.progress * Math.PI * 22) * 0.38
      legs.forEach((leg, index) => { leg.rotation.x = index === 0 ? gait : -gait })
      arms.forEach((arm, index) => { arm.rotation.x = index === 0 ? -gait : gait })
      lidarSweep.rotation.y = elapsed * 0.3

      labels.length = 0
      if (sensors.camera) labels.push({ id: 'camera', text: '攝影機', position: new THREE.Vector3(-2.6, 0.1, halfLength + 6.8), color: palette.camera })
      if (sensors.radar) labels.push({ id: 'radar', text: '後側雷達', position: new THREE.Vector3(3.7, 0.1, -halfLength - 1.8), color: palette.radar })
      if (sensors.lidar) labels.push({ id: 'lidar', text: 'LiDAR 環境掃描', position: new THREE.Vector3(-4.8, 0.1, -2.7), color: palette.lidar })
      if (sensors.ultrasonic) labels.push({ id: 'ultrasonic', text: '超音波', position: new THREE.Vector3(-1.35, 0.1, -halfLength - 2.55), color: palette.ultrasonic })
      labels.push({ id: 'actor', text: frame.actor.kind === 'pedestrian' ? '行人' : frame.actor.kind === 'car' ? '鄰車中心' : '障礙物', position: new THREE.Vector3(frame.actor.x, frame.actor.kind === 'pedestrian' ? 2.05 : 1.7, frame.actor.z), color: actorColor })
    },
    dispose() {
      const geometries = new Set<THREE.BufferGeometry>()
      const materials = new Set<THREE.Material>()
      root.traverse((object) => {
        const drawable = object as THREE.Mesh
        if (drawable.geometry) geometries.add(drawable.geometry)
        if (drawable.material) {
          const entries = Array.isArray(drawable.material) ? drawable.material : [drawable.material]
          entries.forEach((material) => materials.add(material))
        }
      })
      geometries.forEach((geometry) => geometry.dispose())
      materials.forEach((material) => material.dispose())
      root.clear()
      labels.length = 0
    },
  }
}
