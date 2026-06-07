<template>
  <div class="create-page">
    <el-row :gutter="20">
      <el-col :span="10">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>文章参数设置</span>
              <div style="display:flex;align-items:center;gap:8px">
                <el-radio-group v-model="createMode" size="small">
                  <el-radio-button value="form">参数填表</el-radio-button>
                  <el-radio-button value="image">选图创作</el-radio-button>
                </el-radio-group>
                <el-tag type="info" size="small">朴道水汇</el-tag>
              </div>
            </div>
          </template>

          <!-- Form-based creation mode -->
          <el-form v-if="createMode === 'form'" :model="form" label-width="100px" label-position="top" size="default">
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
              <div style="display:flex;gap:8px">
                <el-button type="primary" @click="handleGenerate" :loading="generating" style="flex:1">
                  <el-icon v-if="!generating"><MagicStick /></el-icon>
                  {{ generating ? '正在生成中...' : '生成文章' }}
                </el-button>
                <el-button @click="saveDraft">
                  <el-icon><FolderChecked /></el-icon> 保存草稿
                </el-button>
                <el-badge :value="drafts.length" :hidden="!drafts.length">
                  <el-button @click="draftListVisible = true">
                    <el-icon><List /></el-icon> 草稿箱
                  </el-button>
                </el-badge>
              </div>
            </el-form-item>
          </el-form>

          <!-- Image-based creation mode -->
          <div v-if="createMode === 'image'" style="padding:0">
            <p style="font-size:13px;color:#666;margin-bottom:12px">选择几张宣传图，AI自动理解图片内容并撰写文章</p>

            <div v-if="!imageModeSelected.length" style="margin-bottom:12px">
              <el-input v-model="imageModeSearch" placeholder="搜索素材..." clearable size="small">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </div>

            <div style="max-height:350px;overflow-y:auto;margin-bottom:12px">
              <el-row :gutter="6">
                <el-col v-for="asset in filteredImageAssets" :key="asset.id" :span="8" style="margin-bottom:6px">
                  <div class="image-mode-item" :class="{ selected: imageModeSelected.includes(asset.filepath) }">
                    <img v-if="asset.file_type === 'image'" :src="assetUrl(asset.filepath)"
                         style="width:100%;height:80px;object-fit:cover;border-radius:4px;cursor:pointer"
                         @click="previewImageAsset(asset)" />
                    <div class="image-mode-overlay" @click.stop="toggleImageSelect(asset.filepath)">
                      <el-icon v-if="imageModeSelected.includes(asset.filepath)" color="#0066CC" :size="18">
                        <CircleCheckFilled />
                      </el-icon>
                      <el-icon v-else color="#aaa" :size="18"><CirclePlus /></el-icon>
                    </div>
                    <p style="font-size:10px;color:#666;margin:2px 0 0;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                      {{ asset.filename }}
                    </p>
                  </div>
                </el-col>
              </el-row>
            </div>

            <div v-if="imageModeSelected.length" style="margin-bottom:12px">
              <el-tag v-for="fp in imageModeSelected" :key="fp" closable @close="toggleImageSelect(fp)" size="small" style="margin:0 4px 4px 0">
                {{ fp.split('/').pop() }}
              </el-tag>
            </div>

            <el-form label-width="80px" label-position="top" size="default">
              <el-form-item label="语气风格">
                <el-select v-model="imageModeTone" style="width:100%">
                  <el-option label="专业、科技感" value="专业、科技感" />
                  <el-option label="活泼、促销感" value="活泼、促销感" />
                  <el-option label="科普、亲和" value="科普、亲和" />
                  <el-option label="商务、严谨" value="商务、严谨" />
                </el-select>
              </el-form-item>
              <el-form-item label="主题提示（可选）">
                <el-input v-model="imageModeTopic" placeholder="如：针对企业客户的商务饮水方案" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleGenerateFromImages" :loading="generating" style="width:100%"
                           :disabled="!imageModeSelected.length">
                  <el-icon v-if="!generating"><MagicStick /></el-icon>
                  {{ generating ? '正在生成中...' : '根据选图生成文章' }}
                </el-button>
              </el-form-item>
            </el-form>

            <div style="display:flex;gap:8px;margin-top:8px">
              <el-button @click="saveDraft" size="small">
                <el-icon><FolderChecked /></el-icon> 保存草稿
              </el-button>
              <el-badge :value="drafts.length" :hidden="!drafts.length">
                <el-button @click="draftListVisible = true" size="small">
                  <el-icon><List /></el-icon> 草稿箱
                </el-button>
              </el-badge>
            </div>
          </div>
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
              <p style="color:#0066CC;font-size:24px;font-weight:700;margin:8px 0">{{ elapsedSeconds }}s</p>
              <div style="display:flex;flex-direction:column;gap:6px;align-items:center;margin-top:8px">
                <el-tag :type="genStage === 'planning' ? 'warning' : 'info'" size="small" effect="plain">📋 规划文章结构</el-tag>
                <el-tag :type="genStage === 'drafting' ? 'warning' : 'info'" size="small" effect="plain">✍️ 逐段撰写内容</el-tag>
                <el-tag :type="genStage === 'polishing' ? 'warning' : 'info'" size="small" effect="plain">✨ 润色排版优化</el-tag>
              </div>
              <p style="color:#999;font-size:13px;margin-top:8px">预计需要40-90秒</p>
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
                  <el-button size="small" type="success" @click="openVisualEditor">
                    <el-icon><Edit /></el-icon> 可视化编辑
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

          <el-card v-if="result.images?.length" class="image-card" style="margin-top:12px">
            <template #header>
              <span>文章配图 ({{ result.images.length }}张)</span>
              <span style="font-size:12px;color:#999;margin-left:8px">可点击替换</span>
            </template>
            <div style="display:flex;gap:12px;flex-wrap:wrap">
              <div v-for="(img, idx) in result.images" :key="img.source + idx"
                   class="image-slot"
                   :class="{ dragging: dragIndex === idx }"
                   draggable="true"
                   @dragstart="onDragStart($event, idx)"
                   @dragover.prevent="onDragOver($event, idx)"
                   @drop.prevent="onDrop($event, idx)"
                   @dragend="onDragEnd">
                <div class="drag-handle" title="拖拽排序">⠿</div>
                <img v-if="!img.source?.startsWith('[缺失')"
                     :src="img.source"
                     style="width:120px;height:90px;object-fit:cover;border-radius:6px"
                     @click="openImagePicker(idx)"
                     title="点击替换图片" />
                <div v-else @click="openImagePicker(idx)" style="width:120px;height:90px;border:2px dashed #ddd;border-radius:6px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#999;font-size:12px;text-align:center">
                  {{ img.alt_text || '缺失' }}
                </div>
                <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px">
                  <p style="font-size:10px;color:#999;margin:0;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ img.filename || img.alt_text }}</p>
                  <span style="font-size:10px;color:#0066CC;font-weight:600">#{{ idx + 1 }}</span>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- Draft List Dialog -->
    <el-dialog v-model="draftListVisible" title="草稿箱" width="600px" destroy-on-close>
      <el-empty v-if="!drafts.length" description="暂无草稿" />
      <el-table v-else :data="drafts" stripe style="width:100%" max-height="400">
        <el-table-column label="草稿名称" min-width="180">
          <template #default="{ row }">
            <span style="font-weight:500">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="内容类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.data?.content_type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="保存时间" width="150">
          <template #default="{ row }">
            <span style="font-size:12px;color:#999">{{ row.savedAt }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row, $index }">
            <el-button size="small" @click="loadDraft($index)">加载</el-button>
            <el-button size="small" type="danger" @click="removeDraft($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="draftListVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Image Preview Dialog (for creation mode) -->
    <el-dialog v-model="imagePreviewVisible" title="图片预览" width="500px" destroy-on-close>
      <div v-if="imagePreviewAsset" style="max-height:65vh;overflow-y:auto;text-align:center">
        <img :src="assetUrl(imagePreviewAsset.filepath)"
             style="max-width:100%;display:block" />
        <el-descriptions :column="1" border size="small" style="margin-top:12px">
          <el-descriptions-item label="文件名">{{ imagePreviewAsset.filename }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ imagePreviewAsset.category }}</el-descriptions-item>
          <el-descriptions-item label="关键词">{{ imagePreviewAsset.keywords || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="toggleImageSelect(imagePreviewAsset.filepath)"
                   :type="imageModeSelected.includes(imagePreviewAsset.filepath) ? 'warning' : 'primary'">
          {{ imageModeSelected.includes(imagePreviewAsset.filepath) ? '取消选择' : '选用此图' }}
        </el-button>
        <el-button @click="imagePreviewVisible = false">关闭</el-button>
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
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { articleApi, templateApi, wechatApi, assetApi } from '../api'
import { assetUrl, fixHtmlImages } from '../utils/assetUrl.js'

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
const elapsedSeconds = ref(0)
const genStage = ref('planning')
let elapsedTimer = null

// Image-based creation mode
const createMode = ref('form')
const imageModeSelected = ref([])
const imageModeSearch = ref('')
const imageModeTone = ref('专业、科技感')
const imageModeTopic = ref('')
const imageModeAssets = ref([])

const filteredImageAssets = computed(() => {
  const q = imageModeSearch.value.toLowerCase()
  const assets = imageModeAssets.value.filter(a => a.file_type === 'image')
  if (!q) return assets
  return assets.filter(a =>
    a.filename.toLowerCase().includes(q) ||
    (a.keywords || '').toLowerCase().includes(q) ||
    a.category.toLowerCase().includes(q)
  )
})

async function loadImageAssets() {
  if (imageModeAssets.value.length) return
  try {
    const { data } = await assetApi.list({})
    imageModeAssets.value = data.items || []
  } catch {}
}

const imagePreviewVisible = ref(false)
const imagePreviewAsset = ref(null)

function previewImageAsset(asset) {
  imagePreviewAsset.value = asset
  imagePreviewVisible.value = true
}

function toggleImageSelect(filepath) {
  const idx = imageModeSelected.value.indexOf(filepath)
  if (idx >= 0) {
    imageModeSelected.value.splice(idx, 1)
  } else {
    if (imageModeSelected.value.length >= 10) {
      ElMessage.warning('最多选择10张图片')
      return
    }
    imageModeSelected.value.push(filepath)
  }
}

async function handleGenerateFromImages() {
  if (!imageModeSelected.value.length) {
    ElMessage.warning('请至少选择一张图片')
    return
  }
  generating.value = true
  result.value = null
  syncStatus.value = 'idle'
  elapsedSeconds.value = 0
  genStage.value = 'planning'
  elapsedTimer = setInterval(() => {
    elapsedSeconds.value++
    if (elapsedSeconds.value > 45) genStage.value = 'polishing'
    else if (elapsedSeconds.value > 15) genStage.value = 'drafting'
  }, 1000)

  try {
    const { data } = await articleApi.generateFromImages({
      image_filepaths: imageModeSelected.value,
      tone: imageModeTone.value,
      topic_hint: imageModeTopic.value || undefined,
    })
    result.value = data
    activeTab.value = 'preview'
    await nextTick()
    renderPreview()
    ElMessage.success('文章生成完成')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '生成失败，请重试')
  } finally {
    clearInterval(elapsedTimer)
    generating.value = false
  }
}

// Multi-draft system
const DRAFTS_KEY = 'wechat_editor_drafts'
const draftListVisible = ref(false)
const drafts = ref([])

const DEFAULT_DRAFTS = [
  {
    name: '案例1: 新品上市 - 名士K2智能直饮机',
    data: {
      content_type: '新品上市',
      product_name: '名士K2智能直饮机',
      key_points: ['2000G大流量', 'DPM动态蛋白纳滤技术', 'IoT智能管理', '一级水效节能40%'],
      target_audience: '企业采购决策者',
      tone: '专业、科技感',
      image_requirement: '需要产品实拍图3张 + 功能示意图2张',
    },
  },
  {
    name: '案例2: 节日促销 - 618年中大促',
    data: {
      content_type: '节日促销',
      occasion: '618年中大促',
      promotion_detail: '名士系列全线8折，赠送3年滤芯',
      deadline: '2026-06-18',
      tone: '活泼、促销感',
      image_requirement: '节日氛围图 + 产品图 + 促销海报',
    },
  },
  {
    name: '案例3: 健康科普 - 夏季如何科学补水',
    data: {
      content_type: '喝水知识科普',
      topic: '夏季如何科学补水',
      key_message: '保留矿物质的健康水更适合夏季补水',
      product_association: '朴道DPM技术保留有益矿物质',
      tone: '科普、亲和',
      image_requirement: '科普插图 + 朴道产品图',
    },
  },
]

function loadDrafts() {
  try {
    const saved = localStorage.getItem(DRAFTS_KEY)
    drafts.value = saved ? JSON.parse(saved) : []
  } catch {
    drafts.value = []
  }
  // First visit: seed with default examples
  if (!localStorage.getItem(DRAFTS_KEY)) {
    drafts.value = DEFAULT_DRAFTS.map(d => ({
      ...d,
      savedAt: new Date().toLocaleString(),
    }))
    saveDraftsToStorage()
  }
}

function saveDraftsToStorage() {
  localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts.value))
}

