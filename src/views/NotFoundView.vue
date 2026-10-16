<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import CarvueBrand from '../components/CarvueBrand.vue'

document.title = '找不到這款車 · CARVUE'
</script>

<template>
  <div class="collection-shell">
    <header class="site-header"><CarvueBrand /><span class="header-description">每個角度，都值得探索。</span></header>
    <main class="not-found">
      <span class="not-found-symbol"><AppIcon name="car" :size="44" /></span>
      <p class="eyebrow">重新出發</p>
      <h1>找不到這款車</h1>
      <p>這個連結目前沒有對應的車款，回到總覽繼續探索。</p>
      <RouterLink class="primary-link" to="/vehicles">所有車款<AppIcon name="arrow" :size="18" /></RouterLink>
    </main>
  </div>
</template>
