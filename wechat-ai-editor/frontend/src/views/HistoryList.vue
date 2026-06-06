<template>
  <div class="history-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>生成历史</span>
          <el-tag type="info">共 {{ total }} 条记录</el-tag>
        </div>
      </template>

      <el-table :data="items" stripe style="width:100%" @row-click="showDetail">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="content_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.content_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="article_title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="生成时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="viewHtml(row)">查看HTML</el-button>
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
      </div>
      <template #footer>
        <el-button type="primary" @click="copyCurrentHtml">复制HTML</el-button>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { historyApi } from '../api'

const items = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const dialogVisible = ref(false)
const currentItem = ref(null)
const dialogFrame = ref(null)

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
    doc.open()
    doc.write(`
      <html><head>
        <meta charset="utf-8">
        <style>body{margin:0;padding:0;background:#f5f5f5;display:flex;justify-content:center;}</style>
      </head><body>
        ${currentItem.value.html_output}
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
</style>