function saveDraft() {
  const name = form.value.product_name || form.value.topic || form.value.occasion || form.value.content_type
  const draftName = `${form.value.content_type} - ${name}`
  const existing = drafts.value.findIndex(d => d.name === draftName)
  const entry = {
    name: draftName,
    data: { ...form.value },
    savedAt: new Date().toLocaleString(),
  }
  if (existing >= 0) {
    drafts.value[existing] = entry
  } else {
    drafts.value.unshift(entry)
  }
  saveDraftsToStorage()
  ElMessage.success(`草稿"${draftName}"已保存`)
}

function loadDraft(index) {
  const draft = drafts.value[index]
  if (!draft) return
  const data = draft.data
  Object.keys(data).forEach(k => {
    if (k in form.value) form.value[k] = data[k]
  })
  draftListVisible.value = false
  ElMessage.success(`已加载草稿"${draft.name}"`)
}

function removeDraft(index) {
  drafts.value.splice(index, 1)
  saveDraftsToStorage()
  ElMessage.success('草稿已删除')
}

// Auto-save current form as draft every 5 seconds
let autoSaveTimer = null
watch(form, () => {
  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    const name = form.value.product_name || form.value.topic || form.value.occasion || '未命名'
    const draftName = `[自动] ${form.value.content_type} - ${name}`
    const existing = drafts.value.findIndex(d => d.name === draftName)
    const entry = {
      name: draftName,
      data: { ...form.value },
      savedAt: new Date().toLocaleString(),
    }
    if (existing >= 0) {
      drafts.value[existing] = entry
    } else {
      drafts.value.unshift(entry)
    }
    // Keep max 10 auto-saved drafts
    if (drafts.value.length > 10) {
      const autoDrafts = drafts.value.filter(d => d.name.startsWith('[自动]'))
      if (autoDrafts.length > 5) {
        const oldest = autoDrafts[autoDrafts.length - 1]
        const idx = drafts.value.indexOf(oldest)
        if (idx >= 0) drafts.value.splice(idx, 1)
      }
    }
    saveDraftsToStorage()
  }, 5000)
}, { deep: true })

