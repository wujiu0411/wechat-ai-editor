<template>
  <div class="history-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>生成历史</span>
          <el-tag type="info">共 {{ total }} 条记录</el-tag>
        </div>
      </template>

      <el-table :data="items" stripe style="width:100%" @row-click="resetSyncAndShow">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="content_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.content_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="article_title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="公众号" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.sync_count > 0" type="success" size="small">已同步 {{ row.sync_count }}次</el-tag>
            <el-tag v-else type="info" size="small">未同步</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="resetSyncAndShow(row)">查看HTML</el-button>
            <el-button size="small" type="danger" @click.stop="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top:16px;justify-content:center"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" title="文章详情" width="70%" destroy-on-close>
      <div v-if="currentItem">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="标题">{{ currentItem.article_title }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentItem.content_type }}</el-descriptions-item>
        </el-descriptions>
        <el-tabs>
          <el-tab-pane label="HTML预览">
            <div class="dialog-preview">
              <iframe ref="dialogFrame" class="preview-iframe" sandbox="allow-same-origin"></iframe>
            </div>
          </el-tab-pane>
          <el-tab-pane label="HTML代码">
            <pre class="code-block">{{ currentItem.html_output }}</pre>
          </el-tab-pane>
          <el-tab-pane label="Markdown">
            <pre class="code-block">{{ currentItem.article_content_markdown }}</pre>
          </el-tab-pane>
        </el-tabs>

        <div v-if="parsedImages.length" style="margin-top:12px">
          <p style="font-size:13px;color:#666;margin-bottom:8px">文章配图 ({{ parsedImages.length }}张) — 拖拽排序 / 点击替换</p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <div v-for="(img, idx) in parsedImages" :key="img.source + idx"
                 class="history-image-slot"
                 :class="{ dragging: dragIndex === idx }"
                 draggable="true"
                 @dragstart="onDragStart($event, idx)"
                 @dragover.prevent="onDragOver($event, idx)"
                 @drop.prevent="onDrop($event, idx)"
                 @dragend="onDragEnd">
              <div class="drag-handle" title="拖拽排序">⠿</div>
              <img v-if="img.source && !img.source.startsWith('[缺失')"
                   :src="img.source"
                   style="width:100px;height:75px;object-fit:cover;border-radius:4px"
                   @click="openImagePicker(idx)"
                   title="点击替换" />
              <div v-else @click="openImagePicker(idx)" style="width:100px;height:75px;border:2px dashed #ddd;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#999;font-size:11px">缺失</div>
              <p style="font-size:10px;color:#999;margin:2px 0 0;text-align:center;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ img.filename || img.alt_text || '-' }}</p>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="copyCurrentHtml">复制HTML</el-button>
        <el-button type="success" @click="openVisualEditor">可视化编辑</el-button>
        <el-button
          :type="syncStatus === 'synced' ? 'success' : 'warning'"
          :loading="syncStatus === 'syncing'"
          @click="syncToWechat"
        >
          {{ syncStatus === 'synced' ? '已同步' : syncStatus === 'syncing' ? '同步中...' : '同步到公众号' }}
        </el-button>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Image Picker Dialog -->
    <el-dialog v-model="pickerVisible" title="选择替换图片" width="750px" destroy-on-close>
      <el-input v-model="pickerSearch" placeholder="搜索素材" style="margin-bottom:12px" clearable>
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div style="max-height:400px;overflow-y:auto">
        <el-row :gutter="8">
          <el-col v-for="asset in filteredPickerAssets" :key="asset.id" :span="6" style="margin-bottom:8px">
            <div class="picker-item" :class="{ selected: pickerSelected === asset.id }" @click="pickerSelected = asset.id">
              <img v-if="asset.file_type === 'image'" :src="assetUrl(asset.filepath)" style="width:100%;height:100px;object-fit:cover;border-radius:4px" />
              <div v-else style="width:100%;height:100px;background:#f5f5f5;border-radius:4px;display:flex;align-items:center;justify-content:center">
                <el-icon :size="32" color="#ccc"><Document /></el-icon>
              </div>
              <p style="font-size:11px;color:#666;margin-top:2px;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ asset.filename }}</p>
            </div>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button @click="pickerVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmReplaceImage" :disabled="!pickerSelected">确认替换</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { historyApi, wechatApi, assetApi } from '../api'
