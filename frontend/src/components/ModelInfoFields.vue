<script setup lang="ts">
import type { AiModelPayload, ModelProvider } from '../api/aiModels'

defineProps<{
  providers: Array<{ label: string; value: ModelProvider }>
  providerDisabled?: boolean
}>()

const model = defineModel<AiModelPayload>({ required: true })
</script>

<template>
  <el-divider content-position="left">模型信息</el-divider>
  <div class="form-grid">
    <el-form-item label="模型名称" required>
      <el-input v-model="model.modelName" maxlength="128" />
    </el-form-item>
    <el-form-item label="供应器" required>
      <el-select v-model="model.provider" :disabled="providerDisabled" style="width: 100%">
        <el-option
          v-for="item in providers"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
    </el-form-item>
    <el-form-item label="排序号">
      <el-input-number v-model="model.sortOrder" :min="-9999" :max="9999" />
    </el-form-item>
    <el-form-item label="文档地址">
      <el-input v-model="model.docUrl" maxlength="512" placeholder="https://..." />
    </el-form-item>
    <el-form-item label="启用模型">
      <el-switch v-model="model.enabled" />
    </el-form-item>
  </div>
  <el-form-item label="备注">
    <el-input v-model="model.remark" type="textarea" :rows="2" maxlength="4000" />
  </el-form-item>
</template>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}
@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
