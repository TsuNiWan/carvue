<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import CarvueBrand from '../components/CarvueBrand.vue'
import VehiclePreview from '../components/VehiclePreview.vue'
import VehicleControls from '../components/VehicleControls.vue'
import AdasControls from '../components/AdasControls.vue'
import NotFoundView from './NotFoundView.vue'
import { vehicles } from '../data/vehicles'
import { createVehiclePresentation, createVehicleState, type HotspotAction } from '../types/vehicle'
import { advanceScenario, createScenarioState, evaluateScenario, resetScenario, type ScenarioId } from '../adas/scenarios'

const VehicleViewer = defineAsyncComponent(() => import('../components/VehicleViewer.vue'))
const route = useRoute()
const selected = computed(() => vehicles.find(vehicle => vehicle.id === route.params.id))
const state = reactive(createVehicleState())
const presentation = ref(createVehiclePresentation())
const scenario = reactive(createScenarioState())
const activeTab = ref<'vehicle' | 'adas'>('vehicle')
const view = ref('free')
const viewRequest = ref(0)
const viewerReady = ref(false)
const sensors = reactive({ radar: true, camera: true, lidar: false, ultrasonic: true })
const frame = computed(() => selected.value ? evaluateScenario(scenario, state.signal, selected.value.length) : null)
const desktopQuery = window.matchMedia('(min-width: 1024px)')
const desktop = ref(desktopQuery.matches)
const hintVisible = ref(true)
const switcher = ref<HTMLDetailsElement>()
const tabs = ref<HTMLDivElement>()
const views = [{ id: 'free', label: '自由' }, { id: 'front', label: '前方' }, { id: 'rear', label: '後方' }, { id: 'side', label: '側面' }, { id: 'top', label: '俯視' }]

function setView(id: string) {
  view.value = id
  viewRequest.value++
}
function resetDisplay() {
  Object.assign(state, createVehicleState())
  Object.assign(scenario, { ...createScenarioState(), id: scenario.id })
  Object.assign(sensors, { radar: true, camera: true, lidar: false, ultrasonic: true })
  setView('free')
}
function setTab(tab: 'vehicle' | 'adas') {
  if (tab === activeTab.value) return
  activeTab.value = tab
  scenario.playing = false
  setView('free')
}
function tabKey(event: KeyboardEvent, tab: 'vehicle' | 'adas') {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const next = event.key === 'Home' ? 'vehicle' : event.key === 'End' ? 'adas' : tab === 'vehicle' ? 'adas' : 'vehicle'
  setTab(next)
  tabs.value?.querySelector<HTMLButtonElement>(`#${next}-tab`)?.focus()
}
function togglePart(action: HotspotAction) {
  if (!selected.value) return
  if (action === 'headlights' && selected.value.capabilities.headlights) state.headlights = !state.headlights
  else if (action === 'trunk' && selected.value.capabilities.trunk) state.trunk = !state.trunk
  else if (action !== 'headlights' && action !== 'trunk' && selected.value.capabilities.doors.includes(action)) state.doors[action] = !state.doors[action]
}
function setAllDoors(open: boolean) {
  for (const door of selected.value?.capabilities.doors ?? []) state.doors[door] = open
}
function chooseScenario(id: ScenarioId) {
  Object.assign(scenario, { ...createScenarioState(), id })
  setView('free')
}
function play() {
  if (!viewerReady.value) return
  if (scenario.progress >= 1) scenario.progress = 0
  scenario.playing = !scenario.playing
}
function scrub(progress: number) {
  scenario.playing = false
  scenario.progress = progress
}
function tick(delta: number) {
  if (activeTab.value === 'adas' && scenario.playing) Object.assign(scenario, advanceScenario(scenario, delta))
}
function ready(value: boolean) {
  viewerReady.value = value
  if (!value) scenario.playing = false
}
function viewportChanged() {
  desktop.value = desktopQuery.matches
  if (!desktop.value) {
    scenario.playing = false
    viewerReady.value = false
  }
}
function dismissMenus(event: MouseEvent) {
  if (switcher.value && !switcher.value.contains(event.target as Node)) switcher.value.open = false
}
function visibilityChanged() {
  if (document.hidden) scenario.playing = false
}
watch(() => selected.value?.id, () => {
  Object.assign(state, createVehicleState())
  Object.assign(scenario, createScenarioState())
  Object.assign(sensors, { radar: true, camera: true, lidar: false, ultrasonic: true })
  presentation.value = createVehiclePresentation()
  viewerReady.value = false
  activeTab.value = 'vehicle'
  if (switcher.value) switcher.value.open = false
  setView('free')
})
watch(selected, vehicle => { document.title = vehicle ? `${vehicle.name} · CARVUE 車映` : '找不到這款車 · CARVUE 車映' }, { immediate: true })
onMounted(() => {
  desktopQuery.addEventListener('change', viewportChanged)
  document.addEventListener('click', dismissMenus)
  document.addEventListener('visibilitychange', visibilityChanged)
})
onUnmounted(() => {
  desktopQuery.removeEventListener('change', viewportChanged)
  document.removeEventListener('click', dismissMenus)
  document.removeEventListener('visibilitychange', visibilityChanged)
})
</script>