import { assetUrl, fixHtmlImages } from '../utils/assetUrl.js'

const items = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const dialogVisible = ref(false)
const currentItem = ref(null)
const dialogFrame = ref(null)
const syncStatus = ref('idle')
const saving = ref(false)

// Image picker
const pickerVisible = ref(false)
const pickerSearch = ref('')
const pickerAssets = ref([])
const pickerSelected = ref(null)
const pickerTargetIdx = ref(-1)

const parsedImages = computed(() => {
  if (!currentItem.value) return []
  const imgs = currentItem.value.images
  if (!imgs) return []
  if (Array.isArray(imgs)) return imgs
  if (typeof imgs === 'string') {
    try { return JSON.parse(imgs) } catch { return [] }
  }
  return []
})

const filteredPickerAssets = computed(() => {
  if (!pickerSearch.value) return pickerAssets.value
  const q = pickerSearch.value.toLowerCase()
  return pickerAssets.value.filter(a =>
    a.filename.toLowerCase().includes(q) ||
    (a.keywords || '').toLowerCase().includes(q) ||
    a.category.toLowerCase().includes(q)
  )
})

async function loadHistory() {
  try {
    const { data } = await historyApi.list({
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
    })
    items.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error('加载历史失败')
  }
}

function handlePageChange(page) {
  currentPage.value = page
  loadHistory()
}

async function showDetail(row) {
  try {
    const { data } = await historyApi.get(row.id)
    currentItem.value = data
    dialogVisible.value = true
    await nextTick()
    renderDialogPreview()
  } catch {
    ElMessage.error('加载详情失败')
  }
}

function viewHtml(row) {
  showDetail(row)
}

function renderDialogPreview() {
  if (dialogFrame.value && currentItem.value) {
    const doc = dialogFrame.value.contentDocument
    const html = fixHtmlImages(currentItem.value.html_output)
    doc.open()
    doc.write(`
      <html><head>
        <meta charset="utf-8">
        <style>body{margin:0;padding:0;background:#f5f5f5;display:flex;justify-content:center;}</style>
      </head><body>
        ${html}
      </body></html>
    `)
    doc.close()
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除此记录？', '提示', { type: 'warning' })
    await historyApi.delete(id)
    ElMessage.success('已删除')
    loadHistory()
  } catch {}
}

function openVisualEditor() {
  if (!currentItem.value) return
  sessionStorage.setItem('editor_article', JSON.stringify({
    article_title: currentItem.value.article_title,
    call_to_action: currentItem.value.seo_keywords?.length ? '点击阅读原文了解更多' : '点击阅读原文了解更多',
    html_output: fixHtmlImages(currentItem.value.html_output),
    id: currentItem.value.id,
  }))
  window.open('/editor', '_blank')
}

async function copyCurrentHtml() {
  if (!currentItem.value) return
  try {
    await navigator.clipboard.writeText(currentItem.value.html_output)
    ElMessage.success('HTML已复制到剪贴板')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = currentItem.value.html_output
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制到剪贴板')
  }
}

async function syncToWechat() {
  if (!currentItem.value) return
  syncStatus.value = 'syncing'
  try {
    await wechatApi.sync({
      title: currentItem.value.article_title,
      html_output: currentItem.value.html_output,
      history_id: currentItem.value.id,
    })
    syncStatus.value = 'synced'
    if (currentItem.value.sync_count !== undefined) {
      currentItem.value.sync_count = (currentItem.value.sync_count || 0) + 1
    }
    ElMessage.success('已同步到公众号草稿箱')
  } catch (err) {
    syncStatus.value = 'idle'
    ElMessage.error(err.response?.data?.detail || '同步失败，请确认公众号已配置')
  }
}

