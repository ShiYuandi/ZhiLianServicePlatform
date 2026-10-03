<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createXiaozhiService,
  deleteXiaozhiServiceAsset,
  getXiaozhiService,
  publishXiaozhiService,
  updateXiaozhiService,
  unpublishXiaozhiService,
  uploadXiaozhiServiceAsset,
  XIAOZHI_SERVICE_IMAGE_SLOTS,
  XIAOZHI_SERVICE_VIDEO_SLOTS,
  type XiaozhiServiceAsset,
  type XiaozhiServiceAssetSlot,
  type XiaozhiServiceConfig,
  type XiaozhiServicePayload,
} from '../api/xiaozhiServices'
import { listAiModels, type AiModelListItem } from '../api/aiModels'
import { errorMessage } from '../api/client'
import { listQaTables, type QaTable } from '../api/qa'

const route = useRoute()
const router = useRouter()
const serviceId = computed(() =>
  route.name === 'xiaozhi-service-new' ? null : Number(route.params.id),
)
const loading = ref(false)
const saving = ref(false)
const detail = ref<XiaozhiServiceConfig | null>(null)
const qaTables = ref<QaTable[]>([])
const llmModels = ref<AiModelListItem[]>([])
const form = reactive<XiaozhiServicePayload>({
  serviceCode: undefined,
  serviceName: '',
  digitalHumanName: '',
  title: '',
  subtitle: '',
  questions: [''],
  voiceWakeupEnabled: false,
  wakeWord: '',
  wakeListeningTexts: [''],
  wakeRequirementCount: 0,
  agentName: '',
  agentId: '',
  deviceEnabled: true,
  qaTableId: undefined,
  aiReplyEnabled: true,
  defaultReplyText: '',
  llmModelId: undefined,
})
const assets = computed(
  () => new Map((detail.value?.assets || []).map((asset) => [asset.slot, asset])),
)
const missingHints = computed(() => {
  const missing: string[] = []
  if (!form.serviceName.trim()) missing.push('服务名称')
  if (!form.title.trim()) missing.push('标题')
  if (!form.aiReplyEnabled) {
    if (!form.defaultReplyText?.trim()) missing.push('默认回复词')
  } else if (serviceId.value && !detail.value?.published && !form.llmModelId) {
    missing.push('大语言模型')
  }
  if (!form.agentName.trim() || !/^[0-9a-fA-F]{32}$/.test(form.agentId)) missing.push('设备映射')
  if (form.voiceWakeupEnabled) {
    if (!form.wakeWord?.trim()) missing.push('唤醒词')
    if (!form.wakeListeningTexts.filter((item) => item.trim()).length)
      missing.push('唤醒词监听文字')
  }
  return missing
})

