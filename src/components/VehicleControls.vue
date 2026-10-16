<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import type { DoorId, PartId, Signal, VehicleDefinition, VehiclePresentation, VehicleState } from '../types/vehicle'

const props = defineProps<{ vehicle: VehicleDefinition; state: VehicleState; presentation: VehiclePresentation; ready: boolean }>()
const emit = defineEmits<{ headlights: []; trunk: []; door: [id: DoorId]; doors: [open: boolean]; signal: [value: Signal]; steering: [value: number] }>()
const doors: { id: DoorId; label: string }[] = [
  { id: 'frontLeft', label: '左前門' }, { id: 'frontRight', label: '右前門' },
  { id: 'rearLeft', label: '左後門' }, { id: 'rearRight', label: '右後門' },
]
const signals: { id: Signal; label: string }[] = [
  { id: 'off', label: '關閉' }, { id: 'left', label: '左轉' }, { id: 'right', label: '右轉' }, { id: 'hazard', label: '雙黃燈' },
]
function partStatus(id: PartId, open: boolean) {
  const value = props.presentation.parts[id]
  if (value !== Number(open)) return open ? '開啟中' : '關閉中'
  return open ? '已開啟' : '已關閉'
}
function lightStatus() {
  if (props.presentation.headlights !== Number(props.state.headlights)) return props.state.headlights ? '點亮中' : '熄滅中'
  return props.state.headlights ? '已點亮' : '已關閉'
}
</script>

<template>
  <fieldset class="vehicle-controls-fields" :disabled="!ready">
    <legend class="sr-only">車輛互動控制</legend>
    <section v-if="vehicle.capabilities.headlights || vehicle.capabilities.signals" class="control-section">
      <div class="section-title"><AppIcon name="light" :size="19" /><h3>車輛照明</h3></div>
      <div v-if="vehicle.capabilities.headlights" class="switch-row"><span>頭燈與尾燈<small>{{ lightStatus() }}</small></span><button class="toggle" role="switch" aria-label="頭燈與尾燈" :aria-checked="state.headlights" @click="emit('headlights')"><span></span></button></div>
      <template v-if="vehicle.capabilities.signals"><div class="field-label">方向燈</div><div class="segmented signal-controls"><button v-for="signal in signals" :key="signal.id" :aria-pressed="state.signal === signal.id" :class="{ active: state.signal === signal.id, amber: state.signal === signal.id && signal.id !== 'off' }" @click="emit('signal', signal.id)">{{ signal.label }}</button></div></template>
    </section>
    <section v-if="vehicle.capabilities.doors.length" class="control-section">
      <div class="section-title"><AppIcon name="door" :size="19" /><h3>車門開合</h3><span class="section-note">點選開啟或關閉</span></div>
      <div class="door-grid"><button v-for="door in doors.filter(item => vehicle.capabilities.doors.includes(item.id))" :key="door.id" class="door-button" :class="{ active: state.doors[door.id] }" :aria-pressed="state.doors[door.id]" :aria-label="door.label" @click="emit('door', door.id)"><AppIcon name="door" :size="20" /><span>{{ door.label }}<small>{{ partStatus(door.id, state.doors[door.id]) }}</small></span></button></div>
      <div class="door-actions"><button @click="emit('doors', true)">全部開啟</button><span></span><button @click="emit('doors', false)">全部關閉</button></div>
      <div v-if="vehicle.capabilities.trunk" class="switch-row trunk-row"><span class="trunk-label"><AppIcon name="trunk" :size="20" /><span>{{ vehicle.bodyStyle === 'suv' ? '後尾門' : '後車廂' }}<small>{{ partStatus('trunk', state.trunk) }}</small></span></span><button class="toggle" role="switch" :aria-label="vehicle.bodyStyle === 'suv' ? '後尾門' : '後車廂'" :aria-checked="state.trunk" @click="emit('trunk')"><span></span></button></div>
    </section>
    <section v-if="vehicle.capabilities.steering" class="control-section">
      <div class="section-title"><AppIcon name="wheel" :size="19" /><h3>前輪轉向</h3><output class="angle-value">{{ state.steeringAngle > 0 ? '+' : '' }}{{ state.steeringAngle }}<span>°</span></output></div>
      <input class="range-input" type="range" min="-30" max="30" step="1" :value="state.steeringAngle" aria-label="前輪轉向角度" @input="emit('steering', Number(($event.target as HTMLInputElement).value))" />
      <div class="range-legend"><span>左 −30°</span><button @click="emit('steering', 0)">回正</button><span>右 ＋30°</span></div>
    </section>
  </fieldset>
</template>
