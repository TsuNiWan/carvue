<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number }>(), { size: 20 })
const paths: Record<string, string> = {
  carvue: 'M19 5a9 9 0 1 0 0 14M9 9l3 7 3-7',
  reset: 'M3 11a9 9 0 1 1 2.6 7.4M3 4v7h7',
  arrow: 'M5 12h14m-5-5 5 5-5 5',
  chevron: 'm9 5 7 7-7 7',
  light: 'M13 5c4 0 6 3 6 7s-2 7-6 7V5ZM3 6l6 2M2 12h7M3 18l6-2',
  wheel: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 10h18M8 10l3 11m5-11-3 11M10 14h4',
  door: 'M5 21V9l6-6h8v18H5Zm0-10h14m-4 4h2M11 3v8',
  trunk: 'M4 14h16v7H4v-7Zm1-3 2-8h10l2 8M8 17h8',
  car: 'm4 9 2-5h12l2 5M3 10h18v8H3v-8Zm1 8v3m16-3v3M6 13h2m8 0h2',
  radar: 'M12 12 19 5M5.6 18.4a9 9 0 1 1 12.8 0M8.5 15.5a5 5 0 1 1 7 0M11 19h2m-1-8v2',
  camera: 'M3 7h4l2-3h6l2 3h4v14H3V7Zm13 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  lidar: 'M12 3v18M3 12h18M5 5l14 14M5 19 19 5M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  waves: 'M5 9a5 5 0 0 1 0 6M9 6a9 9 0 0 1 0 12M13 3a13 13 0 0 1 0 18',
  play: 'm8 4 12 8-12 8V4Z',
  pause: 'M8 4v16M16 4v16',
  info: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 11v6m0-10v.5',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  shield: 'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6l-9-4Zm-4 10 3 3 5-6',
  warning: 'm12 3 10 18H2L12 3Zm0 6v5m0 3v1',
  person: 'M14.5 4a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM12 8v7m-6-4 6-3 6 3m-6 4-4 7m4-7 4 7',
  mouse: 'M12 2c-4 0-6 3-6 6v8a6 6 0 0 0 12 0V8c0-3-2-6-6-6Zm0 0v7',
  expand: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5',
  check: 'm5 12 4 4L19 6',
}
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="paths[name] || paths.car" />
  </svg>
</template>