// Image picker
const pickerVisible = ref(false)
const pickerSearch = ref('')
const pickerAssets = ref([])
const pickerSelected = ref(null)
const pickerTargetIdx = ref(-1)

const filteredPickerAssets = computed(() => {
  if (!pickerSearch.value) return pickerAssets.value
  const q = pickerSearch.value.toLowerCase()
  return pickerAssets.value.filter(a =>
    a.filename.toLowerCase().includes(q) ||
    (a.keywords || '').toLowerCase().includes(q) ||
    a.category.toLowerCase().includes(q)
  )
})

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

// Drag-and-drop image reordering
const dragIndex = ref(-1)

function onDragStart(e, idx) {
  dragIndex.value = idx
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(idx))
}

function onDragOver(e, idx) {
  if (dragIndex.value === idx) return
  e.dataTransfer.dropEffect = 'move'
}

function onDrop(e, targetIdx) {
  const sourceIdx = dragIndex.value
  if (sourceIdx < 0 || sourceIdx === targetIdx) return

  // Swap in images array
  const imgs = result.value.images
  const temp = imgs[sourceIdx]
  imgs[sourceIdx] = imgs[targetIdx]
  imgs[targetIdx] = temp

  // Swap the corresponding img tags in HTML
  const srcImgs = result.value.html_output.match(/<img[^>]*>/g) || []
  if (srcImgs[sourceIdx] && srcImgs[targetIdx]) {
    result.value.html_output = result.value.html_output
      .replace(srcImgs[sourceIdx], '__SWAP_TEMP__')
      .replace(srcImgs[targetIdx], srcImgs[sourceIdx])
      .replace('__SWAP_TEMP__', srcImgs[targetIdx])
  }

  nextTick(() => renderPreview())
}

