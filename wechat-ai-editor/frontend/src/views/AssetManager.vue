<template>
  <div class="asset-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>素材库管理</span>
          <div v-if="descProgress.total && !descProgress.done" style="margin-right:12px">
            <el-progress
              :percentage="Math.round(descProgress.current / descProgress.total * 100)"
              :stroke-width="6"
              style="width:180px"
              :status="descProgress.done ? 'success' : ''"
            >
              <span style="font-size:11px">AI理解图片 {{ descProgress.current }}/{{ descProgress.total }}</span>
            </el-progress>
          </div>
          <div>
            <el-input v-model="searchQuery" placeholder="搜索素材" style="width:240px;margin-right:8px" clearable @keyup.enter="loadAssets">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select v-model="selectedCategory" placeholder="分类筛选" clearable style="width:140px;margin-right:8px" @change="loadAssets">
              <el-option v-for="cat in categories" :key="cat.name" :label="`${cat.name} (${cat.count})`" :value="cat.name" />
            </el-select>
            <el-button type="primary" @click="uploadVisible = true"><el-icon><Upload /></el-icon> 上传素材</el-button>
            <el-button @click="refreshAssets"><el-icon><Refresh /></el-icon> 刷新索引</el-button>
          </div>
        </div>
        <div v-if="selectedIds.length" class="batch-bar">
          <el-checkbox v-model="allSelected" :indeterminate="indeterminate" @change="toggleAll">全选</el-checkbox>
          <span style="color:#666;font-size:13px">已选 {{ selectedIds.length }} 项</span>
          <el-button type="danger" size="small" @click="batchDelete">批量删除</el-button>
        </div>
        <div v-else style="display:flex;align-items:center;gap:12px;margin-top:4px">
          <el-checkbox v-model="selectMode" size="small">多选模式</el-checkbox>
        </div>
      </template>

      <el-row :gutter="12">
        <el-col v-for="asset in assets" :key="asset.id" :xs="12" :sm="8" :md="6" :lg="4">
          <el-card class="asset-item" :class="{ selected: selectedIds.includes(asset.id) }" shadow="hover" @click="handleAssetClick(asset)">
            <div v-if="selectMode || selectedIds.length" class="asset-check" @click.stop>
              <el-checkbox :model-value="selectedIds.includes(asset.id)" @change="toggleSelect(asset.id)" />
            </div>
            <div class="asset-thumb">
              <img v-if="asset.file_type === 'image'" :src="`/api/assets/serve/${asset.filepath}`" :alt="asset.filename" />
              <el-icon v-else :size="48" color="#ccc"><Document /></el-icon>
            </div>
            <div class="asset-info">
              <p class="asset-name" :title="asset.filename">{{ asset.filename }}</p>
              <el-tag size="small" type="info">{{ asset.category }}</el-tag>
              <el-tag v-if="asset.sub_category" size="small" style="margin-left:4px">{{ asset.sub_category }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!assets.length" description="暂无素材" />
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadVisible" title="上传素材" width="500px" destroy-on-close>
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".jpg,.jpeg,.png,.gif,.bmp,.webp"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div>支持 jpg/png/gif/bmp/webp，图片不超过2MB</div>
        </template>
      </el-upload>
      <el-form :model="uploadForm" label-width="80px" style="margin-top:16px">
        <el-form-item label="素材分类">
          <el-select v-model="uploadForm.category" style="width:100%">
            <el-option label="产品图" value="产品图" />
            <el-option label="logo" value="logo" />
            <el-option label="海报" value="海报" />
            <el-option label="单页" value="单页" />
            <el-option label="科普图" value="科普图" />
            <el-option label="易拉宝" value="易拉宝" />
            <el-option label="解决方案" value="解决方案" />
            <el-option label="视频" value="视频" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="子分类">
          <el-input v-model="uploadForm.sub_category" placeholder="如：K2/H7" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="uploadForm.keywords" placeholder="检索关键词，逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">上传</el-button>
      </template>
    </el-dialog>

    <!-- Preview & Edit & Crop Dialog -->
    <el-dialog v-model="previewVisible" :title="cropMode ? '裁剪长图' : editMode ? '编辑素材' : '素材预览'" :width="cropMode ? '950px' : '700px'" destroy-on-close @close="editMode = false; cropMode = false">
      <div v-if="previewAssetData">
        <!-- Normal preview mode -->
        <template v-if="!editMode && !cropMode">
          <div class="preview-body" style="max-height:60vh;overflow-y:auto">
            <img v-if="previewAssetData.file_type === 'image'" :src="`/api/assets/serve/${previewAssetData.filepath}`" style="max-width:100%;display:block;margin:0 auto" />
            <div v-else style="text-align:center;padding:60px">
              <el-icon :size="80" color="#ccc"><Document /></el-icon>
              <p style="margin-top:12px;color:#666">{{ previewAssetData.filename }}</p>
            </div>
            <el-descriptions :column="2" border size="small" style="margin-top:16px">
              <el-descriptions-item label="文件名">{{ previewAssetData.filename }}</el-descriptions-item>
              <el-descriptions-item label="分类">{{ previewAssetData.category }}</el-descriptions-item>
              <el-descriptions-item label="子分类">{{ previewAssetData.sub_category || '-' }}</el-descriptions-item>
              <el-descriptions-item label="关键词">{{ previewAssetData.keywords || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
        <!-- Edit mode -->
        <template v-else-if="editMode">
          <el-form :model="editForm" label-width="80px">
            <el-form-item label="文件名">
              <el-input :model-value="previewAssetData.filename" disabled />
            </el-form-item>
            <el-form-item label="素材分类">
              <el-select v-model="editForm.category" style="width:100%">
                <el-option label="产品图" value="产品图" />
                <el-option label="logo" value="logo" />
                <el-option label="海报" value="海报" />
                <el-option label="单页" value="单页" />
                <el-option label="科普图" value="科普图" />
                <el-option label="易拉宝" value="易拉宝" />
                <el-option label="解决方案" value="解决方案" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="子分类">
              <el-input v-model="editForm.sub_category" placeholder="如：K2/H7" />
            </el-form-item>
            <el-form-item label="关键词">
              <el-input v-model="editForm.keywords" placeholder="检索关键词，逗号分隔" />
            </el-form-item>
          </el-form>
        </template>
        <!-- Crop mode -->
        <template v-else>
          <div style="display:flex;gap:16px">
            <!-- Left: Full image with split lines -->
            <div style="flex:1;text-align:center">
              <div class="crop-stage" ref="cropStageEl" @click="onCropStageClick">
                <img :src="`/api/assets/serve/${previewAssetData.filepath}`"
                     style="max-width:100%;display:block"
                     @load="onCropImgLoad" />
                <div v-for="(l, i) in cropLines" :key="'l'+i"
                     class="crop-line" :style="{ top: l.pct + '%' }">
                  <span>{{ l.px }}px</span>
                </div>
              </div>
              <p style="font-size:11px;color:#999;margin-top:4px">
                {{ imgW }}×{{ imgH }}px | 点击图片添加分割线
              </p>
            </div>

            <!-- Right: Controls -->
            <div style="width:280px;flex-shrink:0;">
              <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center">
                <span style="font-size:13px;font-weight:600">{{ cropLines.length + 1 }}段</span>
                <el-button size="small" @click="undoLastLine" :disabled="!cropLines.length">撤销</el-button>
                <el-button size="small" @click="clearAllLines" :disabled="!cropLines.length">清除</el-button>
              </div>
              <p style="font-size:11px;color:#666;margin-bottom:10px">
                点击图片上要裁剪的位置来添加分割线，或手动输入像素位置:
              </p>
              <div v-for="(l, i) in cropLines" :key="i" style="margin-bottom:6px;display:flex;align-items:center;gap:6px">
                <span style="font-size:11px;width:40px">线{{ i+1 }}:</span>
                <input type="number" :value="l.px" @input="e => setLinePx(i, parseInt(e.target.value) || 0)"
                       min="0" :max="imgH || 999999" step="50"
                       style="width:90px;padding:3px 6px;border:1px solid #ddd;border-radius:4px;font-size:12px" />
                <span style="font-size:10px;color:#999">px</span>
                <button @click="removeLine(i)" style="border:none;background:none;color:red;cursor:pointer;font-size:14px">×</button>
              </div>
              <div style="margin-top:10px;padding:8px;background:#f5f5f5;border-radius:6px;max-height:250px;overflow-y:auto">
                <p style="font-size:11px;color:#666;margin-bottom:6px">分段预览:</p>
                <div v-for="(seg, i) in cropSegments" :key="i" style="display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:11px">
                  <span style="width:20px;color:#0066CC;font-weight:600">{{ i+1 }}</span>
                  <span style="flex:1">Y{{ seg.start }}→{{ seg.end }}</span>
                  <span>{{ seg.height }}px</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
      <template #footer>
        <template v-if="!editMode && !cropMode">
          <el-button type="primary" @click="enterEditMode">编辑</el-button>
          <el-button type="warning" @click="enterCropMode">处理长图</el-button>
          <el-button type="danger" @click="handleDelete">删除</el-button>
          <el-button @click="previewVisible = false">关闭</el-button>
        </template>
        <template v-else-if="editMode">
          <el-button type="primary" @click="handleEditSave" :loading="saving">保存</el-button>
          <el-button @click="editMode = false">取消</el-button>
        </template>
        <template v-else>
          <el-button type="primary" @click="doSplitLong" :loading="splitting">确认裁剪</el-button>
          <el-button @click="cropMode = false">返回</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assetApi, articleApi } from '../api'

const assets = ref([])
const categories = ref([])
const searchQuery = ref('')
const selectedCategory = ref('')

const uploadVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const uploadForm = ref({ category: '产品图', sub_category: '', keywords: '' })
const uploadFile = ref(null)

const previewVisible = ref(false)
const previewAssetData = ref(null)
const editMode = ref(false)
const cropMode = ref(false)
const selectMode = ref(false)
const selectedIds = ref([])

const allSelected = computed(() => assets.value.length > 0 && selectedIds.value.length === assets.value.length)
const indeterminate = computed(() => selectedIds.value.length > 0 && selectedIds.value.length < assets.value.length)

function handleAssetClick(asset) {
  if (selectMode.value || selectedIds.value.length > 0) {
    toggleSelect(asset.id)
  } else {
    previewAsset(asset)
  }
}

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function toggleAll(val) {
  selectedIds.value = val ? assets.value.map(a => a.id) : []
}

async function batchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个素材？`, '批量删除', { type: 'warning' })
    for (const id of selectedIds.value) {
      await assetApi.delete(id)
    }
    ElMessage.success(`已删除 ${selectedIds.value.length} 个素材`)
    selectedIds.value = []
    selectMode.value = false
    await loadAssets()
    await loadCategories()
  } catch {}
}
const editForm = ref({})
const saving = ref(false)
const splitting = ref(false)

// Image crop - click to position
const imgW = ref(0)
const imgH = ref(0)
const cropLines = ref([]) // [{px: number, pct: number}], sorted by px
const cropStageEl = ref(null)

const cropSegments = computed(() => {
  const points = [0, ...cropLines.value.map(l => l.px).sort((a,b)=>a-b), imgH.value]
  const segs = []
  for (let i = 0; i < points.length - 1; i++) {
    if (points[i] >= imgH.value) break
    segs.push({ start: points[i], end: Math.min(points[i+1], imgH.value), height: Math.min(points[i+1], imgH.value) - points[i] })
  }
  return segs
})

function onCropImgLoad(e) {
  imgW.value = e.target.naturalWidth
  imgH.value = e.target.naturalHeight
}
function onCropStageClick(e) {
  if (!imgH.value) return
  const rect = cropStageEl.value.getBoundingClientRect()
  const imgEl = cropStageEl.value.querySelector('img')
  const imgRect = imgEl.getBoundingClientRect()
  const clickY = e.clientY - imgRect.top
  const scaleY = imgH.value / imgRect.height
  const px = Math.round(clickY * scaleY)
  if (px < 100 || px > imgH.value - 100) return
  cropLines.value = [...cropLines.value, { px, pct: Math.round(px / imgH.value * 100) }].sort((a,b) => a.px - b.px)
}
function setLinePx(idx, px) {
  cropLines.value = cropLines.value.map((l, i) => i === idx ? { px: Math.max(0, Math.min(px, imgH.value)), pct: Math.round(Math.max(0, Math.min(px, imgH.value)) / imgH.value * 100) } : l).sort((a,b) => a.px - b.px)
}
function removeLine(idx) { cropLines.value = cropLines.value.filter((_, i) => i !== idx) }
function undoLastLine() { cropLines.value = cropLines.value.slice(0, -1) }
function clearAllLines() { cropLines.value = [] }
function enterCropMode() { cropMode.value = true; imgW.value = 0; imgH.value = 0; cropLines.value = [] }

async function doSplitLong() {
  if (!previewAssetData.value || !imgH.value) return
  splitting.value = true
  try {
    const points = [0, ...cropLines.value.map(l => l.px).sort((a,b)=>a-b), imgH.value]
    const heights = []
    for (let i = 0; i < points.length - 1; i++) {
      const h = Math.min(points[i+1], imgH.value) - points[i]
      if (h > 0) heights.push(h)
    }
    const { data } = await assetApi.splitLong(previewAssetData.value.id, { seg_heights: heights })
    ElMessage.success(data.message)
    cropMode.value = false
    previewVisible.value = false
    await loadAssets()
    await loadCategories()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '裁剪失败')
  } finally { splitting.value = false }
}

async function loadAssets() {
  try {
    const { data } = await assetApi.list({
      query: searchQuery.value,
      category: selectedCategory.value,
      file_type: 'image',
    })
    assets.value = data.items
  } catch {
    ElMessage.error('加载素材失败')
  }
}

async function loadCategories() {
  try {
    const { data } = await assetApi.categories()
    categories.value = data
  } catch {}
}

async function refreshAssets() {
  try {
    await articleApi.refreshAssets()
    await loadAssets()
    await loadCategories()
    ElMessage.success('素材索引已刷新')
  } catch {
    ElMessage.error('刷新失败')
  }
}

function handleFileChange(file) {
  uploadFile.value = file.raw
}

async function handleUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    await assetApi.upload(uploadFile.value, uploadForm.value)
    ElMessage.success('上传成功')
    uploadVisible.value = false
    uploadFile.value = null
    uploadForm.value = { category: '产品图', sub_category: '', keywords: '' }
    await loadAssets()
    await loadCategories()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

function previewAsset(asset) {
  previewAssetData.value = asset
  editMode.value = false
  previewVisible.value = true
}

function enterEditMode() {
  editForm.value = {
    category: previewAssetData.value.category,
    sub_category: previewAssetData.value.sub_category || '',
    keywords: previewAssetData.value.keywords || '',
  }
  editMode.value = true
}

async function handleEditSave() {
  saving.value = true
  try {
    await assetApi.update(previewAssetData.value.id, {
      category: editForm.value.category,
      sub_category: editForm.value.sub_category || '',
      keywords: editForm.value.keywords || '',
    })
    previewAssetData.value.category = editForm.value.category
    previewAssetData.value.sub_category = editForm.value.sub_category
    previewAssetData.value.keywords = editForm.value.keywords
    ElMessage.success('更新成功')
    editMode.value = false
    await loadAssets()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(`确定删除素材"${previewAssetData.value.filename}"？`, '提示', { type: 'warning' })
    await assetApi.delete(previewAssetData.value.id)
    ElMessage.success('已删除')
    previewVisible.value = false
    await loadAssets()
    await loadCategories()
  } catch {}
}

const descProgress = ref({ current: 0, total: 0, done: false })
let descPollTimer = null

async function checkDescProgress() {
  try {
    const { data } = await assetApi.descriptionStatus()
    descProgress.value = data
    if (data.done && descPollTimer) {
      clearInterval(descPollTimer)
      descPollTimer = null
    }
  } catch {}
}

onMounted(() => {
  loadAssets()
  loadCategories()
  checkDescProgress()
  descPollTimer = setInterval(checkDescProgress, 5000)
})
</script>

<style scoped>
.asset-page {
  max-width: 1400px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.asset-item {
  margin-bottom: 12px;
  cursor: pointer;
  position: relative;
}
.asset-item.selected {
  border: 2px solid #0066CC;
  background: #F0F7FF;
}
.asset-check {
  position: absolute; top: 6px; left: 6px; z-index: 2;
  background: rgba(255,255,255,0.9); border-radius: 4px; padding: 2px;
}
.batch-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 12px; margin-top: 8px;
  background: #F0F7FF; border-radius: 6px; border: 1px solid #D0E3F7;
}
.asset-thumb {
  width: 100%;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
.asset-thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.asset-info {
  text-align: center;
}
.asset-name {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-area {
  width: 100%;
}
.upload-icon {
  font-size: 48px;
  color: #0066CC;
}
.upload-text {
  margin-top: 8px;
  color: #999;
}
.preview-body { text-align: center; }

/* Crop tool */
.crop-stage { max-height:55vh; overflow-y:auto; position:relative; display:inline-block; border:1px solid #eee; border-radius:8px; cursor:crosshair; }
.crop-line { position:absolute; left:0; right:0; height:3px; background:#FF2E63; z-index:5; transform:translateY(-1.5px); pointer-events:none; }
.crop-line span { position:absolute; right:4px; top:-18px; background:#FF2E63; color:#fff; font-size:9px; padding:1px 5px; border-radius:2px; white-space:nowrap; }
</style>
