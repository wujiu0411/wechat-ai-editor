import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/create',
  },
  {
    path: '/create',
    name: 'CreateArticle',
    component: () => import('./views/CreateArticle.vue'),
  },
  {
    path: '/assets',
    name: 'AssetManager',
    component: () => import('./views/AssetManager.vue'),
  },
  {
    path: '/history',
    name: 'HistoryList',
    component: () => import('./views/HistoryList.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
