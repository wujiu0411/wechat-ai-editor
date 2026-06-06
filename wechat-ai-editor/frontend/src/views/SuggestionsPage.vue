<template>
  <div class="suggestions-page">
    <div class="page-header">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div>
          <h2 style="margin:0">本周选题建议</h2>
          <p style="color:#999;font-size:13px;margin:4px 0 0">AI基于日期、节气、素材库推荐选题，每周自动刷新</p>
        </div>
        <el-button @click="refreshSuggestions" :loading="refreshing">
          <el-icon><Refresh /></el-icon> 刷新选题
        </el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card v-if="loading" style="text-align:center;padding:40px">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <p style="margin-top:8px;color:#999">AI正在分析选题...</p>
        </el-card>
        <el-card v-else-if="suggestions.length" class="suggestion-list-card">
          <div v-for="(s, idx) in suggestions" :key="idx" class="suggestion-row">
            <div class="s-left">
              <el-tag :type="s.urgency === 'high' ? 'danger' : s.urgency === 'medium' ? 'warning' : 'info'" size="small">
                {{ s.urgency === 'high' ? '紧急' : s.urgency === 'medium' ? '推荐' : '常规' }}
              </el-tag>
            </div>
            <div class="s-body">
              <div class="s-title">{{ s.topic }}</div>
              <div class="s-meta">
                <el-tag size="small" type="">{{ s.content_type }}</el-tag>
                <span style="font-size:12px;color:#999;margin-left:8px">{{ s.reason }}</span>
              </div>
            </div>
            <div class="s-actions">
              <el-button type="primary" size="small" @click="generateOne(s, idx)" :loading="generatingIdx === idx">
                {{ generatingIdx === idx ? '生成中...' : '生成文章' }}
              </el-button>
              <el-popover v-if="s.image_prompts?.length" trigger="click" placement="left" :width="420">
                <template #reference>
                  <el-button size="small">配图提示词</el-button>
                </template>
                <div>
                  <p style="font-size:13px;font-weight:600;margin-bottom:8px">AI绘图提示词 — 点击复制</p>
                  <div v-for="(p, pi) in s.image_prompts" :key="pi"
                       class="prompt-item" @click="copyText(p)">
                    <span style="font-size:12px;line-height:1.5">{{ p }}</span>
                    <el-icon style="margin-left:4px;flex-shrink:0" :size="14"><DocumentCopy /></el-icon>
                  </div>
                </div>
              </el-popover>
            </div>
          </div>
        </el-card>
        <el-empty v-else description="暂无选题建议" />
      </el-col>

      <el-col :span="8">
        <el-card class="batch-card">
          <template #header><span>批量操作</span></template>
          <p style="font-size:13px;color:#666;margin-bottom:12px">一键生成所有推荐选题的文章，批量推送到历史记录</p>
          <el-button type="primary" @click="batchGenerateAll" :loading="batchGenerating" style="width:100%">
            <el-icon><MagicStick /></el-icon>
            一键生成全部（{{ Math.min(suggestions.length, 3) }}篇）
          </el-button>
          <el-divider />
          <p style="font-size:12px;color:#999">
            生成后可在历史记录中查看、编辑、同步到公众号
          </p>
        </el-card>
      </el-col>
    </el-row>

    <!-- Results after generation -->
    <div v-if="generatedResults.length" style="margin-top:16px">
      <el-card>
        <template #header>
          <span>生成结果（{{ generatedResults.length }}篇）</span>
        </template>
        <div v-for="(r, idx) in generatedResults" :key="idx" style="margin-bottom:12px">
          <el-alert :title="`#${idx + 1} ${r.title}`" :type="r.error ? 'error' : 'success'" show-icon :closable="false">
            <template v-if="!r.error">
              <span style="font-size:12px">评分: {{ r.quality_report?.score }}/100 | 配图: {{ r.images?.length }}张</span>
              <el-button size="small" style="margin-left:8px" @click="viewResult(r)">查看</el-button>
            </template>
          </el-alert>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { articleApi } from '../api'

const suggestions = ref([])
const loading = ref(true)
const refreshing = ref(false)
const generatingIdx = ref(-1)
const batchGenerating = ref(false)
const generatedResults = ref([])

async function loadSuggestions(forceRefresh = false) {
  if (!forceRefresh) loading.value = true
  try {
    const { data } = await articleApi.suggestions({ force_refresh: forceRefresh })
    suggestions.value = data.suggestions || []
  } catch (err) {
    console.error('Failed to load suggestions:', err)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function refreshSuggestions() {
  refreshing.value = true
  await loadSuggestions(true)
  ElMessage.success('选题已刷新')
}

async function generateOne(s, idx) {
  generatingIdx.value = idx
  try {
    const { data } = await articleApi.generateFromSuggestion({
      topic: s.topic,
      content_type: s.content_type,
      tone: s.content_type === '节日促销' ? '活泼、促销感' : s.content_type === '喝水知识科普' ? '科普、亲和' : '专业、科技感',
    })
    generatedResults.value.push(data)
    ElMessage.success(`已生成: ${data.article_title}`)
  } catch (err) {
    generatedResults.value.push({ title: s.topic, error: err.response?.data?.detail || '生成失败' })
    ElMessage.error('生成失败')
  } finally {
    generatingIdx.value = -1
  }
}

async function batchGenerateAll() {
  const articles = suggestions.value.slice(0, 3).map(s => ({
    content_type: s.content_type,
    tone: s.content_type === '节日促销' ? '活泼、促销感' : s.content_type === '喝水知识科普' ? '科普、亲和' : '专业、科技感',
    product_name: s.content_type === '新品上市' ? '朴道直饮机' : '',
    key_points: [],
    topic: s.topic,
  }))

  batchGenerating.value = true
  try {
    const { data } = await articleApi.batchGenerate({ articles })
    if (data.results) {
      data.results.forEach(r => {
        if (r.status === 'ok') generatedResults.value.push(r.result)
        else generatedResults.value.push({ title: `#${r.index}`, error: r.error })
      })
    }
    if (data.errors) {
      data.errors.forEach(e => generatedResults.value.push({ title: `#${e.index}`, error: e.error }))
    }
    ElMessage.success(`${data.success}篇成功, ${data.failed}篇失败`)
  } catch (err) {
    ElMessage.error('批量生成失败')
  } finally {
    batchGenerating.value = false
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('提示词已复制'),
    () => ElMessage.error('复制失败')
  )
}

function viewResult(r) {
  if (r.history_id) {
    window.open(`/history`, '_blank')
  }
}

onMounted(loadSuggestions)
</script>

<style scoped>
.suggestions-page { max-width:1200px; margin:0 auto; }
.page-header { margin-bottom:16px; }
.suggestion-row {
  display:flex; align-items:flex-start; gap:12px; padding:14px 0;
  border-bottom:1px solid #f0f0f0;
}
.suggestion-row:last-child { border-bottom:none; }
.s-left { flex-shrink:0; padding-top:2px; }
.s-body { flex:1; min-width:0; }
.s-title { font-weight:600; font-size:14px; margin-bottom:4px; }
.s-meta { display:flex; align-items:center; }
.s-actions { display:flex; gap:6px; flex-shrink:0; margin-left:12px; }
.prompt-item {
  display:flex; align-items:flex-start; background:#f5f7fa;
  padding:6px 8px; margin-bottom:6px; border-radius:6px;
  cursor:pointer; transition:background 0.15s;
}
.prompt-item:hover { background:#e8f0fe; }
</style>
