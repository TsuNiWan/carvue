import { createRouter, createWebHashHistory } from 'vue-router'
import VehicleCollectionView from './views/VehicleCollectionView.vue'
import NotFoundView from './views/NotFoundView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/vehicles' },
    { path: '/vehicles', component: VehicleCollectionView },
    { path: '/vehicles/:id', component: () => import('./views/VehicleDetailView.vue') },
    { path: '/:pathMatch(.*)*', component: NotFoundView },
  ],
  scrollBehavior: () => ({ top: 0, left: 0 }),
})
