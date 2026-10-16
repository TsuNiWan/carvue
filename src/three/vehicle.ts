import {
  BoxGeometry, BufferGeometry, Color, CylinderGeometry, DoubleSide,
  ExtrudeGeometry, Float32BufferAttribute, Group, Line, LineBasicMaterial,
  Mesh, MeshPhysicalMaterial, MeshStandardMaterial, Shape,
  SpotLight, TorusGeometry, Vector3,
} from 'three'
import type { Material } from 'three'
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js'
import type { DoorId, VehicleDefinition, VehicleRig, VehicleState } from '../types/vehicle'

type Point = [number, number, number]
type ProfilePoint = [number, number]

/** All body panels use world coordinates before they are attached to a hinge. */
export function createVehicle(def: VehicleDefinition): VehicleRig {
  const root = new Group()
  root.name = `vehicle-${def.id}`
  const suv = def.bodyStyle === 'suv'
  const sport = def.id === 'sedan-02'
  const luxury = def.id === 'sedan-03'
  const halfWidth = def.width / 2
  const halfLength = def.length / 2
  const belt = suv ? 1.10 : 0.99
  const roofHeight = def.height
  const roofWidth = halfWidth * (suv ? 0.78 : 0.75)
  const roofFront = sport ? 0.17 : suv ? 0.48 : 0.36
  const roofRear = suv ? -1.23 : sport ? -0.67 : -0.65
  const glassFront = 0.99
  const glassRear = suv ? -1.70 : -1.23
  const wheelRadius = suv ? 0.375 : 0.345
  const wheelY = wheelRadius
  const frontAxle = halfLength * 0.61
  const rearAxle = -halfLength * 0.61
  const sillY = suv ? 0.43 : 0.36
  const doorBottom = sillY + 0.1
  const frontHingeZ = 0.99
  const rearHingeZ = -0.08

  const paint = new MeshPhysicalMaterial({ color: def.color, metalness: 0.66, roughness: 0.23, clearcoat: 1, clearcoatRoughness: 0.16, side: DoubleSide })
  const paintInner = new MeshStandardMaterial({ color: new Color(def.color).multiplyScalar(0.58), metalness: 0.45, roughness: 0.4, side: DoubleSide })
  const glass = new MeshPhysicalMaterial({ color: '#142630', metalness: 0.12, roughness: 0.12, transparent: true, opacity: 0.68, side: DoubleSide, depthWrite: false, clearcoat: 1 })
  const rubber = new MeshStandardMaterial({ color: '#11151b', roughness: 0.88 })
  const black = new MeshStandardMaterial({ color: '#10151d', metalness: 0.3, roughness: 0.48, side: DoubleSide })
  const chrome = new MeshStandardMaterial({ color: '#9ba9b6', metalness: 0.92, roughness: 0.22, side: DoubleSide })
  const rimDark = new MeshStandardMaterial({ color: '#28313c', metalness: 0.78, roughness: 0.29 })
  const cabin = new MeshStandardMaterial({ color: '#222a32', roughness: 0.92, side: DoubleSide })
  const seatMaterial = new MeshStandardMaterial({ color: luxury ? '#796e60' : '#333c43', roughness: 0.87 })
  const redLens = new MeshPhysicalMaterial({ color: '#9d1423', emissive: '#ff263b', emissiveIntensity: 0.08, roughness: 0.22, metalness: 0.12, clearcoat: 1 })
  const headLens = new MeshPhysicalMaterial({ color: '#bcd9e5', emissive: '#d1f4ff', emissiveIntensity: 0.08, roughness: 0.18, metalness: 0.4, clearcoat: 1, side: DoubleSide })
  const signals = {
    left: new MeshStandardMaterial({ color: '#5f4221', emissive: '#ff9900', emissiveIntensity: 0, roughness: 0.2 }),
    right: new MeshStandardMaterial({ color: '#5f4221', emissive: '#ff9900', emissiveIntensity: 0, roughness: 0.2 }),
  }
  signals.left.name = 'left-signal'
  signals.right.name = 'right-signal'
  headLens.name = 'headlamp'
  redLens.name = 'tail-lamp'
  const joints = {} as Record<DoorId | 'trunk', Group>
  const frontWheels: Group[] = []
  const beams: SpotLight[] = []

  function mesh(geometry: BufferGeometry, material: Material, parent = root, name = '') {
    const result = new Mesh(geometry, material)
    result.name = name
    result.castShadow = true
    result.receiveShadow = true
    parent.add(result)
    return result
  }

  function box(size: Point, position: Point, material: Material, parent = root, radius = 0.025) {
    const result = mesh(radius > 0 ? new RoundedBoxGeometry(...size, 2, radius) : new BoxGeometry(...size), material, parent)
    result.position.set(...position)
    return result
  }

  function surface(points: Point[], indices: number[], material: Material, parent = root, name = '') {
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new Float32BufferAttribute(points.flat(), 3))
    geometry.setIndex(indices)
    geometry.computeVertexNormals()
    return mesh(geometry, material, parent, name)
  }

  function polygon(points: Point[], material: Material, parent = root, name = '') {
    const indices: number[] = []
    for (let i = 1; i < points.length - 1; i++) indices.push(0, i, i + 1)
    return surface(points, indices, material, parent, name)
  }

  function rod(a: Point, b: Point, radius: number, material: Material, parent = root) {
    const start = new Vector3(...a)
    const end = new Vector3(...b)
    const result = mesh(new CylinderGeometry(radius, radius, start.distanceTo(end), 8), material, parent)
    result.position.copy(start).add(end).multiplyScalar(0.5)
    result.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), end.sub(start).normalize())
    if (radius < 0.02) result.castShadow = false
    return result
  }

  function seam(points: Point[], parent = root, color = '#28343e') {
    const geometry = new BufferGeometry().setFromPoints(points.map(p => new Vector3(...p)))
    const line = new Line(geometry, new LineBasicMaterial({ color, transparent: true, opacity: 0.6 }))
    parent.add(line)
  }

  function sideX(y: number, side: number) {
    const taper = Math.max(0, y - belt) / (roofHeight - belt)
    return side * (halfWidth * 0.97 * (1 - taper) + roofWidth * taper)
  }

  function sidePanel(profile: ProfilePoint[], side: number, material: Material, parent = root, offset = 0) {
    return polygon(profile.map(([z, y]) => [sideX(y, side) + side * offset, y, z]), material, parent)
  }

  function curvedDeck(zStart: number, zEnd: number, yStart: number, yEnd: number, parent = root) {
    const points: Point[] = []
    const indices: number[] = []
    const rows = 8
    const cols = 16
    for (let j = 0; j <= rows; j++) {
      const t = j / rows
      for (let i = 0; i <= cols; i++) {
        const u = i / cols * 2 - 1
        const width = halfWidth * (0.9 + 0.075 * Math.sin(t * Math.PI))
        const crown = 0.055 * (1 - u * u)
        const noseCurve = zStart > 0 ? 0.12 * Math.pow(Math.abs(u), 4) * (1 - t) : 0
        points.push([width * u, yStart + (yEnd - yStart) * t + crown, zStart + (zEnd - zStart) * t - noseCurve])
        if (i < cols && j < rows) {
          const a = j * (cols + 1) + i
          indices.push(a, a + cols + 1, a + 1, a + 1, a + cols + 1, a + cols + 2)
        }
      }
    }
    surface(points, indices, paint, parent, 'sculpted-body-panel')
  }

  // The floor and sill stop below the doors, leaving real openings into the cabin.
  box([def.width * 0.8, 0.12, 2.75], [0, sillY, -0.02], cabin)
  box([0.22, 0.18, 1.85], [0, sillY + 0.17, -0.05], black)
  for (const side of [-1, 1]) {
    box([0.14, 0.11, 2.06], [side * (halfWidth - 0.075), sillY, -0.03], paint)
    box([0.055, 0.035, 1.91], [side * halfWidth * 0.99, sillY + 0.028, -0.025], suv ? black : chrome, root, 0.01)
  }

  // Fenders are cut around the wheel openings instead of hiding tires in a box.
  function fender(side: number, front: boolean) {
    const axle = front ? frontAxle : rearAxle
    const arch = wheelRadius + 0.053
    const outerStart = front ? 0.955 : -halfLength + 0.10
    const outerEnd = front ? halfLength - 0.10 : -1.025
    const shape = new Shape()
    shape.moveTo(outerStart, doorBottom)
    shape.lineTo(outerStart, belt - (front ? 0 : 0.07))
    shape.quadraticCurveTo((outerStart + outerEnd) / 2, belt + 0.005, outerEnd, belt - (front ? 0.12 : 0))
    shape.lineTo(outerEnd, doorBottom)
    shape.lineTo(axle + arch, doorBottom)
    shape.lineTo(axle + arch, wheelY)
    shape.absarc(axle, wheelY, arch, 0, Math.PI, false)
    shape.lineTo(axle - arch, doorBottom)
    shape.closePath()
    const geometry = new ExtrudeGeometry(shape, { depth: 0.11, bevelEnabled: true, bevelThickness: 0.013, bevelSize: 0.010, bevelSegments: 3, steps: 1, curveSegments: 18 })
    geometry.rotateY(-Math.PI / 2)
    const panel = mesh(geometry, paint, root, front ? 'front-fender' : 'rear-quarter')
    panel.position.x = side > 0 ? halfWidth * 0.955 : -halfWidth * 0.955 + 0.11
    if (front) {
      const position = geometry.getAttribute('position')
      for (let i = 0; i < position.count; i++) {
        const z = position.getZ(i)
        const t = Math.max(0, (z - frontAxle - 0.18) / (halfLength - 0.10 - frontAxle - 0.18))
        position.setX(i, (position.getX(i) + panel.position.x) * (1 - 0.10 * t * t) - panel.position.x)
        position.setZ(i, z - 0.13 * t * t)
      }
      geometry.computeVertexNormals()
    }
    const trimPoints: Point[] = []
    for (let i = 0; i <= 32; i++) {
      const angle = Math.PI * i / 32
      trimPoints.push([side * (halfWidth * 0.965 + 0.016), wheelY + Math.sin(angle) * (arch + 0.013), axle + Math.cos(angle) * (arch + 0.013)])
    }
    if (suv) {
      for (let i = 0; i < trimPoints.length - 1; i++) rod(trimPoints[i]!, trimPoints[i + 1]!, 0.025, black)
    } else seam(trimPoints)
  }
  for (const side of [-1, 1]) {
    fender(side, true)
    fender(side, false)
  }

  const noseZ = halfLength - 0.12
  curvedDeck(noseZ, glassFront, belt - 0.14, belt + 0.015)
  for (const side of [-1, 1]) {
    seam([[side * halfWidth * 0.72, belt - 0.075, noseZ - 0.04], [side * halfWidth * 0.60, belt + 0.025, 1.4], [side * halfWidth * 0.73, belt + 0.042, glassFront]])
  }
  const fasciaRows = [
    [sillY + 0.015, 0.86, halfLength - 0.105],
    [sillY + 0.075, 0.93, halfLength - 0.035],
    [belt - 0.30, 0.976, halfLength - 0.022],
    [belt - 0.16, 0.965, halfLength - 0.037],
    [belt - 0.085, 0.90, noseZ],
  ]
  const fasciaPoints: Point[] = []
  const fasciaIndices: number[] = []
  for (let row = 0; row < fasciaRows.length; row++) {
    const [y, width, z] = fasciaRows[row]!
    for (let column = 0; column <= 24; column++) {
      const u = column / 12 - 1
      fasciaPoints.push([u * halfWidth * width!, y! - (row === fasciaRows.length - 1 ? 0.055 : 0.021) * u * u, z! - 0.12 * Math.pow(Math.abs(u), 4)])
      if (row < fasciaRows.length - 1 && column < 24) {
        const a = row * 25 + column
        fasciaIndices.push(a, a + 1, a + 25, a + 1, a + 26, a + 25)
      }
    }
  }
  surface(fasciaPoints, fasciaIndices, paint, root, 'sculpted-front-fascia')
  box([def.width * 0.79, 0.035, 0.17], [0, sillY + 0.02, halfLength - 0.19], black, root, 0.018)
  box([def.width * 0.93, 0.3, 0.26], [0, belt - 0.39, -halfLength + 0.15], paint, root, 0.065)
  box([def.width * 0.85, 0.09, 0.25], [0, sillY + 0.025, -halfLength + 0.17], black)

  // Front identities use independent grilles, lamp signatures and bumper details.
  function grille(points: Array<[number, number]>, z: number, material: Material) {
    return polygon(points.map(([x, y]) => [x, y, z]), material)
  }
  const grilleZ = halfLength + 0.005
  const grilleY = belt - 0.29
  if (def.id === 'suv-02') {
    for (const side of [-1, 1]) {
      box([0.40, 0.32, 0.055], [side * 0.228, grilleY + 0.07, grilleZ], chrome, root, 0.08)
      box([0.345, 0.27, 0.058], [side * 0.228, grilleY + 0.07, grilleZ + 0.018], black, root, 0.07)
      for (let i = -2; i <= 2; i++) box([0.014, 0.23, 0.017], [side * 0.228 + i * 0.051, grilleY + 0.07, grilleZ + 0.054], chrome, root, 0.005)
    }
  } else if (sport) {
    const outline: Array<[number, number]> = [[-0.52, grilleY + 0.19], [0.52, grilleY + 0.19], [0.46, grilleY - 0.11], [0, grilleY - 0.24], [-0.46, grilleY - 0.11]]
    grille(outline, grilleZ, chrome)
    grille(outline.map(([x, y]) => [x * 0.93, grilleY + (y - grilleY) * 0.89]), grilleZ + 0.007, black)
  } else if (luxury) {
    box([1.04, 0.34, 0.05], [0, grilleY + 0.025, grilleZ], chrome, root, 0.09)
    box([0.98, 0.285, 0.055], [0, grilleY + 0.025, grilleZ + 0.011], black, root, 0.08)
    box([0.98, 0.022, 0.025], [0, grilleY + 0.028, grilleZ + 0.046], chrome)
    const badge = mesh(new TorusGeometry(0.073, 0.009, 6, 24), chrome)
    badge.position.set(0, grilleY + 0.033, grilleZ + 0.069)
    for (let i = 0; i < 3; i++) {
      const angle = i * Math.PI * 2 / 3
      rod([0, grilleY + 0.033, grilleZ + 0.073], [Math.sin(angle) * 0.068, grilleY + 0.033 + Math.cos(angle) * 0.068, grilleZ + 0.073], 0.007, chrome)
    }
  } else if (def.id === 'suv-01') {
    grille([[-0.64, grilleY + 0.17], [0.64, grilleY + 0.17], [0.5, grilleY - 0.13], [-0.5, grilleY - 0.13]], grilleZ, black)
    box([1.33, 0.045, 0.035], [0, grilleY + 0.155, grilleZ + 0.032], chrome)
    for (let i = -4; i <= 4; i++) box([0.068, 0.2, 0.024], [i * 0.11, grilleY + 0.005, grilleZ + 0.012], rimDark, root, 0.006)
  } else {
    grille([[-0.43, grilleY + 0.075], [0.43, grilleY + 0.075], [0.60, grilleY - 0.18], [0.54, grilleY - 0.23], [-0.54, grilleY - 0.23], [-0.60, grilleY - 0.18]], grilleZ, black)
    for (let i = -5; i <= 5; i++) {
      const x = i * 0.087
      rod([x - 0.028, grilleY - 0.185, grilleZ + 0.004], [x + 0.04, grilleY + 0.027, grilleZ + 0.004], 0.004, rimDark)
    }
    grille([[-0.51, grilleY + 0.185], [-0.19, grilleY + 0.152], [0, grilleY + 0.135], [0.19, grilleY + 0.152], [0.51, grilleY + 0.185], [0.26, grilleY + 0.10], [-0.26, grilleY + 0.10]], grilleZ - 0.005, black)
  }
  if (!luxury) {
    const badge = mesh(new CylinderGeometry(0.035, 0.035, 0.012, 20), chrome)
    badge.rotation.x = Math.PI / 2
    badge.position.set(0, belt - 0.12, grilleZ + 0.034)
  }
  for (const side of [-1, 1]) {
    const intakePoints: Point[] = []
    const intakeIndices: number[] = []
    for (let row = 0; row <= 6; row++) {
      for (let column = 0; column <= 6; column++) {
        const x = side * halfWidth * (0.68 + column / 6 * 0.15)
        const y = belt - 0.48 + row / 6 * 0.145
        let z = halfLength - 0.04
        for (let fasciaRow = 0; fasciaRow < fasciaRows.length - 1; fasciaRow++) {
          const lower = fasciaRows[fasciaRow]!
          const upper = fasciaRows[fasciaRow + 1]!
          const lowerU = x / (halfWidth * lower[1]!)
          const upperU = x / (halfWidth * upper[1]!)
          const lowerY = lower[0]! - 0.021 * lowerU * lowerU
          const upperY = upper[0]! - (fasciaRow + 1 === fasciaRows.length - 1 ? 0.055 : 0.021) * upperU * upperU
          if (y >= lowerY && y <= upperY) {
            const t = (y - lowerY) / (upperY - lowerY)
            const lowerZ = lower[2]! - 0.12 * Math.pow(Math.abs(lowerU), 4)
            const upperZ = upper[2]! - 0.12 * Math.pow(Math.abs(upperU), 4)
            z = lowerZ + (upperZ - lowerZ) * t
            break
          }
        }
        intakePoints.push([x, y, z + 0.006])
        if (column < 6 && row < 6) {
          const a = row * 7 + column
          intakeIndices.push(a, a + 1, a + 7, a + 1, a + 8, a + 7)
        }
      }
    }
    surface(intakePoints, intakeIndices, black, root, 'flush-front-intake')
  }
  box([0.38, 0.105, 0.025], [0, belt - 0.34, grilleZ + 0.026], rimDark, root, 0.01)
  box([0.26, 0.014, 0.003], [0, belt - 0.34, grilleZ + 0.04], chrome, root, 0)

  // Seat cushions, split backrests, dashboard and steering wheel remain visible through open doors.
  for (const row of [0.42, -0.66]) {
    for (const side of [-1, 1]) {
      box([0.52, 0.13, 0.49], [side * 0.43, sillY + 0.25, row], seatMaterial, root, 0.075)
      const back = box([0.51, suv ? 0.56 : 0.48, 0.13], [side * 0.43, sillY + (suv ? 0.56 : 0.50), row - 0.23], seatMaterial, root, 0.06)
      back.rotation.x = -0.1
      box([0.29, 0.17, 0.12], [side * 0.43, sillY + (suv ? 0.90 : 0.79), row - 0.27], seatMaterial, root, 0.05)
    }
  }
  box([def.width * 0.84, 0.17, 0.34], [0, belt - 0.095, 0.86], cabin, root, 0.06)
  box([0.26, 0.11, 0.34], [0, sillY + 0.33, 0.13], cabin)
  box([0.22, 0.15, 0.024], [0, belt + 0.014, 0.75], black, root, 0.016)
  const steeringWheel = mesh(new TorusGeometry(0.14, 0.015, 8, 28), black)
  steeringWheel.position.set(0.42, belt - 0.085, 0.6)
  steeringWheel.rotation.x = -0.32
  rod([0.42, belt - 0.085, 0.6], [0.42, belt - 0.09, 0.86], 0.028, black)
  rod([0.30, belt - 0.085, 0.6], [0.54, belt - 0.085, 0.6], 0.015, chrome)

  // The glazed cabin consists of separate glass, roof and narrow structural pillars.
  const windshieldPoints: Point[] = [
    [-halfWidth * 0.90, belt + 0.027, glassFront], [halfWidth * 0.90, belt + 0.027, glassFront],
    [roofWidth, roofHeight - 0.024, roofFront], [-roofWidth, roofHeight - 0.024, roofFront],
  ]
  polygon(windshieldPoints, glass, root, 'windshield')
  for (const side of [-1, 1]) {
    rod([side * halfWidth * 0.91, belt + 0.015, glassFront], [side * roofWidth, roofHeight - 0.040, roofFront], 0.023, paint)
    rod([side * roofWidth, roofHeight - 0.030, roofFront], [side * roofWidth, roofHeight - 0.030, roofRear], 0.014, paint)
    rod([side * halfWidth * 0.966, belt, rearHingeZ], [side * roofWidth, roofHeight - 0.015, rearHingeZ], 0.038, black)
    rod([side * halfWidth * 0.951, doorBottom, rearHingeZ], [side * halfWidth * 0.957, belt, rearHingeZ], 0.038, paintInner)
  }
  const roofPoints: Point[] = []
  const roofIndices: number[] = []
  for (let j = 0; j <= 6; j++) {
    for (let i = 0; i <= 12; i++) {
      const u = i / 12 * 2 - 1
      const t = j / 6
      roofPoints.push([u * roofWidth, roofHeight + 0.04 * (1 - u * u) - 0.025 * Math.abs(t - 0.5), roofFront + (roofRear - roofFront) * t])
      if (i < 12 && j < 6) {
        const a = j * 13 + i
        roofIndices.push(a, a + 1, a + 13, a + 1, a + 14, a + 13)
      }
    }
  }
  surface(roofPoints, roofIndices, paint, root, 'curved-roof')
  if (suv) {
    for (const side of [-1, 1]) rod([side * roofWidth * 0.91, roofHeight + 0.07, roofFront - 0.1], [side * roofWidth * 0.91, roofHeight + 0.07, roofRear + 0.1], 0.022, chrome)
  }
  for (const x of [-0.34, 0.34]) rod([x - 0.22, belt + 0.049, glassFront + 0.004], [x + 0.15, belt + 0.08, glassFront - 0.046], 0.009, black)

  function createDoor(id: DoorId, side: number, front: boolean) {
    const hingeZ = front ? frontHingeZ : rearHingeZ
    const joint = new Group()
    joint.name = id
    joint.position.set(side * halfWidth * 0.97, 0, hingeZ)
    root.add(joint)
    joints[id] = joint
    const content = new Group()
    content.position.set(-joint.position.x, 0, -hingeZ)
    joint.add(content)
    const zFront = front ? frontHingeZ - 0.018 : rearHingeZ - 0.021
    const zRear = front ? rearHingeZ + 0.021 : -1.22
    const profile: ProfilePoint[] = [
      [zFront, belt - 0.008], [zRear, belt - 0.008],
      [front ? zRear : -1.025, doorBottom + 0.02], [zFront - (front ? 0.07 : 0), doorBottom + 0.02],
    ]
    const lowerPoints: Point[] = []
    const lowerIndices: number[] = []
    for (let j = 0; j <= 6; j++) {
      const t = j / 6
      const y = doorBottom + 0.02 + (belt - doorBottom - 0.028) * t
      const startZ = profile[3]![0] + (zFront - profile[3]![0]) * t
      const endZ = profile[2]![0] + (zRear - profile[2]![0]) * t
      for (let i = 0; i <= 8; i++) {
        const u = i / 8
        const bulge = Math.sin(t * Math.PI) * 0.023 - 0.016 * (1 - t)
        lowerPoints.push([side * (halfWidth * 0.97 + bulge), y, startZ + (endZ - startZ) * u])
        if (i < 8 && j < 6) {
          const a = j * 9 + i
          lowerIndices.push(a, a + 1, a + 9, a + 1, a + 10, a + 9)
        }
      }
    }
    surface(lowerPoints, lowerIndices, paint, content, `${id}-outer-panel`)
    sidePanel(profile, side, cabin, content, -0.038)
    for (let i = 0; i < profile.length; i++) {
      const a = profile[i]!
      const b = profile[(i + 1) % profile.length]!
      polygon([[sideX(a[1], side), a[1], a[0]], [sideX(b[1], side), b[1], b[0]], [sideX(b[1], side) - side * 0.038, b[1], b[0]], [sideX(a[1], side) - side * 0.038, a[1], a[0]]], paintInner, content)
    }
    const upper: ProfilePoint[] = front
      ? [[zFront - 0.04, belt + 0.033], [roofFront - 0.018, roofHeight - 0.045], [zRear + 0.015, roofHeight - 0.045], [zRear + 0.015, belt + 0.033]]
      : [[zFront - 0.023, belt + 0.033], [zFront - 0.023, roofHeight - 0.045], [suv ? -0.92 : roofRear + 0.035, roofHeight - 0.045], [zRear + 0.052, belt + 0.033]]
    sidePanel(upper, side, glass, content)
    for (let i = 0; i < upper.length; i++) {
      const a = upper[i]!
      const b = upper[(i + 1) % upper.length]!
      rod([sideX(a[1], side), a[1], a[0]], [sideX(b[1], side), b[1], b[0]], 0.017, black, content)
    }
    rod([sideX(belt, side) + side * 0.007, belt + 0.009, zFront - 0.018], [sideX(belt, side) + side * 0.007, belt + 0.009, zRear + 0.018], 0.012, luxury || suv ? chrome : black, content)
    box([0.035, 0.025, 0.15], [side * (halfWidth * 0.99 + 0.017), belt - 0.12, zRear + 0.16], luxury ? chrome : paint, content, 0.012)
    box([0.049, 0.047, 0.32], [side * (halfWidth * 0.97 - 0.062), belt - 0.2, (zFront + zRear) / 2], cabin, content, 0.02)
    seam(profile.map<Point>(([z, y]) => [sideX(y, side) + side * 0.003, y, z]).concat([[sideX(profile[0]![1], side) + side * 0.003, profile[0]![1], profile[0]![0]]]), content)
    if (front) {
      rod([side * halfWidth * 0.945, belt + 0.075, 0.76], [side * (halfWidth + 0.14), belt + 0.06, 0.7], 0.026, black, content)
      const mirror = box([0.23, 0.11, 0.21], [side * (halfWidth + 0.13), belt + 0.095, 0.69], paint, content, 0.047)
      mirror.rotation.y = -side * 0.15
      box([0.165, 0.075, 0.018], [side * (halfWidth + 0.13), belt + 0.093, 0.58], chrome, content, 0.024)
      box([0.18, 0.013, 0.02], [side * (halfWidth + 0.13), belt + 0.082, 0.799], side > 0 ? signals.left : signals.right, content, 0.005)
    }
  }
  createDoor('frontLeft', 1, true)
  createDoor('frontRight', -1, true)
  createDoor('rearLeft', 1, false)
  createDoor('rearRight', -1, false)

  // The rear compartment is open above its floor; only the hinged lid closes it.
  const trunk = new Group()
  trunk.name = 'trunk'
  trunk.position.set(0, suv ? roofHeight - 0.035 : belt + 0.018, suv ? roofRear : glassRear)
  root.add(trunk)
  joints.trunk = trunk
  const trunkContent = new Group()
  trunkContent.position.copy(trunk.position).negate()
  trunk.add(trunkContent)
  box([def.width * 0.78, 0.045, suv ? 1.13 : 0.77], [0, sillY + 0.05, suv ? -1.55 : -1.74], cabin)
  box([def.width * 0.76, belt - sillY - 0.04, 0.065], [0, (belt + sillY) / 2, suv ? -1.01 : -1.3], cabin)
  for (const side of [-1, 1]) box([0.07, 0.33, 0.72], [side * halfWidth * 0.80, sillY + 0.22, -1.72], cabin)
  if (suv) {
    for (const side of [-1, 1]) {
      const quarter: ProfilePoint[] = [[-1.25, belt + 0.02], [-0.96, roofHeight - 0.055], [roofRear - 0.035, roofHeight - 0.055], [glassRear + 0.055, belt + 0.11]]
      sidePanel(quarter, side, glass)
      rod([side * roofWidth, roofHeight - 0.02, roofRear], [side * halfWidth * 0.9, belt + 0.045, glassRear], 0.061, paint)
      sidePanel([[-1.23, belt], [glassRear - 0.12, belt - 0.08], [glassRear, belt + 0.12], [roofRear - 0.02, roofHeight - 0.06], [-1.02, roofHeight - 0.06]], side, paint)
    }
    polygon([[-roofWidth + 0.065, roofHeight - 0.08, roofRear - 0.035], [roofWidth - 0.065, roofHeight - 0.08, roofRear - 0.035], [halfWidth * 0.83, belt + 0.03, -halfLength + 0.15], [-halfWidth * 0.83, belt + 0.03, -halfLength + 0.15]], glass, trunkContent, 'tailgate-glass')
    polygon([[-halfWidth * 0.85, belt + 0.042, -halfLength + 0.14], [halfWidth * 0.85, belt + 0.042, -halfLength + 0.14], [halfWidth * 0.84, sillY + 0.26, -halfLength + 0.07], [-halfWidth * 0.84, sillY + 0.26, -halfLength + 0.07]], paint, trunkContent, 'tailgate-panel')
    polygon([[-halfWidth * 0.83, belt + 0.036, -halfLength + 0.19], [halfWidth * 0.83, belt + 0.036, -halfLength + 0.19], [halfWidth * 0.81, sillY + 0.27, -halfLength + 0.12], [-halfWidth * 0.81, sillY + 0.27, -halfLength + 0.12]], cabin, trunkContent)
    box([def.width * 0.8, 0.057, 0.18], [0, roofHeight - 0.025, roofRear - 0.056], paint, trunkContent)
    box([0.31, 0.018, 0.03], [0, roofHeight - 0.038, roofRear - 0.15], redLens, trunkContent, 0.004)
  } else {
    polygon([[-roofWidth, roofHeight - 0.015, roofRear], [roofWidth, roofHeight - 0.015, roofRear], [halfWidth * 0.88, belt + 0.03, glassRear], [-halfWidth * 0.88, belt + 0.03, glassRear]], glass, root, 'rear-windshield')
    for (const side of [-1, 1]) {
      sidePanel([[roofRear + 0.05, roofHeight - 0.02], [glassRear, belt], [-1.40, belt - 0.04], [roofRear - 0.11, roofHeight - 0.04]], side, paint)
      rod([side * roofWidth, roofHeight - 0.03, roofRear], [side * halfWidth * 0.90, belt + 0.025, glassRear], 0.025, paint)
    }
    curvedDeck(-halfLength + 0.10, glassRear, belt - 0.055, belt + 0.018, trunkContent)
    box([def.width * 0.77, 0.027, 0.69], [0, belt - 0.005, -1.75], paintInner, trunkContent)
    box([def.width * 0.86, 0.13, 0.055], [0, belt - 0.1, -halfLength + 0.088], paint, trunkContent, 0.018)
  }
  box([0.15, 0.02, 0.025], [0, belt - 0.14, -halfLength + 0.03], chrome, trunkContent, 0.007)
  box([0.41, 0.1, 0.028], [0, belt - 0.31, -halfLength + 0.006], rimDark, suv ? trunkContent : root, 0.01)
  for (const side of [-1, 1]) {
    const exhaust = mesh(new CylinderGeometry(0.049, 0.045, 0.13, 16), chrome)
    exhaust.rotation.x = Math.PI / 2
    exhaust.position.set(side * halfWidth * 0.69, sillY - 0.005, -halfLength + 0.045)
    const opening = mesh(new CylinderGeometry(0.038, 0.038, 0.008, 16), black)
    opening.rotation.x = Math.PI / 2
    opening.position.set(side * halfWidth * 0.69, sillY - 0.005, -halfLength - 0.024)
  }

  // Light materials are shared only within this vehicle, so disposal never affects another car.
  for (const side of [-1, 1]) {
    const lampX = side * halfWidth * 0.70
    const signalMaterial = side > 0 ? signals.left : signals.right
    const lampProfile: Point[] = [
      [side * (sport ? 0.47 : 0.39), belt - 0.116, halfLength - 0.015],
      [side * halfWidth * 0.905, belt - 0.14, halfLength - 0.158],
      [side * halfWidth * 0.916, belt - (sport ? 0.181 : 0.20), halfLength - 0.161],
      [side * (sport ? 0.49 : 0.46), belt - (sport ? 0.152 : 0.184), halfLength - 0.005],
    ]
    polygon(lampProfile, black, root, 'swept-headlight-housing')
    const ledStart: Point = [lampProfile[0]![0] + side * 0.02, lampProfile[0]![1] - 0.012, lampProfile[0]![2] + 0.006]
    const ledEnd: Point = [lampProfile[1]![0] - side * 0.024, lampProfile[1]![1] - 0.013, lampProfile[1]![2] + 0.006]
    rod(ledStart, ledEnd, 0.010, headLens)
    if (def.id !== 'suv-02') {
      rod([lampX - side * 0.04, belt - 0.16, halfLength - 0.083], [lampX + side * 0.063, belt - 0.17, halfLength - 0.114], 0.014, headLens)
    }
    if (def.id === 'suv-02') {
      for (const offset of [-0.093, 0.093]) {
        rod([lampX + offset - 0.034, belt - 0.15, halfLength - 0.075], [lampX + offset - 0.034, belt - 0.19, halfLength - 0.075], 0.009, headLens)
        rod([lampX + offset - 0.034, belt - 0.19, halfLength - 0.075], [lampX + offset + 0.035, belt - 0.19, halfLength - 0.075], 0.009, headLens)
      }
    }
    rod([lampX + side * 0.02, belt - 0.183, halfLength - 0.079], [lampX + side * 0.13, belt - 0.19, halfLength - 0.124], 0.009, signalMaterial)
    const rearLampY = belt - 0.13
    box([0.39, 0.086, 0.039], [side * halfWidth * 0.70, rearLampY, -halfLength + 0.027], redLens, root, 0.022)
    box([0.19, 0.018, 0.048], [side * halfWidth * 0.79, rearLampY - 0.059, -halfLength + 0.025], signalMaterial, root, 0.006)
    box([0.058, 0.067, 0.25], [side * halfWidth * 0.947, rearLampY + 0.005, -halfLength + 0.20], redLens, root, 0.022)
    if (def.id === 'suv-01') {
      const pillarStart = new Vector3(side * roofWidth, roofHeight - 0.02, roofRear)
      const pillarEnd = new Vector3(side * halfWidth * 0.9, belt + 0.045, glassRear)
      const lampStart = pillarStart.clone().lerp(pillarEnd, 0.40)
      const lampEnd = pillarStart.clone().lerp(pillarEnd, 0.91)
      lampStart.x += side * 0.058
      lampEnd.x += side * 0.058
      rod(lampStart.toArray() as Point, lampEnd.toArray() as Point, 0.018, redLens)
    }
    const beam = new SpotLight('#d7f0ff', 0, 11, Math.PI / 6, 0.6, 1.4)
    beam.position.set(lampX, belt - 0.13, halfLength + 0.065)
    beam.target.position.set(lampX * 1.45, 0.02, halfLength + 6)
    beam.castShadow = false
    root.add(beam, beam.target)
    beams.push(beam)
  }

  function wheel(side: number, z: number, front: boolean) {
    const group = new Group()
    group.name = `${front ? 'front' : 'rear'}-${side > 0 ? 'left' : 'right'}-wheel`
    group.position.set(side * halfWidth * 0.951, wheelY, z)
    root.add(group)
    if (front) frontWheels.push(group)
    const tire = mesh(new TorusGeometry(wheelRadius - 0.081, 0.081, 14, 48), rubber, group)
    tire.rotation.y = Math.PI / 2
    tire.scale.z = 1.38
    const inner = mesh(new CylinderGeometry(wheelRadius - 0.085, wheelRadius - 0.085, 0.18, 40), black, group)
    inner.rotation.z = Math.PI / 2
    const disk = mesh(new CylinderGeometry(wheelRadius - 0.115, wheelRadius - 0.115, 0.015, 36), rimDark, group)
    disk.rotation.z = Math.PI / 2
    disk.position.x = side * 0.085
    const rimRadius = wheelRadius - 0.085
    const rim = mesh(new TorusGeometry(rimRadius, 0.011, 6, 44), chrome, group)
    rim.rotation.y = Math.PI / 2
    rim.position.x = side * 0.108
    const spokes = def.id === 'suv-02' ? 5 : luxury ? 10 : sport ? 10 : 8
    for (let i = 0; i < spokes; i++) {
      const angle = i * Math.PI * 2 / spokes
      const spoke = box([0.025, rimRadius * 0.86, luxury ? 0.022 : 0.030], [side * 0.105, Math.cos(angle) * rimRadius * 0.51, Math.sin(angle) * rimRadius * 0.51], chrome, group, 0.009)
      spoke.rotation.x = angle
      if (def.id === 'suv-02') {
        const secondary = box([0.027, rimRadius * 0.85, 0.022], [side * 0.111, Math.cos(angle + 0.15) * rimRadius * 0.51, Math.sin(angle + 0.15) * rimRadius * 0.51], chrome, group, 0.007)
        secondary.rotation.x = angle + 0.15
      }
    }
    const hub = mesh(new CylinderGeometry(0.055, 0.055, 0.033, 20), chrome, group)
    hub.rotation.z = Math.PI / 2
    hub.position.x = side * 0.112
    const center = mesh(new CylinderGeometry(0.029, 0.029, 0.005, 20), black, group)
    center.rotation.z = Math.PI / 2
    center.position.x = side * 0.132
    const caliper = box([0.033, 0.095, 0.068], [side * 0.066, 0.045, rimRadius * 0.65], sport ? paint : rimDark, group, 0.013)
    caliper.name = 'brake-caliper'
    for (const radius of [wheelRadius - 0.025, wheelRadius - 0.052]) {
      const ring = mesh(new TorusGeometry(radius, 0.002, 4, 40), rimDark, group)
      ring.rotation.y = Math.PI / 2
      ring.position.x = side * 0.092
    }
  }
  for (const side of [-1, 1]) {
    wheel(side, frontAxle, true)
    wheel(side, rearAxle, false)
  }

  let disposed = false
  function update(state: VehicleState, delta: number, elapsed: number, reducedMotion = false) {
    if (disposed) return
    const alpha = reducedMotion ? 1 : 1 - Math.exp(-9 * Math.min(Math.max(delta, 0), 0.1))
    for (const id of ['frontLeft', 'frontRight', 'rearLeft', 'rearRight'] as DoorId[]) {
      const side = id.endsWith('Left') ? 1 : -1
      const target = state.doors[id] ? -side * Math.PI * 0.37 : 0
      joints[id].rotation.y += (target - joints[id].rotation.y) * alpha
    }
    const trunkTarget = state.trunk ? Math.PI * (suv ? 0.55 : 0.40) : 0
    trunk.rotation.x += (trunkTarget - trunk.rotation.x) * alpha
    const steering = -Math.max(-30, Math.min(30, state.steeringAngle)) * Math.PI / 180
    for (const item of frontWheels) item.rotation.y += (steering - item.rotation.y) * alpha
    headLens.emissiveIntensity = state.headlights ? 3.2 : 0.08
    redLens.emissiveIntensity = state.headlights ? 1.6 : 0.08
    for (const light of beams) light.intensity = state.headlights ? 18 : 0
    const blinkOn = Math.floor(elapsed / 0.45) % 2 === 0
    signals.left.emissiveIntensity = blinkOn && (state.signal === 'left' || state.signal === 'hazard') ? 4 : 0
    signals.right.emissiveIntensity = blinkOn && (state.signal === 'right' || state.signal === 'hazard') ? 4 : 0
  }

  function dispose() {
    if (disposed) return
    disposed = true
    const geometries = new Set<BufferGeometry>()
    const materials = new Set<Material>()
    root.traverse(object => {
      if (object instanceof Mesh || object instanceof Line) {
        geometries.add(object.geometry)
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material)
      }
      if (object instanceof SpotLight) object.dispose()
    })
    geometries.forEach(geometry => geometry.dispose())
    materials.forEach(material => material.dispose())
    root.removeFromParent()
    root.clear()
  }

  return { root, joints, frontWheels, lights: { head: [headLens], tail: [redLens], left: [signals.left], right: [signals.right] }, update, dispose }
}
