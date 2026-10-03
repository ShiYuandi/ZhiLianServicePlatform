<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, CopyDocument } from '@element-plus/icons-vue'
import {
  createExternalApiProxy,
  deleteExternalApiProxy,
  listExternalApiProxies,
  updateExternalApiProxy,
  type ExternalApiProxy,
  type ExternalApiProxyPayload,
} from '../api/externalApiProxies'
import { errorMessage } from '../api/client'

const rows = ref<ExternalApiProxy[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editing = ref<ExternalApiProxy | null>(null)
const form = reactive<ExternalApiProxyPayload>({ targetUrl: '', enabled: true })

async function load() {
  loading.value = true
  try {
    const result = await listExternalApiProxies({ page: page.value, page_size: pageSize })
    rows.value = result.items
    total.value = result.total
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.targetUrl = ''
  form.enabled = true
  dialogVisible.value = true
}

function openEdit(row: ExternalApiProxy) {
  editing.value = row
  form.targetUrl = row.targetUrl
  form.enabled = row.enabled
  dialogVisible.value = true
}

async function save() {
  if (!form.targetUrl.trim()) {
    ElMessage.warning('请填写上游接口网址')
    return
  }
  saving.value = true
  try {
    const payload = { targetUrl: form.targetUrl.trim(), enabled: form.enabled }
    if (editing.value) await updateExternalApiProxy(editing.value.proxyUuid, payload)
    else await createExternalApiProxy(payload)
    ElMessage.success(editing.value ? '代理配置已更新' : '代理配置已创建')
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    saving.value = false
  }
}

async function remove(row: ExternalApiProxy) {
  try {
    await ElMessageBox.confirm('删除后该 UUID 将立即失效，确定继续吗？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteExternalApiProxy(row.proxyUuid)
    ElMessage.success('代理配置已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}

async function copy(value: string) {
  try {
    // Clipboard API 只在 HTTPS 或 localhost 可用；内网 HTTP 页面使用降级方案。
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
    } else {
      throw new Error('Clipboard API unavailable')
    }
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = value
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const copied = document.execCommand('copy')
    textarea.remove()
    if (!copied) {
      ElMessage.error('复制失败，请手动选择并复制地址')
      return
    }
  }
  ElMessage.success('已复制到剪贴板')
}

function publicUrl(row: ExternalApiProxy) {
  return `${window.location.origin}/api/external-proxies/${row.proxyUuid}`
}

onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>外部接口代理</h1>
      <p class="page-subtitle">配置上游网址，平台通过 UUID 原样转发请求和响应，解决前端跨域问题</p>
    </div>
    <el-button type="primary" :icon="Plus" @click="openCreate">新增代理</el-button>
  </div>
  <el-alert
    title="前端只访问代理地址，不需要直接请求上游接口。请只配置可信的网址。"
    type="info"
    :closable="false"
    show-icon
    style="margin-bottom: 18px"
  />
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 16px">
      <el-button :icon="Refresh" @click="load">刷新</el-button>
      <span class="page-subtitle">共 {{ total }} 个代理</span>
    </div>
    <el-table v-loading="loading" :data="rows" empty-text="还没有外部接口代理">
      <el-table-column label="代理 UUID" min-width="300">
        <template #default="{ row }"><code>{{ row.proxyUuid }}</code></template>
      </el-table-column>
      <el-table-column label="上游网址" min-width="360" show-overflow-tooltip>
        <template #default="{ row }">{{ row.targetUrl }}</template>
      </el-table-column>
      <el-table-column label="前端访问地址" min-width="360" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="url-cell"><code>{{ publicUrl(row) }}</code><el-button link :icon="CopyDocument" @click="copy(publicUrl(row))" /></div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" style="margin-top: 18px" @current-change="load" />
  </div>

  <el-dialog v-model="dialogVisible" :title="editing ? '编辑外部接口代理' : '新增外部接口代理'" width="min(640px, 92vw)">
    <el-form label-position="top">
      <el-form-item label="上游接口完整网址" required><el-input v-model="form.targetUrl" placeholder="例如：https://example.com/api/v1/data" /></el-form-item>
      <el-form-item label="启用公开转发"><el-switch v-model="form.enabled" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
  </el-dialog>
</template>

<style scoped>
.url-cell { display: flex; align-items: center; gap: 4px; min-width: 0; }
.url-cell code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
