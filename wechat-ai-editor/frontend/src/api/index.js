import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api'

const api = axios.create({
  baseURL,
  timeout: 180000,
})

export const articleApi = {
  generate(data) {
    return api.post('/article/generate-v2', data)
  },
  generateFromImages(data) {
    return api.post('/article/generate-from-images', data)
  },
  reformat(data) {
    return api.post('/article/reformat', data)
  },
  refreshAssets() {
    return api.post('/article/refresh-assets')
  },
  suggestions(params = {}) {
    return api.get('/article/suggestions', { params })
  },
  batchGenerate(data) {
    return api.post('/article/batch-generate', data)
  },
  generateFromSuggestion(data) {
    return api.post('/article/generate-from-suggestion', data)
  },
}

export const assetApi = {
  list(params = {}) {
    return api.get('/assets/list', { params: { ...params, file_type: params.file_type || 'image' } })
  },
  categories() {
    return api.get('/assets/categories')
  },
  descriptionStatus() {
    return api.get('/assets/description-status')
  },
  upload(file, { category, sub_category, keywords }) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('category', category)
    formData.append('sub_category', sub_category)
    formData.append('keywords', keywords)
    return api.post('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  update(id, data) {
    const formData = new FormData()
    formData.append('category', data.category)
    formData.append('sub_category', data.sub_category)
    formData.append('keywords', data.keywords)
    return api.put(`/assets/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete(id) {
    return api.delete(`/assets/${id}`)
  },
  splitLong(id, data = {}) {
    return api.post(`/assets/${id}/split-long`, data)
  },
}

export const historyApi = {
  list(params) {
    return api.get('/history/list', { params })
  },
  get(id) {
    return api.get(`/history/${id}`)
  },
  update(id, data) {
    return api.put(`/history/${id}`, data)
  },
  delete(id) {
    return api.delete(`/history/${id}`)
  },
}

export const templateApi = {
  list() {
    return api.get('/templates/list')
  },
  get(id) {
    return api.get(`/templates/${id}`)
  },
}

export const wechatApi = {
  status() {
    return api.get('/wechat/status')
  },
  sync(data) {
    return api.post('/wechat/sync', data)
  },
  drafts(params) {
    return api.get('/wechat/drafts', { params })
  },
}

export const healthApi = {
  check() {
    return api.get('/health')
  },
}

export default api
