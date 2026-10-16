<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { scenarioDefinitions, type ScenarioFrame, type ScenarioId, type ScenarioState, type Side } from '../adas/scenarios'
import type { Signal } from '../types/vehicle'

const props = defineProps<{ scenario: ScenarioState; frame: ScenarioFrame; signal: Signal; sensors: Record<'radar' | 'camera' | 'lidar' | 'ultrasonic', boolean>; ready: boolean }>()
const emit = defineEmits<{ scenario: [id: ScenarioId]; signal: [value: Signal]; side: [value: Side]; play: []; reset: []; scrub: [value: number]; sensor: [id: keyof typeof props.sensors, visible: boolean] }>()
const definition = computed(() => scenarioDefinitions.find(item => item.id === props.scenario.id)!)
const signals: { id: Signal; label: string }[] = [
  { id: 'off', label: '關閉' }, { id: 'left', label: '左轉' }, { id: 'right', label: '右轉' }, { id: 'hazard', label: '雙黃燈' },
]
const sensorEntries = [
  { id: 'radar' as const, label: '雷達', color: '#78c6b0' },
  { id: 'camera' as const, label: '攝影機', color: '#78aff0' },
  { id: 'lidar' as const, label: 'LiDAR', color: '#b5a0e8' },
  { id: 'ultrasonic' as const, label: '超音波', color: '#eac078' },
]
</script>

<template>
  <div class="adas-controls">
    <div class="adas-disclaimer"><AppIcon name="info" :size="17" /><p>安全科技原理示意</p></div>
    <div class="scenario-list"><button v-for="(item, index) in scenarioDefinitions" :key="item.id" :class="{ active: scenario.id === item.id }" :aria-pressed="scenario.id === item.id" @click="emit('scenario', item.id)"><span class="scenario-number">0{{ index + 1 }}</span><span><strong>{{ item.title }}</strong><small>{{ item.subtitle }}</small></span><AppIcon name="chevron" :size="16" /></button></div>
    <div v-if="scenario.id === 'blindSpot'" class="blind-options">
      <div class="field-label">鄰車位置</div><div class="segmented"><button :class="{ active: scenario.side === 'left' }" :aria-pressed="scenario.side === 'left'" @click="emit('side', 'left')">左側</button><button :class="{ active: scenario.side === 'right' }" :aria-pressed="scenario.side === 'right'" @click="emit('side', 'right')">右側</button></div>
      <div class="field-label">搭配方向燈觀察警示</div><div class="segmented signal-controls"><button v-for="signal in signals" :key="signal.id" :aria-pressed="props.signal === signal.id" :class="{ active: props.signal === signal.id, amber: props.signal === signal.id && signal.id !== 'off' }" @click="emit('signal', signal.id)">{{ signal.label }}</button></div>
    </div>
    <div class="scenario-status" :class="frame.level" role="status" aria-live="polite"><div><AppIcon :name="frame.level === 'danger' ? 'warning' : 'shield'" :size="20" /><strong>{{ frame.title }}</strong></div><p>{{ frame.description }}</p></div>
    <div class="distance-reading" aria-live="off"><span>{{ scenario.id === 'parking' ? '車尾至障礙物' : scenario.id === 'pedestrian' ? '車頭至行人中心' : '車身中線至鄰車中心' }}<small>示意參考距離</small></span><span>{{ frame.distance.toFixed(1) }}<small>m</small></span></div>
    <section class="playback" aria-label="情境播放控制">
      <div class="playback-buttons"><button class="primary-button" :disabled="!ready" @click="emit('play')"><AppIcon :name="scenario.playing ? 'pause' : 'play'" :size="18" />{{ scenario.playing ? '暫停情境' : scenario.progress >= 1 ? '重新播放' : '播放情境' }}</button><button class="icon-button" aria-label="重設情境" title="重設情境" @click="emit('reset')"><AppIcon name="reset" :size="19" /></button></div>
      <input class="range-input" type="range" min="0" max="100" step="0.1" :value="scenario.progress * 100" aria-label="情境進度" @input="emit('scrub', Number(($event.target as HTMLInputElement).value) / 100)" />
      <div class="range-legend"><span>{{ (scenario.progress * definition.duration).toFixed(1) }} / {{ definition.duration }} 秒</span><span>{{ Math.round(scenario.progress * 100) }}%</span></div>
    </section>
    <section class="control-section sensor-section"><div class="section-title"><AppIcon name="eye" :size="19" /><h3>感測視覺圖層</h3></div><div class="sensor-grid"><label v-for="sensor in sensorEntries" :key="sensor.id" :style="{ '--sensor-color': sensor.color }"><input :checked="sensors[sensor.id]" type="checkbox" @change="emit('sensor', sensor.id, ($event.target as HTMLInputElement).checked)" /><span class="sensor-check"><AppIcon name="check" :size="13" /></span><span class="sensor-color"></span>{{ sensor.label }}</label></div><p class="sensor-note">圖層僅影響顯示，不改變情境判斷。</p></section>
  </div>
</template>
