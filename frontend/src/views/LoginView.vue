<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Connection, Lock, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login } from '../api/auth'
import { errorMessage } from '../api/client'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const route = useRoute()
const router = useRouter()

async function submit() {
  if (!form.username || !form.password) return ElMessage.warning('请输入账号和密码')
  loading.value = true
  try {
    await login(form.username, form.password)
    const target = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(target)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="brand-panel">
      <div class="brand-heading">
        <span class="logo">智</span>
        <span><strong>智联服务台</strong><small>AI SERVICE CONSOLE</small></span>
      </div>
      <div class="brand-content">
        <span class="brand-badge">数字人 AI 服务管理平台</span>
        <h1>让数字人服务配置<br />更清晰、更稳定</h1>
        <p>统一管理小智中间件、AI 模型能力与固定问答，让不同前端项目拥有清晰可靠的服务配置。</p>
        <div class="feature-list">
          <div>
            <el-icon><Connection /></el-icon><span>小智中间件集中配置</span>
          </div>
          <div>
            <el-icon><MagicStick /></el-icon><span>多供应器 AI 能力管理</span>
          </div>
          <div>
            <el-icon><Lock /></el-icon><span>敏感凭据安全保存</span>
          </div>
        </div>
      </div>
          <small class="copyright">智联服务台</small>
    </section>

    <main class="form-panel">
      <div class="login-card">
        <span class="mobile-logo">智</span>
        <div class="welcome">欢迎回来</div>
        <h2>登录管理控制台</h2>
        <p>请输入管理员账号和密码继续</p>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item label="管理员账号">
            <el-input
              v-model="form.username"
              size="large"
              autocomplete="username"
              placeholder="请输入管理员账号"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              show-password
              autocomplete="current-password"
              placeholder="请输入登录密码"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-button"
            @click="submit"
          >
            登录
          </el-button>
        </el-form>
        <div class="security-note"><span></span>管理员专用安全入口</div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(420px, 0.9fr) minmax(520px, 1.1fr);
  background: white;
}
.brand-panel {
  position: relative;
  display: flex;
  min-height: 100vh;
  padding: 38px 48px;
  flex-direction: column;
  overflow: hidden;
  color: white;
  background: #0b1f3a;
}
.brand-panel::before,
.brand-panel::after {
  position: absolute;
  pointer-events: none;
  content: '';
  border-radius: 50%;
}
.brand-panel::before {
  top: -120px;
  right: -100px;
  width: 420px;
  height: 420px;
  background: rgba(37, 99, 235, 0.25);
  filter: blur(20px);
}
.brand-panel::after {
  right: -180px;
  bottom: -230px;
  width: 540px;
  height: 540px;
  border: 1px solid rgba(96, 165, 250, 0.13);
  box-shadow:
    0 0 0 70px rgba(96, 165, 250, 0.035),
    0 0 0 140px rgba(96, 165, 250, 0.025);
}
.brand-heading {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  align-items: center;
}
.logo,
.mobile-logo {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  color: white;
  background: #2563eb;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 13px;
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.3);
  font-size: 21px;
  font-weight: 750;
}
.brand-heading > span:last-child {
  display: flex;
  flex-direction: column;
}
.brand-heading strong {
  font-size: 17px;
  letter-spacing: 0.04em;
}
.brand-heading small {
  margin-top: 3px;
  color: #7f93ac;
  font-size: 9px;
  letter-spacing: 0.12em;
}
.brand-content {
  position: relative;
  z-index: 1;
  width: min(500px, 100%);
  margin: auto 0;
}
.brand-badge {
  display: inline-flex;
  padding: 7px 12px;
  color: #bfdbfe;
  background: rgba(37, 99, 235, 0.17);
  border: 1px solid rgba(96, 165, 250, 0.18);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.brand-content h1 {
  margin: 25px 0 18px;
  font-size: clamp(34px, 4vw, 50px);
  font-weight: 700;
  line-height: 1.22;
  letter-spacing: -0.04em;
}
.brand-content > p {
  max-width: 480px;
  margin: 0;
  color: #aebdd0;
  font-size: 15px;
  line-height: 1.8;
}
.feature-list {
  display: grid;
  margin-top: 34px;
  gap: 14px;
}
.feature-list > div {
  display: flex;
  gap: 12px;
  align-items: center;
  color: #d4deea;
  font-size: 14px;
}
.feature-list .el-icon {
  width: 32px;
  height: 32px;
  color: #93c5fd;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 9px;
}
.copyright {
  position: relative;
  z-index: 1;
  color: #526982;
  font-size: 10px;
  letter-spacing: 0.12em;
}
.form-panel {
  display: grid;
  min-height: 100vh;
  padding: 40px;
  place-items: center;
  background: #f8fafc;
}
.login-card {
  width: min(430px, 100%);
  padding: 42px;
  background: white;
  border: 1px solid #eef1f6;
  border-radius: 20px;
  box-shadow: 0 24px 70px rgba(16, 24, 40, 0.08);
}
.mobile-logo {
  display: none;
}
.welcome {
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 650;
}
.login-card h2 {
  margin: 0;
  color: #101828;
  font-size: 28px;
  letter-spacing: -0.03em;
}
.login-card > p {
  margin: 10px 0 30px;
  color: #667085;
  font-size: 14px;
}
.submit-button {
  width: 100%;
  height: 44px;
  margin-top: 6px;
}
.security-note {
  display: flex;
  margin-top: 22px;
  gap: 8px;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
  font-size: 12px;
}
.security-note span {
  width: 6px;
  height: 6px;
  background: #12a36d;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(18, 163, 109, 0.1);
}
@media (max-width: 920px) {
  .login-page {
    grid-template-columns: 1fr;
  }
  .brand-panel {
    display: none;
  }
  .form-panel {
    padding: 24px;
    background: #f5f7fb;
  }
  .mobile-logo {
    display: grid;
    margin-bottom: 28px;
  }
}
@media (max-width: 520px) {
  .form-panel {
    padding: 16px;
  }
  .login-card {
    padding: 28px 22px;
    border-radius: 16px;
  }
  .login-card h2 {
    font-size: 24px;
  }
}
</style>