function applyDetail(value: XiaozhiServiceConfig) {
  detail.value = value
  Object.assign(form, {
    serviceCode: value.serviceCode,
    serviceName: value.serviceName,
    digitalHumanName: value.digitalHumanName || '',
    title: value.title,
    subtitle: value.subtitle || '',
    questions: value.questions.length ? [...value.questions] : [''],
    voiceWakeupEnabled: value.voiceWakeupEnabled,
    wakeWord: value.wakeWord || '',
    wakeListeningTexts: value.wakeListeningTexts.length ? [...value.wakeListeningTexts] : [''],
    wakeRequirementCount: value.wakeRequirementCount,
    agentName: value.agentName,
    agentId: value.agentId,
    deviceEnabled: value.deviceEnabled,
    qaTableId: value.qaTableId,
    aiReplyEnabled: value.aiReplyEnabled,
    defaultReplyText: value.defaultReplyText || '',
    llmModelId: value.llmModelId,
  })
}
async function load() {
  if (!serviceId.value) return
  loading.value = true
  try {
    applyDetail(await getXiaozhiService(serviceId.value))
  } catch (error) {
    ElMessage.error(errorMessage(error))
    await router.replace({ name: 'xiaozhi-services' })
  } finally {
    loading.value = false
  }
}
async function loadQaTables() {
  try {
    qaTables.value = (await listQaTables({ page: 1, page_size: 100 })).items
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
async function loadLlmModels() {
  try {
    llmModels.value = (await listAiModels('llm', { page: 1, page_size: 100, enabled: true })).items
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
function addQuestion() {
  form.questions.push('')
}
function removeQuestion(index: number) {
  if (form.questions.length > 1) form.questions.splice(index, 1)
}
function addListeningText() {
  form.wakeListeningTexts.push('')
}
function removeListeningText(index: number) {
  if (form.wakeListeningTexts.length > 1) form.wakeListeningTexts.splice(index, 1)
}
function payload(): XiaozhiServicePayload {
  return {
    ...form,
    serviceName: form.serviceName.trim(),
    title: form.title.trim(),
    subtitle: form.subtitle?.trim(),
    questions: form.questions.map((item) => item.trim()).filter(Boolean),
    wakeWord: form.wakeWord?.trim(),
    wakeListeningTexts: form.wakeListeningTexts.map((item) => item.trim()).filter(Boolean),
    defaultReplyText: form.defaultReplyText?.trim(),
    agentName: form.agentName.trim(),
    agentId: form.agentId.trim().toLowerCase(),
  }
}
function updatePayload(): XiaozhiServicePayload {
  const value = payload()
  delete value.serviceCode
  return value
}
async function save() {
  if (
    !form.serviceName.trim() ||
    !form.title.trim() ||
    !form.agentName.trim() ||
    !/^[0-9a-fA-F]{32}$/.test(form.agentId)
  ) {
    ElMessage.warning('请先填写服务名称、标题、设备名称和合法 agentId')
    return
  }
  saving.value = true
  try {
    const value = serviceId.value
      ? await updateXiaozhiService(serviceId.value, updatePayload())
      : await createXiaozhiService(payload())
    ElMessage.success('小智中间件服务已保存')
    if (!serviceId.value) {
      await router.replace({ name: 'xiaozhi-service-edit', params: { id: value.id } })
    }
    applyDetail(value)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    saving.value = false
  }
}
async function publish() {
  if (!serviceId.value) return
  try {
    applyDetail(await publishXiaozhiService(serviceId.value))
    ElMessage.success('服务已发布')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
async function unpublish() {
  if (!serviceId.value) return
  try {
    applyDetail(await unpublishXiaozhiService(serviceId.value))
    ElMessage.success('服务已停止发布')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
async function upload(slot: XiaozhiServiceAssetSlot, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !serviceId.value) return
  try {
    const result = await uploadXiaozhiServiceAsset(serviceId.value, slot, file)
    if (detail.value)
      detail.value.assets = [
        ...detail.value.assets.filter((item) => item.slot !== slot),
        result.asset,
      ]
    ElMessage.success(result.asset.contentType.startsWith('video/') ? '视频已上传' : '图片已上传')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
async function removeAsset(slot: XiaozhiServiceAssetSlot, asset?: XiaozhiServiceAsset) {
  if (!serviceId.value || !asset) return
  const mediaName = asset.contentType.startsWith('video/') ? '视频' : '图片'
  try {
    await ElMessageBox.confirm(
      `确定删除这个${mediaName}吗？删除后可以随时重新上传。`,
      `确认删除${mediaName}`,
      { type: 'warning' },
    )
    await deleteXiaozhiServiceAsset(serviceId.value, slot)
    if (detail.value) detail.value.assets = detail.value.assets.filter((item) => item.slot !== slot)
    ElMessage.success(`${mediaName}已删除`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}
function back() {
  void router.push({ name: 'xiaozhi-services' })
}
onMounted(load)
onMounted(loadQaTables)
onMounted(loadLlmModels)
</script>

<template>
  <div v-loading="loading">
    <div class="page-header">
      <div>
        <el-button link @click="back">← 返回服务列表</el-button>
        <h1>{{ serviceId ? '编辑小智中间件服务' : '新建小智中间件服务' }}</h1>
        <p class="page-subtitle">先保存草稿，配置完整后再发布给前端使用</p>
      </div>
      <div class="toolbar">
        <el-tag v-if="detail" :type="detail.published ? 'success' : 'info'">{{
          detail.published ? '已发布' : '草稿'
        }}</el-tag>
        <el-button v-if="detail?.published" @click="unpublish">停止发布</el-button>
        <el-button
          v-else-if="serviceId"
          type="success"
          :disabled="missingHints.length > 0"
          @click="publish"
          >发布服务</el-button
        >
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
      </div>
    </div>

    <el-alert
      v-if="serviceId && missingHints.length"
      type="warning"
      :closable="false"
      style="margin-bottom: 18px"
    >
      <template #title>还缺少：{{ missingHints.join('、') }}</template>
    </el-alert>

    <div class="service-editor-grid">
      <div class="panel">
        <h2>基础信息</h2>
        <el-form label-position="top">
          <el-form-item label="服务标识">
            <el-input :model-value="form.serviceCode || '保存后由系统自动生成'" disabled />
          </el-form-item>
          <el-form-item label="前端显示名称" required
            ><el-input v-model="form.serviceName" maxlength="128"
          /></el-form-item>
          <el-form-item label="数字人名称"
            ><el-input v-model="form.digitalHumanName" maxlength="128" placeholder="可选"
          /></el-form-item>
          <el-form-item label="标题" required
            ><el-input v-model="form.title" maxlength="255"
          /></el-form-item>
          <el-form-item label="副标题"
            ><el-input v-model="form.subtitle" maxlength="255"
          /></el-form-item>
        </el-form>
      </div>

      <div class="panel">
        <h2>固定问答</h2>
        <p class="page-subtitle">
          绑定后优先匹配固定答案（支持高相似度模糊匹配，一字反转语义的问题不会错配）；{{
            form.aiReplyEnabled
              ? '未命中或未绑定问答表时调用外部大模型。'
              : '未命中或未绑定问答表时返回默认回复词。'
          }}
        </p>
        <el-form label-position="top">
          <el-form-item label="绑定问答表">
            <el-select
              v-model="form.qaTableId"
              clearable
              filterable
              placeholder="可选；未绑定时直接调用大语言模型"
              style="width: 100%"
            >
              <el-option
                v-for="table in qaTables"
                :key="table.id"
                :label="`${table.name}（${table.item_count} 条）`"
                :value="table.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <div class="panel">
        <h2>大语言模型</h2>
        <p class="page-subtitle">
          {{
            form.aiReplyEnabled
              ? '固定问答未命中时，使用此服务绑定的大语言模型。'
              : '已关闭真实大模型，未命中固定问答时返回下方默认回复词。'
          }}
        </p>
        <el-form label-position="top">
          <el-form-item label="未命中问答表时调用真实大模型">
            <el-switch v-model="form.aiReplyEnabled" />
          </el-form-item>
          <el-form-item v-if="!form.aiReplyEnabled" label="默认回复词" required>
            <el-input
              v-model="form.defaultReplyText"
              maxlength="255"
              placeholder="固定问答未命中时返回的回复"
            />
          </el-form-item>
          <el-form-item v-if="form.aiReplyEnabled" label="绑定模型" required>
            <el-select
              v-model="form.llmModelId"
              clearable
              filterable
              placeholder="草稿可暂不绑定"
              style="width: 100%"
            >
              <el-option
                v-for="model in llmModels"
                :key="model.id"
                :label="`${model.modelName}（${model.provider === 'dify' ? 'Dify' : 'OpenAI 兼容'}）`"
                :value="model.id"
              />
            </el-select>
          </el-form-item>
          <el-alert
            v-if="form.aiReplyEnabled"
            type="info"
            :closable="false"
            title="模型地址和密钥请在“AI 能力管理 → 大语言模型”中统一维护。"
          />
        </el-form>
      </div>

      <div class="panel">
        <h2>设备与智能体</h2>
        <p class="page-subtitle">设备映射已整合到服务中，设备添加代理会使用这里的配置。</p>
        <el-form label-position="top">
          <el-form-item label="设备名称 / agentName" required
            ><el-input v-model="form.agentName" maxlength="128"
          /></el-form-item>
          <el-form-item label="agentId" required
            ><el-input v-model="form.agentId" maxlength="32" placeholder="32 位十六进制字符串"
          /></el-form-item>
          <el-form-item label="启用设备映射"
            ><el-switch v-model="form.deviceEnabled"
          /></el-form-item>
        </el-form>
      </div>

      <div class="panel">
        <h2>推荐问题</h2>
        <div v-for="(_, index) in form.questions" :key="`question-${index}`" class="array-row">
          <el-input v-model="form.questions[index]" :placeholder="`推荐问题 ${index + 1}`" />
          <el-button
            link
            type="danger"
            :disabled="form.questions.length === 1"
            @click="removeQuestion(index)"
            >删除</el-button
          >
        </div>
        <el-button link type="primary" @click="addQuestion">+ 添加问题</el-button>
      </div>

      <div class="panel">
        <h2>语音唤醒</h2>
        <el-form label-position="top">
          <el-form-item label="启用语音唤醒"
            ><el-switch v-model="form.voiceWakeupEnabled"
          /></el-form-item>
          <el-form-item label="唤醒词"
            ><el-input v-model="form.wakeWord" maxlength="255"
          /></el-form-item>
          <el-form-item label="唤醒需求数量"
            ><el-input-number v-model="form.wakeRequirementCount" :min="0"
          /></el-form-item>
        </el-form>
        <p class="form-label">唤醒词监听文字</p>
        <div
          v-for="(_, index) in form.wakeListeningTexts"
          :key="`listen-${index}`"
          class="array-row"
        >
          <el-input
            v-model="form.wakeListeningTexts[index]"
            :placeholder="`监听文字 ${index + 1}`"
          />
          <el-button
            link
            type="danger"
            :disabled="form.wakeListeningTexts.length === 1"
            @click="removeListeningText(index)"
            >删除</el-button
          >
        </div>
        <el-button link type="primary" @click="addListeningText">+ 添加监听文字</el-button>
      </div>
    </div>

    <div class="panel asset-panel">
      <div class="page-header asset-header">
        <div>
          <h2>服务图片</h2>
          <p class="page-subtitle">选填；支持 PNG、JPEG、WebP，单张最大 10 MiB</p>
        </div>
      </div>
      <div class="asset-grid">
        <div v-for="slot in XIAOZHI_SERVICE_IMAGE_SLOTS" :key="slot.key" class="asset-card">
          <div class="asset-preview">
            <img v-if="assets.get(slot.key)" :src="assets.get(slot.key)?.url" :alt="slot.label" />
            <span v-else>未上传</span>
          </div>
          <strong>{{ slot.label }}</strong>
          <small v-if="assets.get(slot.key)">{{ assets.get(slot.key)?.originalFilename }}</small>
          <div class="toolbar asset-actions">
            <label class="el-button el-button--small el-button--primary">
              {{ assets.get(slot.key) ? '替换' : '上传' }}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                hidden
                @change="upload(slot.key, $event)"
              />
            </label>
            <el-button
              v-if="assets.get(slot.key)"
              size="small"
              type="danger"
              link
              @click="removeAsset(slot.key, assets.get(slot.key))"
              >删除</el-button
            >
          </div>
        </div>
      </div>
    </div>

    <div class="panel asset-panel">
      <div class="page-header asset-header">
        <div>
          <h2>服务视频</h2>
          <p class="page-subtitle">选填；支持 MP4、WebM、MOV，单个最大 200 MiB</p>
        </div>
      </div>
      <div class="asset-grid video-grid">
        <div v-for="slot in XIAOZHI_SERVICE_VIDEO_SLOTS" :key="slot.key" class="asset-card">
          <div class="asset-preview video-preview">
            <video
              v-if="assets.get(slot.key)"
              :src="assets.get(slot.key)?.url"
              :aria-label="slot.label"
              controls
              preload="metadata"
            />
            <span v-else>未上传</span>
          </div>
          <strong>{{ slot.label }}</strong>
          <small v-if="assets.get(slot.key)">{{ assets.get(slot.key)?.originalFilename }}</small>
          <div class="toolbar asset-actions">
            <label class="el-button el-button--small el-button--primary">
              {{ assets.get(slot.key) ? '替换' : '上传' }}
              <input
                type="file"
                accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov"
                hidden
                @change="upload(slot.key, $event)"
              />
            </label>
            <el-button
              v-if="assets.get(slot.key)"
              size="small"
              type="danger"
              link
              @click="removeAsset(slot.key, assets.get(slot.key))"
              >删除</el-button
            >
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
