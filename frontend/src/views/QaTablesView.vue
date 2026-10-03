<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createQaTable, deleteQaTable, listQaTables, updateQaTable, type QaTable } from '../api/qa'
import { errorMessage } from '../api/client'

const router = useRouter()
const rows = ref<QaTable[]>([])
const total = ref(0)
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const dialog = ref(false)
const editing = ref<QaTable | null>(null)
const form = reactive({ name: '', description: '' })

async function load() {
  loading.value = true
  try {
    const data = await listQaTables({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(errorMessage(error))
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
  form.name = ''
  form.description = ''
  dialog.value = true
}
function openEdit(row: QaTable) {
  editing.value = row
  form.name = row.name
  form.description = row.description || ''
  dialog.value = true
}
async function save() {
  try {
    if (editing.value) await updateQaTable(editing.value.id, form)
    else await createQaTable(form)
    ElMessage.success('保存成功')
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
async function remove(row: QaTable) {
  try {
    await ElMessageBox.confirm(`删除“${row.name}”后，其中全部问答也会删除。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteQaTable(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}
function download(row: QaTable) {
  window.open(`/api/tables/${encodeURIComponent(row.name)}/download`, '_blank')
}
onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>问答表管理</h1>
      <p class="page-subtitle">每张表对应一个数字人前端可下载的 Excel</p>
    </div>
    <el-button type="primary" @click="openCreate">新建问答表</el-button>
  </div>
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 16px">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索表名"
        style="width: 260px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button @click="search">搜索</el-button>
    </div>
    <el-table v-loading="loading" :data="rows" empty-text="还没有问答表">
      <el-table-column prop="name" label="表名" min-width="180" />
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column prop="item_count" label="问答数量" width="110" />
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="
              router.push({ name: 'qa-editor', params: { id: row.id }, query: { name: row.name } })
            "
            >编辑问答</el-button
          >
          <el-button link @click="download(row)">下载</el-button>
          <el-button link @click="openEdit(row)">重命名</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
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
  <el-dialog
    v-model="dialog"
    :title="editing ? '编辑问答表' : '新建问答表'"
    width="min(520px, 92vw)"
  >
    <el-form label-position="top">
      <el-form-item label="表名" required
        ><el-input v-model="form.name" maxlength="128"
      /></el-form-item>
      <el-form-item label="说明"
        ><el-input v-model="form.description" type="textarea" maxlength="255" show-word-limit
      /></el-form-item>
    </el-form>
    <template #footer
      ><el-button @click="dialog = false">取消</el-button
      ><el-button type="primary" :disabled="!form.name.trim()" @click="save"
        >保存</el-button
      ></template
    >
  </el-dialog>
</template>
