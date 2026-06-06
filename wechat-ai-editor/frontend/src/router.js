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
    path: '/suggestions',
    name: 'SuggestionsPage',
    component: () => import('./views/SuggestionsPage.vue'),
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
  {
    path: '/editor',
    name: 'ArticleEditor',
    component: () => import('./views/ArticleEditor.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
