<template>
  <div class="editor-page">
    <div class="editor-toolbar">
      <el-button @click="goBack" text><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <span style="font-weight:600;font-size:15px">{{ articleTitle }}</span>
      <div>
        <el-button @click="saveAndPreview">预览</el-button>
        <el-button type="primary" @click="saveToHistory" :loading="saving">保存到历史记录</el-button>
      </div>
    </div>

    <el-row :gutter="20" style="margin-top:16px">
      <!-- Rendered block list -->
      <el-col :span="14">
        <div class="editor-stage">
          <div class="stage-title">
            <h1 style="font-size:22px;font-weight:700;color:#0066CC;text-align:center;margin:0 0 8px;line-height:1.4;">{{ articleTitle }}</h1>
            <div style="width:60px;height:3px;background:#0066CC;margin:0 auto 20px;border-radius:2px;"></div>
          </div>

          <div class="block-list" v-if="blocks.length">
            <div
              v-for="(block, idx) in blocks"
              :key="block.id"
              class="editor-block"
              :class="{ dragging: dragIdx === idx, 'drag-over': dragOverIdx === idx, editing: editingIdx === idx }"
              draggable="true"
              @dragstart="onDragStart($event, idx)"
              @dragover.prevent="onDragOver($event, idx)"
              @drop.prevent="onDrop($event, idx)"
              @dragend="onDragEnd"
            >
              <div class="block-handle" title="拖拽排序">
                <span>⠿</span>
                <span class="block-num">{{ idx + 1 }}</span>
              </div>

              <!-- Rendered text block -->
              <div v-if="block.type === 'text'" class="block-body" @dblclick="startEditBlock(idx)">
                <div v-if="editingIdx !== idx" class="rendered-text" v-html="renderBlockHtml(block)" @dblclick.stop="startEditBlock(idx)"></div>
                <div v-else class="editing-text">
                  <el-input v-model="block.content" type="textarea" :rows="4" @blur="stopEditBlock" @keydown.escape="stopEditBlock" ref="editInput" />
                  <span style="font-size:11px;color:#999">按 Esc 或点击外部退出编辑</span>
                </div>
              </div>

              <!-- Rendered image block -->
              <div v-else-if="block.type === 'image'" class="block-body block-image">
                <img :src="block.src" :alt="block.alt" class="block-img" @click="openImagePickerForBlock(idx)" title="点击替换图片" />
              </div>

              <div class="block-menu">
                <el-dropdown trigger="click" @command="(cmd) => handleBlockCommand(cmd, idx)">
                  <el-button size="small" text><el-icon><MoreFilled /></el-icon></el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit" v-if="block.type === 'text'">编辑文字</el-dropdown-item>
                      <el-dropdown-item command="replace" v-if="block.type === 'image'">替换图片</el-dropdown-item>
                      <el-dropdown-item command="duplicate">复制块</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无内容" />

          <!-- CTA footer preview -->
          <div style="text-align:center;margin-top:20px;padding:16px;background:linear-gradient(135deg,#0066CC 0%,#004C99 100%);border-radius:8px;">
            <p style="color:#fff;font-size:15px;margin:0;font-weight:500;">{{ articleCta }}</p>
          </div>
        </div>
      </el-col>

      <!-- Side preview -->
      <el-col :span="10">
        <div style="position:sticky;top:16px">
          <el-card>
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>手机端预览</span>
                <el-button size="small" @click="copyPreviewHtml">复制HTML</el-button>
              </div>
            </template>
            <div class="phone-preview">
              <iframe ref="editorFrame" class="preview-iframe" sandbox="allow-same-origin"></iframe>
            </div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- Image picker dialog -->
    <el-dialog v-model="pickerVisible" title="替换图片" width="750px" destroy-on-close>
      <el-input v-model="pickerSearch" placeholder="搜索素材" style="margin-bottom:12px" clearable>
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div style="max-height:400px;overflow-y:auto">
        <el-row :gutter="8">
          <el-col v-for="asset in filteredPickerAssets" :key="asset.id" :span="6" style="margin-bottom:8px">
            <div class="picker-item" :class="{ selected: pickerSelected === asset.id }" @click="pickerSelected = asset.id">
              <img v-if="asset.file_type === 'image'" :src="assetUrl(asset.filepath)"
                   style="width:100%;height:100px;object-fit:cover;border-radius:4px" />
              <p style="font-size:11px;color:#666;margin-top:2px;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ asset.filename }}</p>
            </div>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button @click="pickerVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmBlockImageReplace" :disabled="!pickerSelected">确认替换</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetApi, historyApi } from '../api'
