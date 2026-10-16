<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import CarvueBrand from '../components/CarvueBrand.vue'
import VehiclePreview from '../components/VehiclePreview.vue'
import { vehicles } from '../data/vehicles'

document.title = '探索車款 · CARVUE 車映'
</script>

<template>
  <div class="collection-shell">
    <header class="site-header"><CarvueBrand /><span class="header-description">每個角度，都值得探索。</span><span class="header-link">互動賞車</span></header>
    <main class="collection-main">
      <div class="collection-intro">
        <div><p class="eyebrow">CARVUE 車款精選</p><h1>找到讓你停下目光的那一款。</h1><p class="collection-description">轉個角度，打開車門。讓每一個細節，自己說話。</p></div>
        <span class="collection-count">{{ String(vehicles.length).padStart(2, '0') }}<span>款車，等你探索</span></span>
      </div>
      <div class="collection-grid">
        <RouterLink v-for="(vehicle, index) in vehicles" :key="vehicle.id" :to="'/vehicles/' + vehicle.id" class="vehicle-card" :data-testid="'select-' + vehicle.id" :aria-label="vehicle.name + ' 開始賞車'">
          <div class="card-image"><VehiclePreview :vehicle="vehicle" :eager="index < 3" /><span class="body-style-badge">{{ vehicle.bodyStyle === 'suv' ? '休旅車' : '四門轎車' }}</span><span class="card-index">{{ String(index + 1).padStart(2, '0') }}</span><span v-if="vehicle.asset.status === 'development'" class="card-development">製作中</span></div>
          <div class="card-content"><p class="brand-name">{{ vehicle.id.toUpperCase() }}</p><h2>{{ vehicle.name }}</h2><p class="vehicle-trim">360° 互動賞車</p><p class="vehicle-tagline">{{ vehicle.tagline }}</p><div class="card-bottom"><span class="card-action">開始賞車<AppIcon name="arrow" :size="18" /></span><span class="paint-swatch" :style="{ background: vehicle.color }" aria-hidden="true"></span></div></div>
        </RouterLink>
      </div>
      <section class="collection-how" aria-label="賞車方式">
        <div><AppIcon name="mouse" :size="24" /><span><strong>換個角度</strong><small>拖曳旋轉，近看車身細節</small></span></div>
        <div><AppIcon name="door" :size="24" /><span><strong>親手探索</strong><small>開啟車門與後廂，看看內部空間</small></span></div>
        <div><AppIcon name="light" :size="24" /><span><strong>看見變化</strong><small>點亮燈光，感受動態細節</small></span></div>
      </section>
    </main>
    <footer class="collection-footer"><span>CARVUE 車映 · 互動賞車</span><span>拖曳探索 · 桌機體驗最佳</span></footer>
  </div>
</template>
