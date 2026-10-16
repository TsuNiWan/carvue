<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { loadVehicle } from '../three/loadVehicle'
import { partIds, type AssetRig } from '../three/assetRig'
import { assetUrl } from '../data/vehicles'
import { createAdasScene } from '../three/adasScene'
import { createVehiclePresentation, type VehicleDefinition, type VehicleState, type VehiclePresentation, type HotspotAction } from '../types/vehicle'
import type { ScenarioFrame, ScenarioState } from '../adas/scenarios'

const props = defineProps<{
  vehicle: VehicleDefinition
  state: VehicleState
  scenario: ScenarioState
  frame: ScenarioFrame
  adas: boolean
  sensors: Record<'radar' | 'camera' | 'lidar' | 'ultrasonic', boolean>
  view: string
  viewRequest: number
}>()
const emit = defineEmits<{ tick: [delta: number]; orbit: []; ready: [value: boolean]; presentation: [value: VehiclePresentation]; hotspot: [action: HotspotAction] }>()
const host = ref<HTMLDivElement>()
const error = ref('')
const ready = ref(false)
const loading = ref(false)
const loadProgress = ref(0)
const loadState = ref<'loading' | 'ready' | 'error'>('loading')
const mountedVehicleId = ref('')
const hotspots = ref<{ id: HotspotAction; label: string; x: number; y: number; active: boolean }[]>([])
const projectedLabels = ref<{ id: string; text: string; x: number; y: number; color: string }[]>([])
const development = import.meta.env.DEV
const diagnostics = ref({ frames: 0, fps: 0, geometries: 0, textures: 0, vehicleId: '', camera: '[]', doorAngles: '{}', steering: '[]', lights: '{}', presentation: '{}', frameTimes: '[]' })
let renderer: THREE.WebGLRenderer | undefined
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let controls: OrbitControls
let rig: AssetRig | undefined
let loadController: AbortController | undefined
let loadSequence = 0
let hotspotTime = 0
let presentationTime = 0
let labelTime = 0
let hotspotsDirty = true
let cameraInteracting = false
let cameraHotspotsHidden = false
let cameraQuietTime = 0
let lastPresentation = createVehiclePresentation()
const raycaster = new THREE.Raycaster()
const rawFrameTimes: number[] = []
let adasScene: ReturnType<typeof createAdasScene> | undefined
let environment: THREE.WebGLRenderTarget | undefined
let resizeObserver: ResizeObserver | undefined
let motionQuery: MediaQueryList
let reducedMotion = false
let animationId = 0
let previousTime = 0
let elapsed = 0
let metricTime = 0
let metricFrames = 0
let totalFrames = 0
let disposed = false
let contextAvailable = false
let cameraTween: { from: THREE.Vector3; to: THREE.Vector3; targetFrom: THREE.Vector3; targetTo: THREE.Vector3; elapsed: number } | undefined
const initialDirection = new THREE.Vector3(1.2, 0.76, 1.65).normalize()
const stageResources: (THREE.BufferGeometry | THREE.Material)[] = []