import { assetUrl } from '../utils/assetUrl.js'

const router = useRouter()

const articleTitle = ref('')
const articleCta = ref('')
const historyId = ref(null)
const saving = ref(false)
const blocks = ref([])
const dragIdx = ref(-1)
const dragOverIdx = ref(-1)
const editingIdx = ref(-1)
const editInput = ref(null)
const previewHtml = ref('')
const editorFrame = ref(null)
let blockIdCounter = 0

const pickerVisible = ref(false)
const pickerSearch = ref('')
const pickerAssets = ref([])
const pickerSelected = ref(null)
const pickerTargetBlockIdx = ref(-1)
const filteredPickerAssets = computed(() => {
  const q = pickerSearch.value.toLowerCase()
  const assets = pickerAssets.value.filter(a => a.file_type === 'image')
  if (!q) return assets
  return assets.filter(a => a.filename.toLowerCase().includes(q) || (a.keywords || '').toLowerCase().includes(q))
})

onMounted(() => {
  const raw = sessionStorage.getItem('editor_article')
  if (!raw) { ElMessage.error('未找到文章数据'); router.replace('/create'); return }
  try {
    const data = JSON.parse(raw)
    articleTitle.value = data.article_title || '未命名'
    articleCta.value = data.call_to_action || '点击阅读原文了解更多'
    historyId.value = data.history_id || data.id || null
    blocks.value = parseHtmlToBlocks(data.html_output)
    sessionStorage.removeItem('editor_article')
    buildAndRenderPreview()
  } catch {
    ElMessage.error('文章数据损坏'); router.replace('/create')
  }
})

