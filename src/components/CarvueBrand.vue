<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'
</script>

<template>
  <RouterLink class="identity" to="/vehicles" aria-label="CARVUE 車映 所有車款">
    <AppIcon name="carvue" :size="32" />
    <span class="wordmark">CARVUE<span>.</span></span>
  </RouterLink>
</template>
