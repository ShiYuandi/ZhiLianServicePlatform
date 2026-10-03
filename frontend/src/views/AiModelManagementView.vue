<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ModelInfoFields from '../components/ModelInfoFields.vue'
import {
  archiveAiModel,
  createAiModel,
  getAiModel,
  listAiModels,
  setAiModelStatus,
  testAiModelConnection,
  updateAiModel,
  type AiModelDetail,
  type AiModelListItem,
  type AiModelPayload,
  type ModelCapability,
  type ModelProvider,
} from '../api/aiModels'
import { errorMessage } from '../api/client'

const props = defineProps<{
  capability: ModelCapability
  title: string
  description: string
}>()

const rows = ref<AiModelListItem[]>([])
const total = ref(0)
const page = ref(1)
const keyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const detail = ref<AiModelDetail | null>(null)
const pageSize = 20

const providerLabels: Record<ModelProvider, string> = {
  openai: 'OpenAI 兼容接口',
  dify: 'Dify',
  baidu: '百度智能云',
  volcengine: '火山引擎',
}

function providerLabel(provider: ModelProvider) {
  return providerLabels[provider]
}

const providerOptions = computed<Array<{ label: string; value: ModelProvider }>>(() => {
  if (props.capability === 'llm') {
    return [
      { label: 'OpenAI 兼容接口', value: 'openai' },
      { label: 'Dify', value: 'dify' },
    ]
  }
  if (props.capability === 'speech-recognition') {
    return [
      { label: '百度智能云', value: 'baidu' },
      { label: '火山引擎', value: 'volcengine' },
    ]
  }
  return [{ label: '火山引擎 Seedream', value: 'volcengine' }]
})

function defaultForm(): AiModelPayload {
  const provider = providerOptions.value[0].value
  return {
    modelName: '',
    modelCode: undefined,
    provider,
    sortOrder: 0,
    docUrl: '',
    remark: '',
    enabled: true,
    timeoutSeconds: props.capability === 'image-generation' ? 120 : 30,
    mode: 'chat-messages',
    devPid: 1537,
    language: 'zh-CN',
    apiUrl: 'https://ark.cn-beijing.volces.com/api/v3/images/generations',
    upstreamModel:
      props.capability === 'image-generation' ? 'doubao-seedream-4-0-250828' : undefined,
    defaultWidth: 932,
    defaultHeight: 582,
    watermark: false,
  }
}

const form = reactive<AiModelPayload>(defaultForm())