function parseHtmlToBlocks(html) {
  const result = []
  const bodyMatch = html.match(/<section[^>]*>(.*?)<div style="text-align:center;margin-top:30/s)
  const bodyHtml = bodyMatch ? bodyMatch[1] : html
  const parser = new DOMParser()
  const doc = parser.parseFromString(`<div>${bodyHtml}</div>`, 'text/html')
  const container = doc.querySelector('div')

  for (const el of container.children) {
    const tag = el.tagName.toLowerCase()
    if (tag === 'img') {
      result.push({ id: ++blockIdCounter, type: 'image', src: el.getAttribute('src') || '', alt: el.getAttribute('alt') || '' })
    } else if (tag === 'hr') {
      continue
    } else {
      const html = el.outerHTML
      const text = el.textContent.trim()
      if (text) {
        result.push({ id: ++blockIdCounter, type: 'text', tag, content: html, plainText: text })
      }
    }
  }
  return result
}

function renderBlockHtml(block) {
  if (block.type === 'text') return block.content
  return ''
}

function startEditBlock(idx) {
  editingIdx.value = idx
  // Save current HTML, switch to plain text for editing
  const block = blocks.value[idx]
  if (block.content && block.content.includes('<')) {
    // Already has HTML content, extract text
    const div = document.createElement('div')
    div.innerHTML = block.content
    block.content = div.textContent.trim()
  }
  nextTick(() => {
    const inputs = document.querySelectorAll('.editing-text textarea')
    if (inputs.length) inputs[inputs.length - 1].focus()
  })
}

function stopEditBlock() {
  const idx = editingIdx.value
  if (idx >= 0 && blocks.value[idx]) {
    const text = blocks.value[idx].content
    blocks.value[idx].plainText = text
    // Convert back to styled HTML
    const tag = blocks.value[idx].tag
    if (tag === 'h1' || tag === 'h2') {
      blocks.value[idx].content = `<h2 style="font-size:18px;font-weight:700;color:#0066CC;margin:28px 0 12px 0;padding-bottom:8px;border-bottom:2px solid #E6F0FA;">${text}</h2>`
    } else if (tag === 'h3') {
      blocks.value[idx].content = `<h3 style="font-size:16px;font-weight:600;color:#1A1A1A;margin:20px 0 10px 0;padding-left:10px;border-left:3px solid #0066CC;">${text}</h3>`
    } else if (tag === 'blockquote') {
      blocks.value[idx].content = `<blockquote style="margin:16px 0;padding:12px 16px;background:#F0F7FF;border-left:4px solid #0066CC;border-radius:0 6px 6px 0;font-size:14px;color:#555;line-height:1.7;">${text}</blockquote>`
    } else if (tag === 'ul') {
      const items = text.split('\n').filter(Boolean).map(t => t.replace(/^\d+\.\s*/, ''))
      blocks.value[idx].content = `<ul style="margin:10px 0;padding-left:20px;list-style:none;">${items.map(t => `<li style="font-size:15px;color:#333;line-height:1.8;margin:6px 0;padding-left:12px;">• ${t}</li>`).join('')}</ul>`
    } else {
      blocks.value[idx].content = `<p style="font-size:15px;color:#333;line-height:1.85;margin:12px 0;text-align:justify;letter-spacing:0.5px;text-indent:2em;">${text}</p>`
    }
  }
  editingIdx.value = -1
  buildAndRenderPreview()
}

function handleBlockCommand(cmd, idx) {
  if (cmd === 'edit') startEditBlock(idx)
  else if (cmd === 'replace') openImagePickerForBlock(idx)
  else if (cmd === 'duplicate') {
    const b = blocks.value[idx]
    blocks.value.splice(idx + 1, 0, { ...b, id: ++blockIdCounter })
    buildAndRenderPreview()
  }
  else if (cmd === 'delete') { blocks.value.splice(idx, 1); buildAndRenderPreview() }
}

function onDragStart(e, idx) { dragIdx.value = idx; e.dataTransfer.effectAllowed = 'move' }
function onDragOver(e, idx) { dragOverIdx.value = idx; e.dataTransfer.dropEffect = 'move' }
function onDrop(e, targetIdx) {
  const src = dragIdx.value
  if (src < 0 || src === targetIdx) return
  const temp = blocks.value[src]
  blocks.value.splice(src, 1)
  blocks.value.splice(targetIdx > src ? targetIdx - 1 : targetIdx, 0, temp)
  buildAndRenderPreview()
}
function onDragEnd() { dragIdx.value = -1; dragOverIdx.value = -1 }

async function openImagePickerForBlock(idx) {
  pickerTargetBlockIdx.value = idx
  pickerSelected.value = null; pickerSearch.value = ''
  pickerVisible.value = true
  try { const { data } = await assetApi.list({}); pickerAssets.value = data.items || [] }
  catch { pickerAssets.value = [] }
}

function confirmBlockImageReplace() {
  if (pickerSelected.value === null || pickerTargetBlockIdx.value < 0) return
  const asset = pickerAssets.value.find(a => a.id === pickerSelected.value)
  if (!asset) return
  blocks.value[pickerTargetBlockIdx.value].src = assetUrl(asset.filepath)
  blocks.value[pickerTargetBlockIdx.value].alt = asset.filename
  pickerVisible.value = false
  buildAndRenderPreview()
  ElMessage.success('已替换')
}

function buildHtml() {
  const titleHtml = `<div style="text-align:center;margin-bottom:24px;"><h1 style="font-size:22px;font-weight:700;color:#0066CC;margin:0 0 8px 0;line-height:1.4;">${articleTitle.value}</h1><div style="width:60px;height:3px;background:#0066CC;margin:0 auto;border-radius:2px;"></div></div>`

  const bodyParts = blocks.value.map(b => {
    if (b.type === 'image') return `<img src="${b.src}" alt="${b.alt}" style="max-width:100%;height:auto;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.08);display:block;margin:20px auto;" />`
    return b.content
  })

  const ctaHtml = `<div style="text-align:center;margin-top:30px;padding:16px;background:linear-gradient(135deg,#0066CC 0%,#004C99 100%);border-radius:8px;"><p style="color:#fff;font-size:15px;margin:0;font-weight:500;">${articleCta.value}</p></div>`

  return `<section style="max-width:677px;margin:0 auto;padding:20px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:#333;line-height:1.75;letter-spacing:0.5px;">${titleHtml}${bodyParts.join('\n')}${ctaHtml}</section>`
}

function buildAndRenderPreview() {
  previewHtml.value = buildHtml()
  setTimeout(() => {
    if (editorFrame.value) {
      const doc = editorFrame.value.contentDocument || editorFrame.value.contentWindow.document
      doc.open()
      doc.write(`<html><head><meta charset="utf-8"><style>body{margin:0;padding:0;background:#f5f5f5;display:flex;justify-content:center;}</style></head><body>${previewHtml.value}</body></html>`)
      doc.close()
    }
  }, 100)
}

function saveAndPreview() {
  buildAndRenderPreview()
  ElMessage.success('已更新预览并生成HTML')
}

function copyPreviewHtml() {
  previewHtml.value = buildHtml()
  navigator.clipboard.writeText(previewHtml.value).then(
    () => ElMessage.success('HTML已复制'),
    () => ElMessage.error('复制失败')
  )
}

async function saveToHistory() {
  if (!historyId.value) {
    ElMessage.warning('未关联历史记录，请从创建或历史页面进入编辑器')
    return
  }
  saving.value = true
  try {
    previewHtml.value = buildHtml()
    await historyApi.update(historyId.value, {
      article_title: articleTitle.value,
      html_output: previewHtml.value,
    })
    ElMessage.success('已保存到历史记录')
  } catch (err) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    window.close()
    router.replace('/create')
  }
}
</script>

