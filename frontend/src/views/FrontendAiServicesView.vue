<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  archiveFrontendAiService,
  createFrontendAiService,
  getFrontendAiService,
  listFrontendAiServices,
  rotateFrontendAiServiceKey,
  updateFrontendAiService,
  type FrontendAiService,
  type FrontendAiServicePayload,
} from '../api/frontendAiServices'
import { listAiModels, type AiModelListItem } from '../api/aiModels'
import { errorMessage } from '../api/client'
import ApiKeyRevealDialog from '../components/ApiKeyRevealDialog.vue'

const rows = ref<FrontendAiService[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const revealVisible = ref(false)
const revealedKey = ref('')
const speechModels = ref<AiModelListItem[]>([])
const imageModels = ref<AiModelListItem[]>([])
const allowedOriginsText = ref('')
const form = reactive<FrontendAiServicePayload>(defaultForm())

function defaultForm(): FrontendAiServicePayload {
  return {
    serviceName: '',
    serviceCode: '',
    enabled: false,
    remark: '',
    rateLimitPerMinute: 60,
    maxInflightTasks: 3,
    allowedOrigins: [],
  }
}

async function load() {
  loading.value = true
  try {
    const [services, speech, image] = await Promise.all([
      listFrontendAiServices({ page: page.value, page_size: pageSize, keyword: keyword.value || undefined }),
      listAiModels('speech-recognition', { page: 1, page_size: 100, enabled: true }),
      listAiModels('image-generation', { page: 1, page_size: 100, enabled: true }),
    ])
    rows.value = services.items
    total.value = services.total
    speechModels.value = speech.items
    imageModels.value = image.items
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, defaultForm())
  allowedOriginsText.value = ''
  dialogVisible.value = true
}

async function openEdit(row: FrontendAiService) {
  try {
    const service = await getFrontendAiService(row.id)
    Object.assign(form, defaultForm(), service, { serviceCode: row.serviceCode })
    allowedOriginsText.value = service.allowedOrigins.join(', ')
    editingId.value = row.id
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function payload(): FrontendAiServicePayload {
  return {
    serviceName: form.serviceName.trim(),
    enabled: form.enabled,
    remark: form.remark?.trim() || undefined,
    rateLimitPerMinute: form.rateLimitPerMinute,
    maxInflightTasks: form.maxInflightTasks,
    allowedOrigins: allowedOriginsText.value.split(',').map((item) => item.trim()).filter(Boolean),
    speechModelId: form.speechModelId,
    imageModelId: form.imageModelId,
  }
}

async function save() {
  if (!form.serviceName.trim()) {
    ElMessage.warning('请填写服务名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) await updateFrontendAiService(editingId.value, payload())
    else {
      const created = await createFrontendAiService(payload())
      revealedKey.value = created.apiKey
      revealVisible.value = true
    }
    ElMessage.success(editingId.value ? '服务已更新' : '服务已创建')
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    saving.value = false
  }
}

async function rotate(row: FrontendAiService) {
  try {
    await ElMessageBox.confirm('轮换后旧 API Key 会立即失效，确定继续吗？', '确认轮换 Key', { type: 'warning' })
    const result = await rotateFrontendAiServiceKey(row.id)
    revealedKey.value = result.apiKey
    revealVisible.value = true
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}

async function archive(row: FrontendAiService) {
  try {
    await ElMessageBox.confirm(`归档“${row.serviceName}”后将禁止新调用，确定继续吗？`, '确认归档', { type: 'warning' })
    await archiveFrontendAiService(row.id)
    ElMessage.success('前端 AI 服务已归档')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}

function search() {
  page.value = 1
  void load()
}

onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>前端 AI 服务</h1>
      <p class="page-subtitle">为每个数字人前端创建独立 API Key，并绑定语音识别和图像生成模型</p>
    </div>
    <el-button type="primary" :icon="Plus" @click="openCreate">新建服务</el-button>
  </div>
  <el-alert
    title="前端只需要调用本服务，不会接触百度、火山等供应器密钥。服务 API Key 只在创建或轮换时显示一次。"
    type="info"
    :closable="false"
    show-icon
    style="margin-bottom: 18px"
  />
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 16px">
      <el-input v-model="keyword" clearable placeholder="搜索服务名称或编码" style="width: 280px" @keyup.enter="search" @clear="search" />
      <el-button :icon="Refresh" @click="search">搜索</el-button>
      <span class="page-subtitle">共 {{ total }} 个服务</span>
    </div>
    <el-table v-loading="loading" :data="rows" empty-text="还没有前端 AI 服务">
      <el-table-column prop="serviceName" label="服务名称" min-width="170" />
      <el-table-column prop="serviceCode" label="服务编码" min-width="150"><template #default="{ row }"><code>{{ row.serviceCode }}</code></template></el-table-column>
      <el-table-column label="能力绑定" min-width="250">
        <template #default="{ row }"><div class="binding-cell"><span>语音：{{ row.speechModelName || '未绑定' }}</span><span>图像：{{ row.imageModelName || '未绑定' }}</span></div></template>
      </el-table-column>
      <el-table-column label="API Key" width="150"><template #default="{ row }"><code>{{ row.apiKeyHint }}</code></template></el-table-column>
      <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="260" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button link @click="rotate(row)">轮换 Key</el-button><el-button link type="danger" @click="archive(row)">归档</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" style="margin-top: 18px" @current-change="load" />
  </div>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑前端 AI 服务' : '新建前端 AI 服务'" width="720px">
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item label="服务名称" required><el-input v-model="form.serviceName" maxlength="128" /></el-form-item>
        <el-form-item v-if="editingId" label="服务编码"><el-input :model-value="form.serviceCode" disabled /></el-form-item>
        <el-form-item label="每分钟任务上限"><el-input-number v-model="form.rateLimitPerMinute" :min="1" :max="100000" /></el-form-item>
        <el-form-item label="最大在途任务数"><el-input-number v-model="form.maxInflightTasks" :min="1" :max="10000" /></el-form-item>
      </div>
      <el-form-item label="允许的前端 Origin"><el-input v-model="allowedOriginsText" type="textarea" :rows="2" placeholder="多个 Origin 用逗号分隔；留空表示不限制" /></el-form-item>
      <div class="form-grid">
        <el-form-item label="语音识别模型"><el-select v-model="form.speechModelId" clearable placeholder="不绑定" style="width: 100%"><el-option v-for="item in speechModels" :key="item.id" :label="`${item.modelName}（${item.provider}）`" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="图像生成模型"><el-select v-model="form.imageModelId" clearable placeholder="不绑定" style="width: 100%"><el-option v-for="item in imageModels" :key="item.id" :label="`${item.modelName}（${item.provider}）`" :value="item.id" /></el-select></el-form-item>
      </div>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" maxlength="4000" /></el-form-item>
      <el-form-item label="允许新任务"><el-switch v-model="form.enabled" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
  </el-dialog>
  <ApiKeyRevealDialog v-model="revealVisible" :api-key="revealedKey" />
</template>

<style scoped>
.binding-cell { display: flex; flex-direction: column; gap: 3px; color: #667085; font-size: 12px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
@media (max-width: 720px) { .form-grid { grid-template-columns: 1fr; } }
</style>