async function load() {
  loading.value = true
  try {
    const data = await listAiModels(props.capability, {
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

function openCreate() {
  editingId.value = null
  detail.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

async function openEdit(row: AiModelListItem) {
  try {
    const value = await getAiModel(props.capability, row.id)
    detail.value = value
    editingId.value = row.id
    Object.assign(form, defaultForm(), value, {
      apiKey: '',
      secretKey: '',
      accessToken: '',
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function commonPayload() {
  return {
    modelName: form.modelName.trim(),
    ...(form.modelCode?.trim() ? { modelCode: form.modelCode.trim() } : {}),
    provider: form.provider,
    sortOrder: form.sortOrder,
    docUrl: form.docUrl?.trim() || undefined,
    remark: form.remark?.trim() || undefined,
    enabled: form.enabled,
  }
}

function payload(): AiModelPayload {
  const common = commonPayload()
  if (props.capability === 'llm' && form.provider === 'openai') {
    return {
      ...common,
      provider: 'openai',
      baseUrl: form.baseUrl?.trim() || undefined,
      upstreamModel: form.upstreamModel?.trim() || undefined,
      apiKey: form.apiKey?.trim() || undefined,
      timeoutSeconds: form.timeoutSeconds || 30,
    }
  }
  if (props.capability === 'llm') {
    return {
      ...common,
      provider: 'dify',
      baseUrl: form.baseUrl?.trim() || undefined,
      mode: form.mode || 'chat-messages',
      apiKey: form.apiKey?.trim() || undefined,
      timeoutSeconds: form.timeoutSeconds || 30,
    }
  }
  if (props.capability === 'speech-recognition' && form.provider === 'baidu') {
    return {
      ...common,
      provider: 'baidu',
      appId: form.appId?.trim() || undefined,
      apiKey: form.apiKey?.trim() || undefined,
      secretKey: form.secretKey?.trim() || undefined,
      devPid: form.devPid || 1537,
    }
  }
  if (props.capability === 'speech-recognition') {
    return {
      ...common,
      provider: 'volcengine',
      appId: form.appId?.trim() || undefined,
      accessToken: form.accessToken?.trim() || undefined,
      resourceId: form.resourceId?.trim() || undefined,
      language: form.language?.trim() || undefined,
      boostingTableName: form.boostingTableName?.trim() || undefined,
      correctTableName: form.correctTableName?.trim() || undefined,
    }
  }
  return {
    ...common,
    provider: 'volcengine',
    apiUrl: form.apiUrl?.trim(),
    apiKey: form.apiKey?.trim() || undefined,
    upstreamModel: form.upstreamModel?.trim() || undefined,
    defaultWidth: form.defaultWidth || 932,
    defaultHeight: form.defaultHeight || 582,
    timeoutSeconds: form.timeoutSeconds || 120,
    watermark: form.watermark || false,
  }
}

async function save() {
  if (!form.modelName.trim()) {
    ElMessage.warning('请填写模型名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) await updateAiModel(props.capability, editingId.value, payload())
    else await createAiModel(props.capability, payload())
    ElMessage.success(editingId.value ? '模型已更新' : '模型已创建')
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    saving.value = false
  }
}

async function toggle(row: AiModelListItem) {
  try {
    const result = await setAiModelStatus(props.capability, row.id, !row.enabled)
    ElMessage.success(
      result.affectedServiceCount
        ? `${result.message}，影响 ${result.affectedServiceCount} 个服务`
        : result.message,
    )
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function archive(row: AiModelListItem) {
  try {
    await ElMessageBox.confirm(`归档“${row.modelName}”后将不再出现在模型列表中。`, '确认归档', {
      type: 'warning',
      confirmButtonText: '归档',
      cancelButtonText: '取消',
    })
    await archiveAiModel(props.capability, row.id)
    ElMessage.success('模型已归档')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}

async function testConnection() {
  if (!editingId.value) return
  try {
    await testAiModelConnection(props.capability, editingId.value)
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.warning(errorMessage(error))
  }
}

onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>{{ title }}</h1>
      <p class="page-subtitle">{{ description }}</p>
    </div>
    <el-button type="primary" @click="openCreate">新增模型</el-button>
  </div>
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 16px">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索模型名称或编码"
        style="width: 280px"
        @keyup.enter="load"
        @clear="load"
      />
      <el-button @click="load">搜索</el-button>
      <span class="page-subtitle">共 {{ total }} 个模型</span>
    </div>
    <el-table v-loading="loading" :data="rows" empty-text="还没有模型配置">
      <el-table-column prop="modelName" label="模型名称" min-width="180" />
      <el-table-column label="供应器" width="150">
        <template #default="{ row }">{{ providerLabel(row.provider) }}</template>
      </el-table-column>
      <el-table-column prop="sortOrder" label="排序" width="80" />
      <el-table-column label="状态" width="100"
        ><template #default="{ row }"
          ><el-tag :type="row.enabled ? 'success' : 'info'">{{
            row.enabled ? '已启用' : '已停用'
          }}</el-tag></template
        ></el-table-column
      >
      <el-table-column label="操作" width="260" fixed="right"
        ><template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link @click="toggle(row)">{{ row.enabled ? '停用' : '启用' }}</el-button>
          <el-button link type="danger" @click="archive(row)">归档</el-button>
        </template></el-table-column
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

  <el-dialog
    v-model="dialogVisible"
    :title="editingId ? `编辑${title}` : `新增${title}`"
    width="760px"
    destroy-on-close
  >
    <el-form label-position="top">
      <ModelInfoFields :model-value="form" :providers="providerOptions" />
      <el-divider content-position="left">调用信息</el-divider>

      <template v-if="capability === 'llm'">
        <el-form-item label="基础 URL" required
          ><el-input v-model="form.baseUrl" placeholder="https://.../v1"
        /></el-form-item>
        <el-form-item v-if="form.provider === 'openai'" label="上游模型名称" required
          ><el-input v-model="form.upstreamModel"
        /></el-form-item>
        <el-form-item v-else label="Dify 应用模式" required
          ><el-select v-model="form.mode" style="width: 100%"
            ><el-option label="对话（chat-messages）" value="chat-messages" /><el-option
              label="工作流（workflows/run）"
              value="workflows/run" /></el-select
        ></el-form-item>
        <el-form-item label="API Key"
          ><el-input
            v-model="form.apiKey"
            type="password"
            show-password
            :placeholder="
              detail?.credentialConfigured
                ? `已配置：${detail.apiKeyMasked || '********'}；留空保持原值`
                : '请输入 API Key'
            "
        /></el-form-item>
        <el-form-item label="请求超时（秒）"
          ><el-input-number v-model="form.timeoutSeconds" :min="1" :max="600"
        /></el-form-item>
      </template>

      <template v-else-if="capability === 'speech-recognition' && form.provider === 'baidu'">
        <el-form-item label="AppID"><el-input v-model="form.appId" /></el-form-item>
        <el-form-item label="API Key"
          ><el-input
            v-model="form.apiKey"
            type="password"
            show-password
            :placeholder="
              detail?.apiKeyMasked ? `已配置：${detail.apiKeyMasked}；留空保持原值` : ''
            "
        /></el-form-item>
        <el-form-item label="Secret Key"
          ><el-input
            v-model="form.secretKey"
            type="password"
            show-password
            :placeholder="
              detail?.secretKeyMasked ? `已配置：${detail.secretKeyMasked}；留空保持原值` : ''
            "
        /></el-form-item>
        <el-form-item label="语言模型编号"
          ><el-input-number v-model="form.devPid" :min="1"
        /></el-form-item>
      </template>

      <template v-else-if="capability === 'speech-recognition'">
        <el-form-item label="AppID"><el-input v-model="form.appId" /></el-form-item>
        <el-form-item label="Access Token"
          ><el-input
            v-model="form.accessToken"
            type="password"
            show-password
            :placeholder="
              detail?.accessTokenMasked ? `已配置：${detail.accessTokenMasked}；留空保持原值` : ''
            "
        /></el-form-item>
        <el-form-item label="资源 ID"><el-input v-model="form.resourceId" /></el-form-item>
        <el-form-item label="语言"
          ><el-input v-model="form.language" placeholder="zh-CN"
        /></el-form-item>
        <el-form-item label="热词表名称"
          ><el-input v-model="form.boostingTableName"
        /></el-form-item>
        <el-form-item label="纠错表名称"><el-input v-model="form.correctTableName" /></el-form-item>
      </template>

      <template v-else>
        <el-form-item label="API 地址" required><el-input v-model="form.apiUrl" /></el-form-item>
        <el-form-item label="API Key"
          ><el-input
            v-model="form.apiKey"
            type="password"
            show-password
            :placeholder="
              detail?.apiKeyMasked ? `已配置：${detail.apiKeyMasked}；留空保持原值` : ''
            "
        /></el-form-item>
        <el-form-item label="Seedream 实际模型 ID" required
          ><el-input v-model="form.upstreamModel"
        /></el-form-item>
        <div class="form-inline">
          <el-form-item label="默认宽度"
            ><el-input-number v-model="form.defaultWidth" :min="256" :max="4096" /></el-form-item
          ><el-form-item label="默认高度"
            ><el-input-number v-model="form.defaultHeight" :min="256" :max="4096" /></el-form-item
          ><el-form-item label="超时秒数"
            ><el-input-number v-model="form.timeoutSeconds" :min="1" :max="900"
          /></el-form-item>
        </div>
        <el-form-item label="添加水印"><el-switch v-model="form.watermark" /></el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button v-if="editingId" @click="testConnection">测试连接</el-button>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.form-inline {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 720px) {
  .form-inline {
    grid-template-columns: 1fr;
  }
}
</style>