function resetSyncAndShow(row) {
  syncStatus.value = 'idle'
  showDetail(row)
}

// Drag-and-drop image reordering
const dragIndex = ref(-1)

function onDragStart(e, idx) {
  dragIndex.value = idx
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e, idx) {
  if (dragIndex.value === idx) return
  e.dataTransfer.dropEffect = 'move'
}

function onDrop(e, targetIdx) {
  const sourceIdx = dragIndex.value
  if (sourceIdx < 0 || sourceIdx === targetIdx) return

  const imgs = parsedImages.value
  ;[imgs[sourceIdx], imgs[targetIdx]] = [imgs[targetIdx], imgs[sourceIdx]]

  // Swap in HTML
  const srcImgs = currentItem.value.html_output.match(/<img[^>]*>/g) || []
  if (srcImgs[sourceIdx] && srcImgs[targetIdx]) {
    currentItem.value.html_output = currentItem.value.html_output
      .replace(srcImgs[sourceIdx], '__SWAP__')
      .replace(srcImgs[targetIdx], srcImgs[sourceIdx])
      .replace('__SWAP__', srcImgs[targetIdx])
  }

  // Save to backend
  historyApi.update(currentItem.value.id, { html_output: currentItem.value.html_output }).catch(() => {})

  nextTick(() => renderDialogPreview())
}

function onDragEnd() {
  dragIndex.value = -1
}

async function openImagePicker(idx) {
  pickerTargetIdx.value = idx
  pickerSelected.value = null
  pickerSearch.value = ''
  pickerVisible.value = true
  try {
    const { data } = await assetApi.list({})
    pickerAssets.value = (data.items || []).filter(a => a.file_type === 'image')
  } catch {
    pickerAssets.value = []
  }
}

async function confirmReplaceImage() {
  if (pickerSelected.value === null || pickerTargetIdx.value < 0) return
  const asset = pickerAssets.value.find(a => a.id === pickerSelected.value)
  if (!asset) return

  const imgs = parsedImages.value
  if (!imgs[pickerTargetIdx.value]) return

  const oldSrc = imgs[pickerTargetIdx.value].source
  const newSrc = assetUrl(asset.filepath)

  imgs[pickerTargetIdx.value].source = newSrc
  imgs[pickerTargetIdx.value].filename = asset.filename
  imgs[pickerTargetIdx.value].alt_text = asset.filename

  // Update in HTML
  if (oldSrc) {
    currentItem.value.html_output = currentItem.value.html_output.replace(oldSrc, newSrc)
  }

  // Save to backend
  saving.value = true
  try {
    await historyApi.update(currentItem.value.id, {
      html_output: currentItem.value.html_output,
    })
    ElMessage.success('配图已替换')
  } catch (err) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }

  pickerVisible.value = false
  await nextTick()
  renderDialogPreview()
}

onMounted(loadHistory)
</script>

<style scoped>
.history-page {
  max-width: 1400px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dialog-preview {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: center;
}
.preview-iframe {
  width: 375px;
  min-height: 600px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fff;
}
.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 6px;
  font-size: 13px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.picker-item {
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 6px;
  padding: 4px;
  transition: border-color 0.15s;
}
.picker-item:hover {
  border-color: #0066CC;
}
.picker-item.selected {
  border-color: #0066CC;
  background: #F0F7FF;
}
.history-image-slot {
  cursor: grab;
  position: relative;
  padding: 4px;
  border: 2px solid transparent;
  border-radius: 6px;
  transition: opacity 0.15s;
}
.history-image-slot:hover {
  border-color: #e0e0e0;
}
.history-image-slot.dragging {
  opacity: 0.4;
  border-color: #0066CC;
}
.drag-handle {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 18px;
  height: 18px;
  background: rgba(0,0,0,0.4);
  color: #fff;
  border-radius: 3px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  z-index: 1;
}
</style>