<template>
  <div v-if="selected && frame" class="detail-shell">
    <header class="site-header detail-header">
      <CarvueBrand /><span class="header-separator"></span><RouterLink class="back-link" to="/vehicles"><AppIcon class="back-arrow" name="arrow" :size="17" />所有車款</RouterLink>
      <div class="detail-header-end">
        <details ref="switcher" class="model-switcher" @keydown.esc="switcher!.open = false">
          <summary>切換車款<AppIcon name="chevron" :size="16" /></summary>
          <nav aria-label="切換車款"><RouterLink v-for="vehicle in vehicles" :key="vehicle.id" :to="'/vehicles/' + vehicle.id" :data-testid="'select-' + vehicle.id" :class="{ selected: vehicle.id === selected.id }" :aria-current="vehicle.id === selected.id ? 'page' : undefined" @click="switcher!.open = false"><span><small>{{ vehicle.id.toUpperCase() }}</small>{{ vehicle.name }}</span><AppIcon v-if="vehicle.id === selected.id" name="check" :size="17" /></RouterLink></nav>
        </details>
        <button v-if="desktop" class="reset-button" @click="resetDisplay"><AppIcon name="reset" :size="17" />重設展示</button>
      </div>
    </header>

    <main v-if="desktop" class="showroom-workspace">
      <section id="main-stage" class="stage" :class="{ 'adas-stage': activeTab === 'adas' }" aria-label="3D 車輛展示">
        <VehicleViewer :vehicle="selected" :state="state" :scenario="scenario" :frame="frame" :adas="activeTab === 'adas'" :sensors="sensors" :view="view" :view-request="viewRequest" @tick="tick" @orbit="view = 'free'" @ready="ready" @presentation="presentation = $event" @hotspot="togglePart" />
        <div class="stage-heading"><p class="brand-name">{{ selected.id.toUpperCase() }}</p><h1>{{ selected.name }}</h1><p class="stage-trim">360° 互動賞車</p><span v-if="selected.asset.status === 'development'" class="development-badge">外觀開發預覽</span></div>
        <div v-if="activeTab === 'adas'" class="scene-callout" :class="frame.level"><AppIcon :name="frame.level === 'danger' ? 'warning' : 'radar'" :size="18" /><span>{{ frame.title }}</span><span class="callout-progress">{{ Math.round(scenario.progress * 100) }}%</span></div>
        <div class="stage-bottom">
          <div v-if="hintVisible && activeTab === 'vehicle' && viewerReady" class="explore-hint"><AppIcon name="mouse" :size="18" /><span>拖曳旋轉、滾輪縮放；點選車上熱點開啟部位。</span><button aria-label="關閉操作提示" @click="hintVisible = false">×</button></div>
          <div class="view-controls" role="group" aria-label="觀看視角"><button v-for="item in views" :key="item.id" :class="{ active: view === item.id }" :aria-pressed="view === item.id" @click="setView(item.id)">{{ item.label }}</button><span></span><button class="view-reset" aria-label="重設視角" title="重設視角" @click="setView('free')"><AppIcon name="reset" :size="18" /></button></div>
        </div>
      </section>

      <aside class="control-panel" aria-label="互動控制面板">
        <div ref="tabs" class="panel-tabs" role="tablist" aria-label="控制模式"><button id="vehicle-tab" role="tab" :aria-selected="activeTab === 'vehicle'" aria-controls="vehicle-panel" :tabindex="activeTab === 'vehicle' ? 0 : -1" :class="{ active: activeTab === 'vehicle' }" @click="setTab('vehicle')" @keydown="tabKey($event, 'vehicle')"><AppIcon name="car" :size="18" />車輛控制</button><button id="adas-tab" role="tab" aria-label="ADAS 情境" :aria-selected="activeTab === 'adas'" aria-controls="adas-panel" :tabindex="activeTab === 'adas' ? 0 : -1" :class="{ active: activeTab === 'adas' }" @click="setTab('adas')" @keydown="tabKey($event, 'adas')"><AppIcon name="radar" :size="18" />安全科技</button></div>
        <div v-if="activeTab === 'vehicle'" id="vehicle-panel" class="panel-content" role="tabpanel" aria-labelledby="vehicle-tab">
          <div class="panel-intro"><h2>細節，親手探索。</h2><p>{{ viewerReady ? '點選部位，即可開啟或關閉。' : '正在準備車輛，請稍候。' }}</p></div>
          <VehicleControls :vehicle="selected" :state="state" :presentation="presentation" :ready="viewerReady" @headlights="togglePart('headlights')" @trunk="togglePart('trunk')" @door="togglePart" @doors="setAllDoors" @signal="state.signal = $event" @steering="state.steeringAngle = $event" />
          <details class="vehicle-information"><summary>車輛資訊<AppIcon name="chevron" :size="16" /></summary><div><dl><div><dt>車身形式</dt><dd>{{ selected.bodyStyle === 'suv' ? '休旅車' : '四門轎車' }}</dd></div><div><dt>長 × 寬 × 高</dt><dd>{{ selected.length }} × {{ selected.width }} × {{ selected.height }} m</dd></div><div><dt>軸距</dt><dd>{{ selected.wheelbase }} m</dd></div></dl></div></details>
        </div>
        <div v-else id="adas-panel" class="panel-content adas-content" role="tabpanel" aria-labelledby="adas-tab"><div class="panel-intro"><h2>看見安全，如何發生。</h2></div><AdasControls :scenario="scenario" :frame="frame" :signal="state.signal" :sensors="sensors" :ready="viewerReady" @scenario="chooseScenario" @signal="state.signal = $event" @side="scenario.side = $event" @play="play" @reset="Object.assign(scenario, resetScenario(scenario))" @scrub="scrub" @sensor="(id, visible) => sensors[id] = visible" /></div>
        <footer class="viewer-status"><span class="status-dot" :class="{ ready: viewerReady }"></span>{{ viewerReady ? '互動展示已就緒' : '3D 展示尚未就緒' }}</footer>
      </aside>
    </main>

    <main v-else class="mobile-fallback"><p class="brand-name">{{ selected.id.toUpperCase() }}</p><h1>{{ selected.name }}</h1><p class="vehicle-trim">360° 互動賞車</p><VehiclePreview :vehicle="selected" eager /><div class="mobile-message"><AppIcon name="expand" :size="27" /><h2>請在桌機開啟完整 3D 體驗</h2><p>使用寬螢幕搭配滑鼠，即可自由旋轉車身，開啟車門與後廂、探索燈光細節。</p><p class="mobile-requirement">建議使用 1280px 以上的桌機視窗</p><RouterLink class="primary-link" to="/vehicles">所有車款<AppIcon name="arrow" :size="17" /></RouterLink></div></main>
  </div>
  <NotFoundView v-else />
</template>
