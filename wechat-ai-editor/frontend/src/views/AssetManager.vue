<template>
  <div class="asset-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>素材库管理</span>
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
      </template>

      <el-row :gutter="12">
        <el-col v-for="asset in assets" :key="asset.id" :xs="12" :sm="8" :md="6" :lg="4">
          <el-card class="asset-item" shadow="hover" @click="previewAsset(asset)">
            <div class="asset-thumb">
              <img v-if="asset.file_type === 'image'" :src="`/api/assets/serve/${asset.filepath}`" :alt="asset.filename" />
              <el-icon v-else :size="48" color="#ccc"><Document /></el-icon>
            </div>
            <div class="asset-info">
              <p class="asset-name" :title="asset.filename">{{ asset.filename }}</p>
              <el-tag size="small" type="info">{{ asset.category }}</el-tag>
              <el-tag v-if="asset.sub_category" size="small" style="margin-left:4px">{{ asset.sub_category }}</el-tag>
            </div>
            <div class="asset-actions" @click.stop>
              <el-button size="small" @click="editAsset(asset)"><el-icon><Edit /></el-icon></el-button>
              <el-button size="small" type="danger" @click="handleDelete(asset)"><el-icon><Delete /></el-icon></el-button>
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
        accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.pdf"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div>支持 jpg/png/gif/bmp/webp/mp4/pdf，图片不超过2MB</div>
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

    <!-- Edit Dialog -->
    <el-dialog v-model="editVisible" title="编辑素材" width="450px" destroy-on-close>
      <el-form v-if="editForm" :model="editForm" label-width="80px">
        <el-form-item label="文件名">
          <el-input :model-value="editForm.filename" disabled />
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
            <el-option label="视频" value="视频" />
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
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog v-model="previewVisible" title="素材预览" width="700px" destroy-on-close>
      <div v-if="previewAssetData" class="preview-body">
        <img v-if="previewAssetData.file_type === 'image'" :src="`/static/uploads/${previewAssetData.filepath}`" style="max-width:100%;max-height:60vh;display:block;margin:0 auto" />
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
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

const editVisible = ref(false)
const saving = ref(false)
const editForm = ref(null)

const previewVisible = ref(false)
const previewAssetData = ref(null)

async function loadAssets() {
  try {
    const { data } = await assetApi.list({
      query: searchQuery.value,
      category: selectedCategory.value,
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

function editAsset(asset) {
  editForm.value = { ...asset }
  editVisible.value = true
}

async function handleEditSave() {
  saving.value = true
  try {
    await assetApi.update(editForm.value.id, {
      category: editForm.value.category,
      sub_category: editForm.value.sub_category || '',
      keywords: editForm.value.keywords || '',
    })
    ElMessage.success('更新成功')
    editVisible.value = false
    await loadAssets()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(asset) {
  try {
    await ElMessageBox.confirm(`确定删除素材"${asset.filename}"？`, '提示', { type: 'warning' })
    await assetApi.delete(asset.id)
    ElMessage.success('已删除')
    await loadAssets()
    await loadCategories()
  } catch {}
}

function previewAsset(asset) {
  previewAssetData.value = asset
  previewVisible.value = true
}

onMounted(() => {
  loadAssets()
  loadCategories()
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
.asset-item:hover .asset-actions {
  opacity: 1;
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
.asset-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s;
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
.preview-body {
  text-align: center;
}
</style>
