<template>
  <div class="create-page">
    <el-row :gutter="20">
      <el-col :span="10">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>文章参数设置</span>
              <el-tag type="info" size="small">朴道水汇</el-tag>
            </div>
          </template>
          <el-form :model="form" label-width="100px" label-position="top" size="default">
            <el-form-item label="内容类型" required>
              <el-select v-model="form.content_type" placeholder="选择内容类型" style="width:100%">
                <el-option label="新品上市" value="新品上市" />
                <el-option label="节日促销" value="节日促销" />
                <el-option label="喝水知识科普" value="喝水知识科普" />
                <el-option label="装机案例" value="装机案例" />
                <el-option label="获奖推送" value="获奖推送" />
                <el-option label="营销案例" value="营销案例" />
              </el-select>
            </el-form-item>

            <el-form-item label="排版模板">
              <el-select v-model="form.template_id" placeholder="选择排版模板" style="width:100%">
                <el-option
                  v-for="t in templates"
                  :key="t.id"
                  :label="t.name"
                  :value="t.id"
                >
                  <span style="display:flex;align-items:center;gap:8px">
                    <span :style="{width:'12px',height:'12px',borderRadius:'2px',background:t.preview_color,display:'inline-block'}"></span>
                    {{ t.name }} - {{ t.description }}
                  </span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item v-if="showProductFields" label="产品名称">
              <el-input v-model="form.product_name" placeholder="如：名士K2智能直饮机" />
            </el-form-item>

            <el-form-item v-if="showProductFields" label="核心卖点">
              <div style="width:100%">
                <el-tag
                  v-for="(point, idx) in form.key_points"
                  :key="idx"
                  closable
                  @close="form.key_points.splice(idx, 1)"
                  style="margin:0 4px 4px 0"
                >{{ point }}</el-tag>
                <el-input
                  v-model="newPoint"
                  size="small"
                  placeholder="输入卖点后按回车"
                  @keyup.enter="addPoint"
                  style="width:200px;margin-top:4px"
                />
              </div>
            </el-form-item>

            <el-form-item v-if="showProductFields" label="目标受众">
              <el-input v-model="form.target_audience" placeholder="如：企业采购决策者" />
            </el-form-item>

            <el-form-item v-if="form.content_type === '节日促销'" label="节日/场合">
              <el-input v-model="form.occasion" placeholder="如：618年中大促" />
            </el-form-item>

            <el-form-item v-if="form.content_type === '节日促销'" label="促销详情">
              <el-input v-model="form.promotion_detail" type="textarea" :rows="2" placeholder="如：名士系列全线8折" />
            </el-form-item>

            <el-form-item v-if="form.content_type === '节日促销'" label="截止日期">
              <el-date-picker v-model="form.deadline" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
            </el-form-item>

            <el-form-item v-if="form.content_type === '喝水知识科普'" label="科普主题">
              <el-input v-model="form.topic" placeholder="如：夏季如何科学补水" />
            </el-form-item>

            <el-form-item v-if="form.content_type === '喝水知识科普'" label="核心信息">
              <el-input v-model="form.key_message" placeholder="如：保留矿物质的健康水更适合夏季补水" />
            </el-form-item>

            <el-form-item v-if="form.content_type === '喝水知识科普'" label="产品关联">
              <el-input v-model="form.product_association" placeholder="如：朴道DPM技术保留有益矿物质" />
            </el-form-item>

            <template v-if="showInstallFields">
              <el-form-item label="客户名称">
                <el-input v-model="form.customer_name" placeholder="如：上海XX科技有限公司" />
              </el-form-item>
              <el-form-item label="装机地址">
                <el-input v-model="form.install_location" placeholder="如：客户总部办公楼" />
              </el-form-item>
              <el-form-item label="设备型号">
                <el-input v-model="form.equipment_model" placeholder="如：名士K2智能直饮机" />
              </el-form-item>
              <el-form-item label="使用效果">
                <el-input v-model="form.install_results" type="textarea" :rows="2" placeholder="如：员工满意度提升30%，年节水200吨" />
              </el-form-item>
            </template>

            <template v-if="showAwardFields">
              <el-form-item label="获奖名称">
                <el-input v-model="form.award_name" placeholder="如：2024年度净水行业创新企业奖" />
              </el-form-item>
              <el-form-item label="颁奖机构">
                <el-input v-model="form.award_organization" placeholder="如：中国净水行业协会" />
              </el-form-item>
              <el-form-item label="获奖意义">
                <el-input v-model="form.award_significance" type="textarea" :rows="2" placeholder="如：彰显朴道技术创新实力和行业认可度" />
              </el-form-item>
            </template>

            <template v-if="showMarketingFields">
              <el-form-item label="案例名称">
                <el-input v-model="form.case_name" placeholder="如：华为总部饮水改造项目" />
              </el-form-item>
              <el-form-item label="合作客户">
                <el-input v-model="form.client_name" placeholder="如：华为技术有限公司" />
              </el-form-item>
              <el-form-item label="客户挑战">
                <el-input v-model="form.case_challenge" type="textarea" :rows="2" placeholder="如：员工饮水品质参差不齐，桶装水管理混乱" />
              </el-form-item>
              <el-form-item label="解决方案">
                <el-input v-model="form.case_solution" type="textarea" :rows="2" placeholder="如：部署朴道商务直饮机+全屋净水系统" />
              </el-form-item>
              <el-form-item label="案例成果">
                <el-input v-model="form.case_results" type="textarea" :rows="2" placeholder="如：年节约饮水成本40%，员工满意度提升至95%" />
              </el-form-item>
            </template>

            <el-form-item label="语气风格">
              <el-select v-model="form.tone" style="width:100%">
                <el-option label="专业、科技感" value="专业、科技感" />
                <el-option label="活泼、促销感" value="活泼、促销感" />
                <el-option label="科普、亲和" value="科普、亲和" />
                <el-option label="商务、严谨" value="商务、严谨" />
              </el-select>
            </el-form-item>

            <el-form-item label="图片需求描述">
              <el-input v-model="form.image_requirement" type="textarea" :rows="2" placeholder="如：需要产品实拍图3张 + 功能示意图2张" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleGenerate" :loading="generating" style="width:100%">
                <el-icon v-if="!generating"><MagicStick /></el-icon>
                {{ generating ? '正在生成中...' : '生成文章' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card v-if="!result && !generating" class="preview-card empty-preview">
          <el-empty description="设置参数后点击生成文章" />
        </el-card>

        <div v-if="generating" class="preview-card loading-preview">
          <el-card>
            <div style="text-align:center;padding:60px 0">
              <el-icon class="is-loading" :size="48" color="#0066CC"><Loading /></el-icon>
              <p style="margin-top:16px;color:#666">AI正在创作中，请稍候...</p>
              <p style="color:#999;font-size:13px">预计需要30-60秒</p>
            </div>
          </el-card>
        </div>

        <div v-if="result" class="result-area">
          <el-card class="preview-card">
            <template #header>
              <div class="card-header">
                <span>文章预览</span>
                <div>
                  <el-button type="primary" size="small" @click="copyHtml">
                    <el-icon><CopyDocument /></el-icon> 复制HTML
                  </el-button>
                  <el-button size="small" @click="copyMarkdown">
                    <el-icon><DocumentCopy /></el-icon> 复制Markdown
                  </el-button>
                  <el-button
                    size="small"
                    :type="syncStatus === 'synced' ? 'success' : 'warning'"
                    :loading="syncStatus === 'syncing'"
                    @click="syncToWechat"
                  >
                    <el-icon><Promotion /></el-icon>
                    {{ syncStatus === 'synced' ? '已同步' : syncStatus === 'syncing' ? '同步中...' : '同步到公众号' }}
                  </el-button>
                </div>
              </div>
            </template>

            <div class="result-meta">
              <el-tag>{{ result.article_title }}</el-tag>
              <el-tag type="info" size="small">阅读约{{ result.estimated_reading_time }}</el-tag>
              <el-tag v-if="result.quality_report" :type="result.quality_report.passed ? 'success' : 'danger'" size="small">
                质量评分: {{ result.quality_report.score }}/100
              </el-tag>
            </div>

            <el-tabs v-model="activeTab">
              <el-tab-pane label="HTML预览" name="preview">
                <div class="html-preview-wrapper">
                  <iframe ref="previewFrame" class="preview-iframe" sandbox="allow-same-origin"></iframe>
                </div>
              </el-tab-pane>
              <el-tab-pane label="HTML代码" name="html">
                <pre class="code-block">{{ result.html_output }}</pre>
              </el-tab-pane>
              <el-tab-pane label="Markdown" name="markdown">
                <pre class="code-block">{{ result.article_content_markdown }}</pre>
              </el-tab-pane>
            </el-tabs>
          </el-card>

          <el-card v-if="result.quality_report" class="quality-card" style="margin-top:12px">
            <template #header><span>质量检查报告</span></template>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="字数">{{ result.quality_report.word_count }}</el-descriptions-item>
              <el-descriptions-item label="配图数">{{ result.quality_report.image_count }}</el-descriptions-item>
              <el-descriptions-item label="缺失图片">{{ result.quality_report.missing_image_count }}</el-descriptions-item>
              <el-descriptions-item label="评分">{{ result.quality_report.score }}/100</el-descriptions-item>
            </el-descriptions>
            <div v-if="result.quality_report.issues?.length" style="margin-top:12px">
              <el-alert v-for="issue in result.quality_report.issues" :key="issue" :title="issue" type="error" show-icon :closable="false" style="margin-bottom:6px" />
            </div>
            <div v-if="result.quality_report.warnings?.length" style="margin-top:8px">
              <el-alert v-for="warn in result.quality_report.warnings" :key="warn" :title="warn" type="warning" show-icon :closable="false" style="margin-bottom:6px" />
            </div>
          </el-card>

          <el-card class="seo-card" style="margin-top:12px">
            <template #header><span>SEO关键词 & CTA</span></template>
            <div>
              <el-tag v-for="kw in result.seo_keywords" :key="kw" style="margin:0 4px 4px 0">{{ kw }}</el-tag>
            </div>
            <p style="margin-top:8px;color:#666;font-size:13px">CTA: {{ result.call_to_action }}</p>
          </el-card>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { articleApi, templateApi, wechatApi } from '../api'

const form = ref({
  content_type: '新品上市',
  product_name: '',
  key_points: [],
  target_audience: '',
  tone: '专业、科技感',
  occasion: '',
  promotion_detail: '',
  deadline: '',
  topic: '',
  key_message: '',
  product_association: '',
  image_requirement: '',
  template_id: '',
  customer_name: '',
  install_location: '',
  equipment_model: '',
  install_results: '',
  award_name: '',
  award_organization: '',
  award_significance: '',
  case_name: '',
  client_name: '',
  case_challenge: '',
  case_solution: '',
  case_results: '',
})

const newPoint = ref('')
const generating = ref(false)
const result = ref(null)
const activeTab = ref('preview')
const previewFrame = ref(null)
const templates = ref([])
const syncStatus = ref('idle')

const showProductFields = computed(() => {
  return ['新品上市', '装机案例', '获奖推送', '营销案例'].includes(form.value.content_type)
})

const showInstallFields = computed(() => form.value.content_type === '装机案例')
const showAwardFields = computed(() => form.value.content_type === '获奖推送')
const showMarketingFields = computed(() => form.value.content_type === '营销案例')

watch(() => form.value.content_type, (val) => {
  const autoTemplate = { '新品上市': 'tech_pro', '节日促销': 'festival', '喝水知识科普': 'science', '装机案例': 'tech_pro', '获奖推送': 'tech_pro', '营销案例': 'tech_pro' }
  form.value.template_id = autoTemplate[val] || ''
  const autoTone = { '新品上市': '专业、科技感', '节日促销': '活泼、促销感', '喝水知识科普': '科普、亲和', '装机案例': '商务、严谨', '获奖推送': '商务、严谨', '营销案例': '商务、严谨' }
  form.value.tone = autoTone[val] || '专业、科技感'
})

function addPoint() {
  if (newPoint.value.trim()) {
    form.value.key_points.push(newPoint.value.trim())
    newPoint.value = ''
  }
}

async function handleGenerate() {
  if (!form.value.content_type) {
    ElMessage.warning('请选择内容类型')
    return
  }

  generating.value = true
  result.value = null
  syncStatus.value = 'idle'

  try {
    const payload = { ...form.value }
    if (!payload.key_points?.length) delete payload.key_points
    if (!payload.product_name) delete payload.product_name
    if (!payload.template_id) delete payload.template_id

    const { data } = await articleApi.generate(payload)
    result.value = data
    activeTab.value = 'preview'

    await nextTick()
    renderPreview()

    ElMessage.success('文章生成完成')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '生成失败，请重试')
  } finally {
    generating.value = false
  }
}

function renderPreview() {
  if (previewFrame.value && result.value) {
    const doc = previewFrame.value.contentDocument
    doc.open()
    doc.write(`
      <html><head>
        <meta charset="utf-8">
        <style>body{margin:0;padding:0;background:#f5f5f5;display:flex;justify-content:center;}</style>
      </head><body>
        ${result.value.html_output}
      </body></html>
    `)
    doc.close()
  }
}

async function copyHtml() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value.html_output)
    ElMessage.success('HTML已复制到剪贴板，可直接粘贴到公众号后台')
  } catch {
    _fallbackCopy(result.value.html_output)
  }
}

