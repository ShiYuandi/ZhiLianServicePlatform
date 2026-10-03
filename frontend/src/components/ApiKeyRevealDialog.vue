<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

defineProps<{ modelValue: boolean; apiKey: string; title?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const copied = ref(false)

async function copyKey(key: string) {
  try {
    await navigator.clipboard.writeText(key)
    copied.value = true
    ElMessage.success('API Key 已复制，请妥善保存')
    window.setTimeout(() => (copied.value = false), 1600)
  } catch {
    ElMessage.warning('浏览器禁止访问剪贴板，请手动复制')
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title || '保存服务 API Key'"
    width="560px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-alert
      title="完整 API Key 只显示这一次，关闭后无法再次查看。请立即复制并保存到前端服务的安全配置中。"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 18px"
    />
    <el-input :model-value="apiKey" readonly>
      <template #append><el-button @click="copyKey(apiKey)">{{ copied ? '已复制' : '复制' }}</el-button></template>
    </el-input>
    <template #footer><el-button type="primary" @click="emit('update:modelValue', false)">我已保存</el-button></template>
  </el-dialog>
</template>
