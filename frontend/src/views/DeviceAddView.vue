<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Refresh } from '@element-plus/icons-vue'
import { addDevice, type DeviceAddPayload } from '../api/device'
import { listXiaozhiServices, type XiaozhiServiceListItem } from '../api/xiaozhiServices'
import { errorMessage } from '../api/client'

const services = ref<XiaozhiServiceListItem[]>([])
const loading = ref(false)
const submitting = ref(false)
const selectedServiceId = ref<number>()
const result = ref('')
const form = reactive<DeviceAddPayload>({
  name: '',
  board: 'esp32',
  appVersion: '1.0.0',
  macAddress: '',
})

const selectedService = computed(() => services.value.find((item) => item.id === selectedServiceId.value))
const apiUrl = computed(() => `${window.location.origin}/api/device/add`)

async function loadServices() {
  loading.value = true
  try {
    services.value = (await listXiaozhiServices({ page: 1, page_size: 100 })).items
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function selectService(id?: number) {
  selectedServiceId.value = id
  const service = services.value.find((item) => item.id === id)
  if (service) form.name = service.agentName
}

function resetResult() {
  result.value = ''
}

async function submit() {
  const payload = {
    name: form.name.trim(),
    board: form.board.trim(),
    appVersion: form.appVersion.trim(),
    macAddress: form.macAddress.trim(),
  }
  if (!selectedService.value) {
    ElMessage.warning('请先选择要绑定的服务')
    return
  }
  if (selectedService.value.agentName.trim().toLocaleLowerCase() !== payload.name.toLocaleLowerCase()) {
    ElMessage.warning('设备名称必须与所选服务的设备名称一致')
    return
  }
  if (Object.values(payload).some((value) => !value)) {
    ElMessage.warning('请完整填写设备名称、主板型号、应用版本和 MAC 地址')
    return
  }
  submitting.value = true
  resetResult()
  try {
    result.value = JSON.stringify(await addDevice(payload), null, 2)
    ElMessage.success('设备添加请求已成功返回')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function copyApiUrl() {
  try {
    await navigator.clipboard.writeText(apiUrl.value)
    ElMessage.success('设备添加 API 地址已复制')
  } catch {
    ElMessage.warning('浏览器禁止访问剪贴板，请手动复制 API 地址')
  }
}

onMounted(loadServices)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>设备添加</h1>
      <p class="page-subtitle">通过小智设备添加代理，将新设备绑定到已配置的数字人智能体。</p>
    </div>
    <el-button :icon="Refresh" :loading="loading" @click="loadServices">刷新服务</el-button>
  </div>

  <div class="device-add-grid">
    <div class="panel">
      <h2>添加设备</h2>
      <el-alert
        title="设备名称必须与服务中的设备名称 / agentName 一致，匹配时忽略前后空格和大小写。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 18px"
      />
      <el-form label-position="top">
        <el-form-item label="绑定服务" required>
          <el-select
            :model-value="selectedServiceId"
            clearable
            filterable
            placeholder="选择小智中间件服务"
            style="width: 100%"
            @update:model-value="selectService"
          >
            <el-option
              v-for="service in services"
              :key="service.id"
              :label="`${service.serviceName}（设备：${service.agentName}）`"
              :value="service.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="设备名称" required>
          <el-input v-model="form.name" placeholder="自动带入所选服务的设备名称" />
        </el-form-item>
        <el-form-item label="主板型号" required>
          <el-input v-model="form.board" placeholder="例如：esp32" />
        </el-form-item>
        <el-form-item label="应用版本" required>
          <el-input v-model="form.appVersion" placeholder="例如：1.0.0" />
        </el-form-item>
        <el-form-item label="MAC 地址" required>
          <el-input v-model="form.macAddress" placeholder="例如：00:11:22:33:44:55" />
        </el-form-item>
      </el-form>
      <el-button type="primary" :loading="submitting" @click="submit">添加设备</el-button>
      <pre v-if="result" class="api-result">{{ result }}</pre>
    </div>

    <div class="panel api-panel">
      <div class="api-panel-header">
        <h2>API 调用提示</h2>
        <el-button link type="primary" :icon="CopyDocument" @click="copyApiUrl">复制地址</el-button>
      </div>
      <p class="page-subtitle">数字人前端也可以直接调用此接口，不需要接触小智平台 Token。</p>
      <div class="api-url"><code>{{ apiUrl }}</code></div>
      <p class="api-method"><el-tag size="small">POST</el-tag> <code>Content-Type: application/json</code></p>
      <pre class="api-example">{{ `{
  "name": "设备名称",
  "board": "esp32",
  "appVersion": "1.0.0",
  "macAddress": "00:11:22:33:44:55"
}` }}</pre>
      <el-divider />
      <p class="page-subtitle api-note">
        成功时返回小智平台的设备添加结果；设备名称没有启用映射、小智平台拒绝或请求超时时，会返回中文错误提示。
      </p>
    </div>
  </div>
</template>

<style scoped>
.device-add-grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr); gap: 18px; }
.api-panel-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.api-url { padding: 10px 12px; background: var(--el-fill-color-light); border-radius: 6px; overflow-x: auto; }
.api-url code { white-space: nowrap; }
.api-method { display: flex; align-items: center; gap: 8px; margin: 14px 0 8px; }
.api-example, .api-result { margin: 10px 0 0; padding: 12px; background: #0f172a; color: #dbeafe; border-radius: 6px; overflow-x: auto; font: 13px/1.6 ui-monospace, SFMono-Regular, Consolas, monospace; }
.api-note { margin-bottom: 0; }
@media (max-width: 900px) { .device-add-grid { grid-template-columns: 1fr; } }
</style>