<style scoped>
.editor-page { max-width:1400px; margin:0 auto; }
.editor-toolbar {
  display:flex; justify-content:space-between; align-items:center;
  padding:10px 16px; background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.06);
  position:sticky; top:0; z-index:10;
}

/* Main editing stage */
.editor-stage {
  max-width:677px; margin:0 auto; padding:24px 20px;
  background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.06);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
}

.block-list { display:flex; flex-direction:column; gap:4px; }

.editor-block {
  display:flex; align-items:flex-start; gap:8px;
  padding:8px 8px 8px 4px; border:2px solid transparent; border-radius:8px;
  transition: all 0.15s; position:relative; cursor:default;
}
.editor-block:hover { border-color:#d0d0d0; background:#fafafa; }
.editor-block:hover .block-menu { opacity:1; }
.editor-block.dragging { opacity:0.4; border-color:#0066CC; }
.editor-block.drag-over { border-color:#0066CC; border-style:dashed; background:#F0F7FF; }
.editor-block.editing { border-color:#0066CC; background:#F8FBFF; }

.block-handle {
  width:32px; min-width:32px; display:flex; flex-direction:column;
  align-items:center; gap:2px; cursor:grab; user-select:none;
  padding-top:4px; color:#bbb; font-size:14px;
}
.block-handle:hover { color:#666; }
.block-num { font-size:10px; font-weight:600; color:#ccc; }

.block-body { flex:1; min-width:0; }
.block-body :deep(h2) { font-size:18px;font-weight:700;color:#0066CC;margin:0;padding-bottom:8px;border-bottom:2px solid #E6F0FA; }
.block-body :deep(h3) { font-size:16px;font-weight:600;color:#1A1A1A;margin:0;padding-left:10px;border-left:3px solid #0066CC; }
.block-body :deep(p) { font-size:15px;color:#333;line-height:1.85;margin:0;text-align:justify;letter-spacing:0.5px;text-indent:2em; }
.block-body :deep(blockquote) { margin:0;padding:12px 16px;background:#F0F7FF;border-left:4px solid #0066CC;border-radius:0 6px 6px 0;font-size:14px;color:#555;line-height:1.7; }
.block-body :deep(ul) { margin:0;padding-left:20px;list-style:none; }
.block-body :deep(li) { font-size:15px;color:#333;line-height:1.8;margin:6px 0;padding-left:12px; }

.block-image { padding:4px 0; }
.block-img { max-width:100%;height:auto;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.08);display:block;margin:0 auto;cursor:pointer; }
.block-img:hover { opacity:0.9; }

.block-menu { position:absolute; top:8px; right:8px; opacity:0; transition:opacity 0.15s; }
.editing-text { margin-top:4px; }

/* Phone preview */
.phone-preview {
  background:#f5f5f5; border-radius:8px; padding:12px; display:flex; justify-content:center;
}
.preview-iframe { width:375px; min-height:600px; border:1px solid #e0e0e0; border-radius:8px; background:#fff; }

.picker-item { cursor:pointer; border:2px solid transparent; border-radius:6px; padding:4px; transition:border-color .15s; }
.picker-item:hover { border-color:#0066CC; }
.picker-item.selected { border-color:#0066CC; background:#F0F7FF; }
</style>