function baseDistance() {
  const vertical = rig?.framing.distance ?? props.vehicle.length * 1.62
  return Math.max(vertical, props.vehicle.length / Math.max(camera.aspect, 0.5) * 1.6)
}
function frameTarget() {
  if (!props.adas && rig) return new THREE.Vector3(...rig.framing.target)
  return new THREE.Vector3(0, props.adas ? 0.5 : props.vehicle.height * 0.44, props.adas && props.scenario.id === 'pedestrian' ? 1.7 : props.adas && props.scenario.id === 'parking' ? -2.6 : 0)
}
function fitDistance(direction: THREE.Vector3) {
  if (!props.adas && !rig) return baseDistance()
  const half = props.vehicle.length / 2
  const points: THREE.Vector3[] = []
  function includeBox(xMin: number, xMax: number, zMin: number, zMax: number, height: number) {
    for (const x of [xMin, xMax]) for (const z of [zMin, zMax]) for (const y of [0, height]) points.push(new THREE.Vector3(x, y, z))
  }
  if (!props.adas && rig) {
    // Frame the current articulated pose, including raised SUV tailgates.
    rig.root.updateWorldMatrix(true, true)
    const bounds = new THREE.Box3().setFromObject(rig.root)
    includeBox(bounds.min.x, bounds.max.x, bounds.min.z, bounds.max.z, bounds.max.y)
  } else {
    includeBox(-props.vehicle.width / 2 - 0.3, props.vehicle.width / 2 + 0.3, -half - 0.2, half + 0.2, props.vehicle.height)
    if (props.scenario.id === 'pedestrian') includeBox(-6.4, 6.4, half + 2.7, half + 3.3, 2.1)
    if (props.scenario.id === 'blindSpot') includeBox(-3.5, 3.5, -half - 9.5, half + 9.5, 1.8)
    if (props.scenario.id === 'parking') includeBox(-1, 1, -half - 6.5, -half - 0.3, 1.3)
  }
  const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), direction).normalize()
  const up = new THREE.Vector3().crossVectors(direction, right).normalize()
  const tangent = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
  const target = frameTarget()
  let distance = baseDistance()
  for (const point of points) {
    const relative = point.sub(target)
    const depth = relative.dot(direction)
    distance = Math.max(distance, depth + Math.abs(relative.dot(right)) / (tangent * camera.aspect * 0.86), depth + Math.abs(relative.dot(up)) / (tangent * (props.adas ? 0.66 : 0.86)))
  }
  return distance
}
function moveCamera(view: string, animate = true) {
  if (!camera || !controls || !contextAvailable) return
  hideCameraHotspots()
  hotspotsDirty = true
  const target = frameTarget()
  let direction = rig ? new THREE.Vector3(...rig.framing.direction).normalize() : initialDirection.clone()
  if (view === 'front') direction.set(0, 0.26, 1).normalize()
  if (view === 'rear') direction.set(0, 0.3, -1).normalize()
  if (view === 'side') direction.set(1, 0.17, 0).normalize()
  if (view === 'top') direction.set(0, 1, 0.025).normalize()
  if (props.adas && view === 'free') direction.set(0.8, 1.25, 1.2).normalize()
  const distance = fitDistance(direction) * (!props.adas && view === 'top' ? 1.15 : 1)
  const position = target.clone().addScaledVector(direction, distance)
  if (animate && !reducedMotion) {
    cameraTween = { from: camera.position.clone(), to: position, targetFrom: controls.target.clone(), targetTo: target, elapsed: 0 }
    controls.enabled = false
  } else {
    cameraTween = undefined
    controls.enabled = true
    camera.position.copy(position)
    controls.target.copy(target)
    controls.update()
  }
}
async function syncVehicle() {
  if (!scene || !controls || !contextAvailable) return
  loadController?.abort()
  const controller = new AbortController()
  loadController = controller
  const sequence = ++loadSequence
  const vehicle = props.vehicle
  ready.value = false
  loading.value = true
  loadState.value = 'loading'
  loadProgress.value = 0
  error.value = ''
  hotspots.value = []
  mountedVehicleId.value = ''
  emit('ready', false)
  lastPresentation = createVehiclePresentation()
  emit('presentation', lastPresentation)
  renderer!.domElement.dataset.ready = 'false'
  if (rig) { scene.remove(rig.root); rig.dispose(); rig = undefined }
  if (adasScene) { scene.remove(adasScene.root); adasScene.dispose(); adasScene = undefined }
  try {
    const next = await loadVehicle(vehicle, controller.signal, progress => {
      if (sequence === loadSequence && !disposed) loadProgress.value = progress
    }, candidate => renderer!.compileAsync(candidate.root, camera, scene))
    if (sequence !== loadSequence || controller.signal.aborted || disposed || !contextAvailable) { next.dispose(); return }
    rig = next
    hotspotsDirty = true
    rig.update(props.state, 0, elapsed, reducedMotion)
    scene.add(rig.root)
    adasScene = createAdasScene(vehicle)
    scene.add(adasScene.root)
    adasScene.root.visible = props.adas
    cameraTween = undefined
    controls.enabled = true
    controls.minDistance = vehicle.length * 0.72
    controls.maxDistance = vehicle.length * 9
    moveCamera(props.view, false)
    if (development) performance.mark('carvue-load:first-render-start')
    renderer!.render(scene, camera)
    if (development) performance.mark('carvue-load:first-render-end')
    mountedVehicleId.value = vehicle.id
    loading.value = false
    loadProgress.value = 1
    loadState.value = 'ready'
    ready.value = true
    renderer!.domElement.dataset.ready = 'true'
    previousTime = 0
    rawFrameTimes.length = 0
    updateMetrics()
    emit('ready', true)
  } catch (cause) {
    if (sequence !== loadSequence || disposed || controller.signal.aborted) return
    controller.abort()
    console.error('Unable to load the vehicle model.', cause)
    loading.value = false
    loadState.value = 'error'
    error.value = '車輛模型載入失敗。請確認連線後重新載入，或返回車款總覽。'
  }
}
function addStage() {
  const groundGeometry = new THREE.CircleGeometry(70, 96)
  const groundMaterial = new THREE.MeshStandardMaterial({ color: '#070e11', roughness: 0.94, metalness: 0.05 })
  const ground = new THREE.Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.035
  ground.receiveShadow = true
  scene.add(ground)
  stageResources.push(groundGeometry, groundMaterial)

  const platformGeometry = new THREE.CylinderGeometry(4.05, 4.09, 0.025, 128)
  const platformMaterial = new THREE.MeshStandardMaterial({ color: '#111b1e', roughness: 0.85, metalness: 0.14 })
  const platform = new THREE.Mesh(platformGeometry, platformMaterial)
  platform.position.y = -0.018
  platform.receiveShadow = true
  scene.add(platform)
  stageResources.push(platformGeometry, platformMaterial)

  for (const radius of [4.1, 4.22]) {
    const geometry = new THREE.RingGeometry(radius, radius + 0.008, 128)
    const material = new THREE.MeshBasicMaterial({ color: '#6b9981', transparent: true, opacity: radius === 4.1 ? 0.4 : 0.12, depthWrite: false, side: THREE.DoubleSide })
    const ring = new THREE.Mesh(geometry, material)
    ring.rotation.x = -Math.PI / 2
    ring.position.y = -0.013
    scene.add(ring)
    stageResources.push(geometry, material)
  }
  const points: number[] = []
  for (let i = 0; i < 72; i++) {
    const theta = i * Math.PI * 2 / 72
    const a = 4.3
    const b = i % 6 === 0 ? 4.43 : 4.35
    points.push(Math.sin(theta) * a, -0.008, Math.cos(theta) * a, Math.sin(theta) * b, -0.008, Math.cos(theta) * b)
  }
  const marksGeometry = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(points, 3))
  const marksMaterial = new THREE.LineBasicMaterial({ color: '#749781', transparent: true, opacity: 0.24 })
  scene.add(new THREE.LineSegments(marksGeometry, marksMaterial))
  stageResources.push(marksGeometry, marksMaterial)
}
function resize() {
  if (!renderer || !host.value) return
  const { width, height } = host.value.getBoundingClientRect()
  if (width <= 0 || height <= 0) return
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height, false)
  hotspotsDirty = true
  if (ready.value) moveCamera(props.view, false)
}
function updatePoseDiagnostics() {
  if (!rig || !development) return
  const angles: Record<string, number> = {}
  for (const [name, joint] of Object.entries(rig.joints)) angles[name] = name === 'trunk' ? joint.rotation.x : joint.rotation.y
  const lights: Record<string, number> = {}
  if (rig.lights) for (const [name, materials] of Object.entries(rig.lights)) lights[name] = materials.reduce((sum, material) => sum + material.emissiveIntensity, 0) / Math.max(1, materials.length)
  diagnostics.value.doorAngles = JSON.stringify(angles)
  diagnostics.value.steering = JSON.stringify(rig.frontWheels.map(w => w.rotation.y))
  diagnostics.value.lights = JSON.stringify(lights)
  diagnostics.value.presentation = JSON.stringify(rig.presentation)
}
function updateMetrics() {
  if (!development || !renderer || !rig) return
  updatePoseDiagnostics()
  Object.assign(diagnostics.value, { frames: totalFrames, fps: Math.round(metricFrames / Math.max(metricTime, 0.001)), geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures, vehicleId: mountedVehicleId.value, camera: JSON.stringify(camera.position.toArray()), frameTimes: JSON.stringify(rawFrameTimes) })
  metricTime = 0
  metricFrames = 0
}
function hideCameraHotspots() {
  cameraHotspotsHidden = true
  cameraQuietTime = 0
  hotspotsDirty = true
  if (document.activeElement instanceof HTMLElement && document.activeElement.dataset.hotspot) renderer?.domElement.focus({ preventScroll: true })
  if (hotspots.value.length) hotspots.value = []
}
function updateHotspots() {
  if (!host.value || !rig || props.adas || !ready.value || cameraHotspotsHidden) { if (hotspots.value.length) hotspots.value = []; return }
  const { width, height } = host.value.getBoundingClientRect()
  const next = rig.hotspots.flatMap(hotspot => {
    if (hotspot.id !== 'headlights') {
      const target = hotspot.id === 'trunk' ? props.state.trunk : props.state.doors[hotspot.id]
      if (rig!.presentation.parts[hotspot.id] !== Number(target)) return []
    }
    const world = hotspot.anchor.localToWorld(hotspot.position.clone())
    const screen = world.clone().project(camera)
    const x = (screen.x + 1) * width / 2
    const y = (1 - screen.y) * height / 2
    if (screen.z < -1 || screen.z > 1 || x < 40 || x > width - 40 || y < 115 || y > height - 100) return []
    const direction = world.clone().sub(camera.position)
    const distance = direction.length()
    raycaster.set(camera.position, direction.normalize())
    raycaster.far = Math.max(0, distance - 0.075)
    const blocked = raycaster.intersectObject(rig!.root, true).some(hit => {
      const mesh = hit.object as THREE.Mesh
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
      return materials.some(material => material && (!material.transparent || material.opacity > 0.8))
    })
    if (blocked) return []
    const active = hotspot.id === 'headlights' ? props.state.headlights : hotspot.id === 'trunk' ? props.state.trunk : props.state.doors[hotspot.id]
    return [{ id: hotspot.id, label: hotspot.label, x, y, active }]
  })
  const focused = document.activeElement instanceof HTMLElement ? document.activeElement.dataset.hotspot : undefined
  if (focused && !next.some(hotspot => hotspot.id === focused)) renderer?.domElement.focus({ preventScroll: true })
  hotspots.value = next
}
function updateLabels() {
  if (!host.value || !adasScene || !props.adas) { if (projectedLabels.value.length) projectedLabels.value = []; return }
  const { width, height } = host.value.getBoundingClientRect()
  projectedLabels.value = adasScene.labels.flatMap(label => {
    const point = label.position.clone().project(camera)
    const x = (point.x + 1) * width / 2
    const y = (-point.y + 1) * height / 2
    if (point.z < -1 || point.z > 1 || x < 40 || x > width - 100 || y < 145 || y > height - 150) return []
    return [{ id: label.id, text: label.text, x, y, color: label.color }]
  })
}
function render(time: number) {
  if (disposed || document.hidden || !renderer || !contextAvailable) return
  const rawDelta = previousTime ? (time - previousTime) / 1000 : 0
  const delta = Math.min(rawDelta, 0.05)
  previousTime = time
  elapsed += rawDelta
  const cameraWasAnimating = Boolean(cameraTween)
  if (cameraTween) {
    cameraTween.elapsed += rawDelta
    const t = Math.min(cameraTween.elapsed / 0.4, 1)
    const ease = 1 - Math.pow(1 - t, 3)
    camera.position.lerpVectors(cameraTween.from, cameraTween.to, ease)
    controls.target.lerpVectors(cameraTween.targetFrom, cameraTween.targetTo, ease)
    if (t === 1) { cameraTween = undefined; controls.enabled = true }
  }
  const cameraChanged = controls.update(delta)
  if (cameraChanged || cameraWasAnimating) hotspotsDirty = true
  if (cameraHotspotsHidden && !cameraInteracting && !cameraWasAnimating && !cameraChanged) {
    cameraQuietTime += delta
    if (cameraQuietTime >= 0.12) { cameraHotspotsHidden = false; hotspotsDirty = true }
  }
  ;(scene.fog as THREE.FogExp2).density = props.adas ? 0.01 : 0.045
  rig?.update(props.state, rawDelta, elapsed, reducedMotion)
  if (adasScene) {
    adasScene.root.visible = props.adas
    if (props.adas) adasScene.update(props.frame, props.scenario, props.sensors, reducedMotion ? 0 : elapsed)
  }
  renderer.render(scene, camera)
  totalFrames++
  if (development && rawDelta > 0 && ready.value) {
    rawFrameTimes.push(rawDelta * 1000)
    if (rawFrameTimes.length > 4096) rawFrameTimes.shift()
  }
  if (development) {
    metricFrames++
    metricTime += rawDelta
    if (metricTime >= 0.25) updateMetrics()
  }
  hotspotTime += rawDelta
  presentationTime += rawDelta
  labelTime += rawDelta
  if (rig && presentationTime >= 1 / 30) {
    const current = rig.presentation
    const changed = current.headlights !== lastPresentation.headlights || current.steeringAngle !== lastPresentation.steeringAngle || partIds.some(id => current.parts[id] !== lastPresentation.parts[id])
    if (changed) {
      lastPresentation = { ...current, parts: { ...current.parts } }
      emit('presentation', lastPresentation)
      hotspotsDirty = true
    }
    updatePoseDiagnostics()
    presentationTime = 0
  }
  if (hotspotsDirty && hotspotTime >= 1 / 30) { updateHotspots(); hotspotsDirty = false; hotspotTime = 0 }
  if (labelTime >= 1 / 30) { updateLabels(); labelTime = 0 }
  if (ready.value && props.adas && props.scenario.playing) emit('tick', rawDelta)
  animationId = requestAnimationFrame(render)
}
function visibilityChanged() {
  cancelAnimationFrame(animationId)
  previousTime = 0
  metricTime = 0
  metricFrames = 0
  if (!document.hidden && !disposed && renderer && contextAvailable) animationId = requestAnimationFrame(render)
}
function motionChanged() { reducedMotion = motionQuery.matches }
function takeCameraControl() {
  if (!cameraTween) return
  cameraTween = undefined
  controls.enabled = true
  emit('orbit')
}
function keyboard(event: KeyboardEvent) {
  if (!controls || !renderer || !contextAvailable) return
  const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-', 'Home']
  if (!keys.includes(event.key)) return
  event.preventDefault()
  hotspotsDirty = true
  cameraTween = undefined
  controls.enabled = true
  if (event.key === 'Home') { moveCamera('free'); emit('orbit'); return }
  const spherical = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target))
  if (event.key === 'ArrowLeft') spherical.theta += 0.12
  if (event.key === 'ArrowRight') spherical.theta -= 0.12
  if (event.key === 'ArrowUp') spherical.phi = Math.max(controls.minPolarAngle, spherical.phi - 0.1)
  if (event.key === 'ArrowDown') spherical.phi = Math.min(controls.maxPolarAngle, spherical.phi + 0.1)
  if (event.key === '+' || event.key === '=') spherical.radius = Math.max(controls.minDistance, spherical.radius * 0.92)
  if (event.key === '-') spherical.radius = Math.min(controls.maxDistance, spherical.radius * 1.08)
  camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical))
  controls.update()
  emit('orbit')
}
function contextLost(event: Event) {
  event.preventDefault()
  cancelAnimationFrame(animationId)
  contextAvailable = false
  loadController?.abort()
  loading.value = false
  loadState.value = 'error'
  hotspots.value = []
  ready.value = false
  if (renderer) renderer.domElement.dataset.ready = 'false'
  emit('ready', false)
  error.value = '3D 顯示暫時中斷。請重新整理頁面；若持續發生，請確認瀏覽器已啟用硬體加速。'
}