async function copyMarkdown() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value.article_content_markdown)
    ElMessage.success('Markdown已复制到剪贴板')
  } catch {
    _fallbackCopy(result.value.article_content_markdown)
  }
}

function _fallbackCopy(text) {
  const ta = document.createElement('textarea')
  ta.value = text
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  document.body.removeChild(ta)
  ElMessage.success('已复制到剪贴板')
}

async function syncToWechat() {
  if (!result.value) return
  syncStatus.value = 'syncing'
  try {
    await wechatApi.sync({
      title: result.value.article_title,
      html_output: result.value.html_output,
    })
    syncStatus.value = 'synced'
    ElMessage.success('已同步到公众号草稿箱')
  } catch (err) {
    syncStatus.value = 'idle'
    ElMessage.error(err.response?.data?.detail || '同步失败，请确认公众号已配置')
  }
}

async function loadTemplates() {
  try {
    const { data } = await templateApi.list()
    templates.value = data
  } catch {}
}

loadTemplates()
</script>

<style scoped>
.create-page {
  max-width: 1400px;
  margin: 0 auto;
}
.input-card, .preview-card {
  min-height: 500px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.empty-preview {
  display: flex;
  align-items: center;
  justify-content: center;
}
.html-preview-wrapper {
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
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.result-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
</style>
