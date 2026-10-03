<script setup lang="ts">
import AiModelManagementView from './AiModelManagementView.vue'
</script>
<template>
  <AiModelManagementView
    capability="llm"
    title="大语言模型"
    description="集中维护 OpenAI 和 Dify 模型，供小智中间件服务绑定"
  />
</template>