onMounted(() => {
  try {
    motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    motionChanged()
    motionQuery.addEventListener('change', motionChanged)
    scene = new THREE.Scene()
    scene.background = new THREE.Color('#111a1d')
    scene.fog = new THREE.FogExp2('#111a1d', 0.045)
    camera = new THREE.PerspectiveCamera(36, 1, 0.1, 120)
    camera.position.copy(initialDirection).multiplyScalar(props.vehicle.length * 1.62)
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.12
    renderer.setClearColor('#172220', 0)
    const canvas = renderer.domElement
    canvas.setAttribute('aria-label', '車輛 3D 場景')
    canvas.setAttribute('role', 'img')
    canvas.setAttribute('aria-description', '拖曳旋轉、滾輪縮放。聚焦後可用方向鍵旋轉、加減鍵縮放、Home 重設。')
    canvas.tabIndex = 0
    canvas.addEventListener('keydown', keyboard)
    canvas.addEventListener('pointerdown', takeCameraControl, true)
    canvas.addEventListener('webglcontextlost', contextLost)
    host.value!.prepend(canvas)
    controls = new OrbitControls(camera, canvas)
    controls.enableDamping = true
    controls.dampingFactor = 0.075
    controls.enablePan = false
    controls.minPolarAngle = 0.03
    controls.maxPolarAngle = Math.PI / 2 - 0.045
    controls.zoomSpeed = 0.6
    controls.rotateSpeed = 0.65
    controls.addEventListener('change', hideCameraHotspots)
    controls.addEventListener('start', () => { cameraInteracting = true; hideCameraHotspots(); cameraTween = undefined; controls.enabled = true; emit('orbit') })
    controls.addEventListener('end', () => { cameraInteracting = false })
    contextAvailable = true
    resize()
    // Start network I/O before the synchronous environment and stage preparation.
    void syncVehicle()
    if (development) performance.mark('carvue-load:environment-start')
    const pmrem = new THREE.PMREMGenerator(renderer)
    const room = new RoomEnvironment()
    environment = pmrem.fromScene(room, 0.04)
    scene.environment = environment.texture
    scene.environmentIntensity = 0.85
    room.dispose()
    pmrem.dispose()
    if (development) performance.mark('carvue-load:environment-ready')
    scene.add(new THREE.HemisphereLight('#ffffff', '#858585', 1.3))
    const key = new THREE.DirectionalLight('#ffffff', 2.6)
    key.position.set(4, 8, 5)
    key.castShadow = true
    key.shadow.mapSize.set(1024, 1024)
    Object.assign(key.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7, near: 1, far: 25 })
    key.shadow.bias = -0.0003
    key.shadow.normalBias = 0.035
    scene.add(key)
    const rim = new THREE.DirectionalLight('#ffffff', 2.4)
    rim.position.set(-5, 4, -4)
    scene.add(rim)
    addStage()
    moveCamera('free', false)
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(host.value!)
    document.addEventListener('visibilitychange', visibilityChanged)
    animationId = requestAnimationFrame(render)
  } catch (cause) {
    contextAvailable = false
    loadController?.abort()
    console.error('Unable to initialize the 3D viewer.', cause)
    error.value = '無法啟動 3D 顯示。請使用支援 WebGL 2 的 Chrome 或 Edge，並確認已開啟硬體加速。'
    loadState.value = 'error'
    loading.value = false
    emit('ready', false)
  }
})
watch(() => props.vehicle.id, syncVehicle)
watch(() => [props.adas, props.state.headlights, props.state.trunk, ...Object.values(props.state.doors)], () => { hotspotsDirty = true })
watch(() => props.viewRequest, () => moveCamera(props.view))
watch(() => props.adas, () => moveCamera(props.view))
watch(() => props.scenario.id, () => { if (props.adas) moveCamera(props.view) })
onUnmounted(() => {
  disposed = true
  loadSequence++
  loadController?.abort()
  cancelAnimationFrame(animationId)
  document.removeEventListener('visibilitychange', visibilityChanged)
  motionQuery?.removeEventListener('change', motionChanged)
  resizeObserver?.disconnect()
  controls?.dispose()
  rig?.dispose()
  adasScene?.dispose()
  stageResources.forEach(resource => resource.dispose())
  environment?.dispose()
  scene?.traverse(object => { if (object instanceof THREE.DirectionalLight) object.shadow.dispose() })
  renderer?.domElement.removeEventListener('keydown', keyboard)
  renderer?.domElement.removeEventListener('pointerdown', takeCameraControl, true)
  renderer?.domElement.removeEventListener('webglcontextlost', contextLost)
  renderer?.dispose()
  renderer?.domElement.remove()
})
</script>

