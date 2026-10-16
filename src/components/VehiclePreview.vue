<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { assetUrl } from '../data/vehicles'
import type { VehicleDefinition } from '../types/vehicle'

const props = defineProps<{ vehicle: VehicleDefinition; eager?: boolean }>()
const failed = ref(false)
const source = computed(() => assetUrl(props.vehicle.asset.posterUrl))
watch(source, () => { failed.value = false })
</script>

<template>
  <div class="vehicle-preview" :style="{ '--paint-color': vehicle.color }">
    <img v-if="!failed" :src="source" :alt="vehicle.name + ' 外觀預覽'" :loading="eager ? 'eager' : 'lazy'" decoding="async" @error="failed = true" />
    <div v-else class="preview-placeholder"><AppIcon name="car" :size="72" /><span>{{ vehicle.name }}</span></div>
  </div>
</template>
