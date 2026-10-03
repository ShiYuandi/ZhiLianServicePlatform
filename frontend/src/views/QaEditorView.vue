<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import {
  batchQaItems,
  createQaItem,
  deleteQaItem,
  importQaExcel,
  listQaItems,
  updateQaItem,
  type QaItem,
} from '../api/qa'
import { errorMessage } from '../api/client'

const route = useRoute(),
  router = useRouter()
const tableId = Number(route.params.id)
const tableName = computed(() => String(route.query.name || `问答表 ${tableId}`))
const rows = ref<QaItem[]>([]),
  total = ref(0),
  loading = ref(false),
  keyword = ref(''),
  page = ref(1)
const pageSize = 50
const editor = ref(false),
  batchDialog = ref(false),
  importDialog = ref(false)
const editing = ref<QaItem | null>(null)
const form = reactive({ question: '', answer: '', sort_order: 0 })
const batchText = ref(''),
  importMode = ref<'append' | 'replace'>('append'),
  selectedFile = ref<File | null>(null)

async function load() {
  loading.value = true
  try {
    const data = await listQaItems(tableId, {
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
    })
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}
function search() {
  page.value = 1
  void load()
}
function openCreate() {
  editing.value = null
  Object.assign(form, { question: '', answer: '', sort_order: total.value })
  editor.value = true
}
function openEdit(row: QaItem) {
  editing.value = row
  Object.assign(form, { question: row.question, answer: row.answer, sort_order: row.sort_order })
  editor.value = true
}
async function save() {
  try {
    if (editing.value) await updateQaItem(editing.value.id, form)
    else await createQaItem(tableId, form)
    editor.value = false
    ElMessage.success('保存成功')
    await load()
  } catch (e) {
    ElMessage.error(errorMessage(e))
  }
}
async function remove(row: QaItem) {
  try {
    await ElMessageBox.confirm('确认删除这条问答？', '删除确认', { type: 'warning' })
    await deleteQaItem(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(errorMessage(e))
  }
}
async function submitBatch() {
  const items = batchText.value
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line, index) => {
      const split = line.indexOf('\t')
      if (split < 0) throw new Error(`第 ${index + 1} 行缺少 Tab 分隔符`)
      return {
        question: line.slice(0, split).trim(),
        answer: line.slice(split + 1).trim(),
        sort_order: total.value + index,
      }
    })
  try {
    if (!items.length) throw new Error('请粘贴问答内容')
    await batchQaItems(tableId, items)
    batchDialog.value = false
    batchText.value = ''
    ElMessage.success(`已添加 ${items.length} 条`)
    await load()
  } catch (e) {
    ElMessage.error(errorMessage(e))
  }
}
function chooseFile(file: UploadFile) {
  selectedFile.value = file.raw || null
}
async function submitImport() {
  if (!selectedFile.value) return ElMessage.warning('请选择 .xlsx 文件')
  try {
    if (importMode.value === 'replace')
      await ElMessageBox.confirm(`替换将删除“${tableName.value}”的现有问答。`, '确认替换', {
        type: 'warning',
      })
    const res = await importQaExcel(tableId, selectedFile.value, importMode.value)
    importDialog.value = false
    selectedFile.value = null
    ElMessage.success(`成功导入 ${res.data.count} 条`)
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(errorMessage(e))
  }
}
onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <el-button link @click="router.push({ name: 'qa-tables' })">← 返回问答表</el-button>
      <h1>{{ tableName }}</h1>
      <p class="page-subtitle">忽略问题前后空格和大小写后，同一张表内不可重复</p>
    </div>
    <div class="toolbar">
      <el-button @click="batchDialog = true">批量粘贴</el-button
      ><el-button @click="importDialog = true">导入 Excel</el-button
      ><el-button type="primary" @click="openCreate">新增问答</el-button>
    </div>
  </div>
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 16px">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索问题或答案"
        style="width: 280px"
        @keyup.enter="search"
        @clear="search"
      /><el-button @click="search">搜索</el-button
      ><span class="page-subtitle">共 {{ total }} 条</span>
    </div>
    <el-table
      v-loading="loading"
      :data="rows"
      empty-text="还没有问答数据"
      max-height="calc(100vh - 265px)"
    >
      <el-table-column type="index" width="60" />
      <el-table-column prop="question" label="问题" min-width="260" show-overflow-tooltip />
      <el-table-column prop="answer" label="固定答案" min-width="380" show-overflow-tooltip />
      <el-table-column label="操作" width="130" fixed="right"
        ><template #default="{ row }"
          ><el-button link type="primary" @click="openEdit(row)">编辑</el-button
          ><el-button link type="danger" @click="remove(row)">删除</el-button></template
        ></el-table-column
      >
    </el-table>
    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      style="margin-top: 18px"
      @current-change="load"
    />
  </div>
  <el-dialog v-model="editor" :title="editing ? '编辑问答' : '新增问答'" width="min(720px,94vw)"
    ><el-form label-position="top"
      ><el-form-item label="问题" required
        ><el-input
          v-model="form.question"
          type="textarea"
          :rows="3"
          maxlength="1000"
          show-word-limit /></el-form-item
      ><el-form-item label="固定答案" required
        ><el-input
          v-model="form.answer"
          type="textarea"
          :rows="7"
          maxlength="20000"
          show-word-limit /></el-form-item></el-form
    ><template #footer
      ><el-button @click="editor = false">取消</el-button
      ><el-button
        type="primary"
        :disabled="!form.question.trim() || !form.answer.trim()"
        @click="save"
        >保存</el-button
      ></template
    ></el-dialog
  >
  <el-dialog v-model="batchDialog" title="批量粘贴问答" width="min(760px,94vw)"
    ><p class="page-subtitle">
      每行一组，问题与固定答案之间使用 Tab 分隔，可直接从 Excel 两列复制。
    </p>
    <el-input
      v-model="batchText"
      type="textarea"
      :rows="14"
      placeholder="问题一[TAB]固定答案一&#10;问题二[TAB]固定答案二"
    /><template #footer
      ><el-button @click="batchDialog = false">取消</el-button
      ><el-button type="primary" @click="submitBatch">校验并添加</el-button></template
    ></el-dialog
  >
  <el-dialog v-model="importDialog" title="导入 Excel" width="min(560px,94vw)"
    ><el-alert
      title="第一行必须且只能包含“问题、固定答案”两列"
      type="info"
      :closable="false"
    /><el-radio-group v-model="importMode" style="margin: 20px 0"
      ><el-radio-button value="append">追加导入</el-radio-button
      ><el-radio-button value="replace">清空后替换</el-radio-button></el-radio-group
    ><el-upload drag :auto-upload="false" :limit="1" accept=".xlsx" :on-change="chooseFile"
      ><div>拖放或点击选择 .xlsx 文件</div></el-upload
    ><template #footer
      ><el-button @click="importDialog = false">取消</el-button
      ><el-button type="primary" @click="submitImport">开始导入</el-button></template
    ></el-dialog
  >
</template>