<template>
  <div ref="host" class="viewer" :aria-busy="!ready && !error">
    <div v-if="loading" class="model-loading" role="status" aria-live="polite">
      <img :src="assetUrl(vehicle.asset.posterUrl)" :alt="vehicle.name + ' 模型預覽'" @error="($event.target as HTMLImageElement).style.visibility = 'hidden'" />
      <strong>{{ loadProgress < 0.92 ? '正在載入 ' + vehicle.name : '正在準備展示細節' }}</strong>
      <progress :value="loadProgress" max="1" aria-label="模型載入進度"></progress>
      <span>{{ Math.round(loadProgress * 100) }}%</span>
    </div>
    <div v-if="error" class="viewer-error" role="alert"><p>{{ error }}</p><button v-if="contextAvailable" type="button" @click="syncVehicle">重新載入模型</button></div>
    <button v-for="hotspot in hotspots" :key="hotspot.id" class="vehicle-hotspot" :class="{ active: hotspot.active }" :data-hotspot="hotspot.id" :style="{ left: hotspot.x + 'px', top: hotspot.y + 'px' }" :aria-label="hotspot.label + '熱點'" :aria-pressed="hotspot.active" :title="hotspot.label" @click="emit('hotspot', hotspot.id)"><span aria-hidden="true">{{ hotspot.active ? '−' : '+' }}</span><span class="hotspot-label">{{ hotspot.label }}</span></button>
    <span v-for="label in projectedLabels" :key="label.id" class="sensor-world-label" :style="{ left: label.x + 'px', top: label.y + 'px', color: label.color }">{{ label.text }}</span>
    <span v-if="development" hidden data-testid="renderer-diagnostics" :data-frames="diagnostics.frames" :data-fps="diagnostics.fps" :data-geometries="diagnostics.geometries" :data-textures="diagnostics.textures" :data-vehicle-id="mountedVehicleId" :data-load-state="loadState" :data-load-progress="loadProgress" :data-presentation="diagnostics.presentation" :data-frame-times="diagnostics.frameTimes" :data-camera="diagnostics.camera" :data-door-angles="diagnostics.doorAngles" :data-steering="diagnostics.steering" :data-lights="diagnostics.lights"></span>
  </div>