function onDragEnd() {
  dragIndex.value = -1
}

function confirmReplaceImage() {
  if (pickerSelected.value === null || pickerTargetIdx.value < 0) return
  const asset = pickerAssets.value.find(a => a.id === pickerSelected.value)
  if (!asset) return

  const img = result.value.images[pickerTargetIdx.value]
  const oldSrc = img.source
  const newSrc = assetUrl(asset.filepath)

  // Replace in images array
  img.source = newSrc
  img.filename = asset.filename
  img.alt_text = asset.filename

  // Replace in HTML
  result.value.html_output = result.value.html_output.replace(oldSrc, newSrc)

  // Re-render preview
  nextTick(() => renderPreview())

  pickerVisible.value = false
  ElMessage.success('配图已替换')
}

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

watch(createMode, (mode) => {
  if (mode === 'image') loadImageAssets()
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
  elapsedSeconds.value = 0
  genStage.value = 'planning'
  elapsedTimer = setInterval(() => {
    elapsedSeconds.value++
    if (elapsedSeconds.value > 45) genStage.value = 'polishing'
    else if (elapsedSeconds.value > 15) genStage.value = 'drafting'
  }, 1000)

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
    clearInterval(elapsedTimer)
    generating.value = false
  }
}

function renderPreview() {
  if (previewFrame.value && result.value) {
    const doc = previewFrame.value.contentDocument
    const html = fixHtmlImages(result.value.html_output)
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

async function openVisualEditor() {
  if (!result.value) return
  sessionStorage.setItem('editor_article', JSON.stringify({
    article_title: result.value.article_title,
    call_to_action: result.value.call_to_action,
    html_output: fixHtmlImages(result.value.html_output),
    history_id: result.value.history_id,
  }))
  window.open('/editor', '_blank')
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
      history_id: result.value.history_id,
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

onMounted(() => {
  loadDrafts()
})
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
.markdown-editor {
  width: 100%;
  min-height: 400px;
  resize: vertical;
  font-family: monospace;
  outline: none;
  border: none;
}
.markdown-editor:focus {
  background: #2d2d2d;
}
.result-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.image-slot {
  cursor: grab;
  position: relative;
  transition: transform 0.15s, opacity 0.15s;
  padding: 4px;
  border: 2px solid transparent;
  border-radius: 8px;
}
.image-slot:hover {
  border-color: #e0e0e0;
}
.image-slot.dragging {
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
.image-mode-item {
  position: relative;
  border: 2px solid transparent;
  border-radius: 6px;
  padding: 2px;
  transition: border-color 0.15s;
}
.image-mode-item:hover {
  border-color: #e0e0e0;
}
.image-mode-item.selected {
  border-color: #0066CC;
  background: #F0F7FF;
}
.image-mode-overlay {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  background: rgba(255,255,255,0.9);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
</style>
