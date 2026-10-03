<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '../api/auth'
import { errorMessage } from '../api/client'

const router = useRouter(),
  loading = ref(false)
const form = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
async function submit() {
  if (form.newPassword.length < 10) return ElMessage.warning('新密码至少 10 个字符')
  if (form.newPassword !== form.confirmPassword) return ElMessage.warning('两次新密码不一致')
  loading.value = true
  try {
    await changePassword(form.currentPassword, form.newPassword)
    ElMessage.success('密码已修改，请重新登录')
    await router.replace({ name: 'login' })
  } catch (e) {
    ElMessage.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-header">
    <div>
      <h1>账号设置</h1>
      <p class="page-subtitle">修改唯一管理员账号的登录密码</p>
    </div>
  </div>
  <div class="panel settings">
    <el-alert
      title="修改后所有已登录会话会立即失效"
      type="info"
      :closable="false"
      style="margin-bottom: 22px"
    /><el-form label-position="top"
      ><el-form-item label="当前密码"
        ><el-input
          v-model="form.currentPassword"
          type="password"
          show-password
          autocomplete="current-password" /></el-form-item
      ><el-form-item label="新密码"
        ><el-input
          v-model="form.newPassword"
          type="password"
          show-password
          autocomplete="new-password" /></el-form-item
      ><el-form-item label="确认新密码"
        ><el-input
          v-model="form.confirmPassword"
          type="password"
          show-password
          autocomplete="new-password"
          @keyup.enter="submit" /></el-form-item
      ><el-button type="primary" :loading="loading" @click="submit">修改密码</el-button></el-form
    >
  </div>
</template>
<style scoped>
.settings {
  max-width: 620px;
}
</style>