</template>

<style scoped>
.model-loading { position: absolute; inset: 0; z-index: 6; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; background: #151b1ef5; color: #e8efeb; }
.model-loading img { width: min(70%, 520px); max-height: 45%; object-fit: contain; }
.model-loading strong { font-size: 16px; font-weight: 500; }
.model-loading progress { width: 200px; height: 4px; accent-color: #a6e5c5; }
.model-loading > span { font-size: 12px; color: #b4beba; }
.viewer-error { z-index: 8; }
.viewer-error button { min-height: 44px; margin-top: 12px; padding: 8px 20px; border: 1px solid #a6e5c5; border-radius: 6px; color: #a6e5c5; background: #182822; cursor: pointer; }
.vehicle-hotspot { position: absolute; z-index: 4; transform: translate(-50%, -50%); width: 44px; height: 44px; padding: 0; border-radius: 50%; border: 0; background: transparent; color: #dcffed; cursor: pointer; display: grid; place-items: center; font-size: 18px; }
.vehicle-hotspot { animation: hotspot-reveal 120ms ease-out; }
@keyframes hotspot-reveal { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .vehicle-hotspot { animation: none; } }
.vehicle-hotspot > span:first-child { width: 28px; height: 28px; display: grid; place-items: center; border: 1px solid #d8ead9ba; border-radius: 50%; background: #10231cce; box-shadow: 0 0 0 3px #afebc815; }
.vehicle-hotspot:hover > span:first-child, .vehicle-hotspot:focus-visible > span:first-child, .vehicle-hotspot.active > span:first-child { background: #b9efcf; color: #14231a; }
.vehicle-hotspot:focus-visible { outline: 2px solid #fff; outline-offset: 4px; }
.hotspot-label { position: absolute; left: 50%; top: calc(100% + 9px); transform: translateX(-50%); white-space: nowrap; font-size: 12px; color: #e1eae4; background: #101915e8; padding: 4px 8px; border-radius: 4px; opacity: 0; pointer-events: none; }
.vehicle-hotspot:hover .hotspot-label, .vehicle-hotspot:focus-visible .hotspot-label { opacity: 1; }
</style>
