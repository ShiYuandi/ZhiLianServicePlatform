<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ChatDotRound,
  Connection,
  DataAnalysis,
  Document,
  Expand,
  Fold,
  Cpu,
  MagicStick,
  Microphone,
  Picture,
  Setting,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { logout } from '../api/auth'

const collapsed = ref(false)
const narrowScreen = ref(false)
const route = useRoute()
const router = useRouter()

const menuCollapsed = computed(() => collapsed.value || narrowScreen.value)
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    dashboard: '数据概览',
    'xiaozhi-services': '小智中间件服务',
    'device-add': '设备添加',
    'xiaozhi-service-new': '新建小智中间件服务',
    'xiaozhi-service-edit': '编辑小智中间件服务',
    'llm-models': '大语言模型',
    'speech-recognition-models': '语音识别模型',
    'image-generation-models': '图像生成模型',
    'frontend-ai-services': '前端 AI 服务',
    'external-api-proxies': '外部接口代理',
    'qa-tables': '问答表管理',
    'qa-editor': '问答内容维护',
    settings: '账号设置',
  }
  return titles[String(route.name)] || '数字人 AI 服务管理平台'
})

function updateViewport() {
  narrowScreen.value = window.innerWidth <= 860
}

async function signOut() {
  try {
    await logout()
  } finally {
    ElMessage.success('已退出登录')
    await router.replace({ name: 'login' })
  }
}

onMounted(() => {
  updateViewport()
  window.addEventListener('resize', updateViewport)
})
onBeforeUnmount(() => window.removeEventListener('resize', updateViewport))
</script>

<template>
  <div class="shell">
    <aside :class="['sidebar', { collapsed: menuCollapsed }]">
      <div class="brand">
        <span class="brand-mark">智</span>
        <span v-if="!menuCollapsed" class="brand-copy">
          <strong>智联服务台</strong>
          <small>AI SERVICE CONSOLE</small>
        </span>
      </div>
      <div v-if="!menuCollapsed" class="menu-caption">工作台</div>
      <el-menu
        :default-active="route.path"
        router
        class="side-menu"
        :collapse="menuCollapsed"
        :collapse-transition="false"
        :default-openeds="['/ai-models']"
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon><template #title>概览</template>
        </el-menu-item>
        <el-menu-item index="/xiaozhi-services">
          <el-icon><Connection /></el-icon><template #title>小智中间件服务</template>
        </el-menu-item>
        <el-menu-item index="/device-add">
          <el-icon><Cpu /></el-icon><template #title>设备添加</template>
        </el-menu-item>
        <el-sub-menu index="/ai-models" popper-class="sidebar-model-popper">
          <template #title>
            <el-icon><MagicStick /></el-icon><span>AI 能力管理</span>
          </template>
          <el-menu-item index="/ai-models/llm">
            <el-icon><ChatDotRound /></el-icon><template #title>大语言模型</template>
          </el-menu-item>
          <el-menu-item index="/ai-models/speech-recognition">
            <el-icon><Microphone /></el-icon><template #title>语音识别模型</template>
          </el-menu-item>
          <el-menu-item index="/ai-models/image-generation">
            <el-icon><Picture /></el-icon><template #title>图像生成模型</template>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/frontend-ai-services">
          <el-icon><Connection /></el-icon><template #title>前端 AI 服务</template>
        </el-menu-item>
        <el-menu-item index="/external-api-proxies">
          <el-icon><Connection /></el-icon><template #title>外部接口代理</template>
        </el-menu-item>
        <el-menu-item index="/qa-tables">
          <el-icon><Document /></el-icon><template #title>问答表管理</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon><template #title>账号设置</template>
        </el-menu-item>
      </el-menu>
      <button
        v-if="!narrowScreen"
        class="collapse-button"
        @click="collapsed = !collapsed"
        :aria-label="collapsed ? '展开导航' : '收起导航'"
      >
        <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
        <span v-if="!collapsed">收起导航</span>
      </button>
    </aside>
    <section class="main-area">
      <header class="topbar">
        <div>
          <span class="topbar-eyebrow">管理控制台</span>
          <div class="topbar-title">{{ pageTitle }}</div>
        </div>
        <el-dropdown trigger="click" @command="signOut">
          <button class="user-menu" type="button">
            <span class="user-avatar"
              ><el-icon><UserFilled /></el-icon
            ></span>
            <span class="user-info"><strong>管理员</strong><small>系统管理员</small></span>
            <el-icon class="user-arrow"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <main class="content"><router-view /></main>
    </section>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  width: 244px;
  height: 100vh;
  flex: 0 0 auto;
  flex-direction: column;
  overflow: hidden;
  color: white;
  background: #0b1f3a;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: width 0.2s ease;
}
.sidebar::before {
  position: absolute;
  top: -100px;
  left: -60px;
  width: 230px;
  height: 230px;
  pointer-events: none;
  content: '';
  background: rgba(37, 99, 235, 0.16);
  border-radius: 50%;
  filter: blur(70px);
}
.sidebar.collapsed {
  width: 72px;
}
.brand {
  position: relative;
  display: flex;
  height: 76px;
  padding: 0 18px;
  flex: 0 0 auto;
  gap: 11px;
  align-items: center;
  overflow: hidden;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.collapsed .brand {
  padding: 0 16px;
}
.brand-mark {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  color: white;
  background: #2563eb;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 82, 217, 0.3);
  font-size: 20px;
  font-weight: 750;
}
.brand-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  white-space: nowrap;
}
.brand-copy strong {
  font-size: 16px;
  font-weight: 650;
  letter-spacing: 0.04em;
}
.brand-copy small {
  margin-top: 3px;
  color: #8194ac;
  font-size: 9px;
  letter-spacing: 0.12em;
}
.menu-caption {
  padding: 22px 22px 8px;
  color: #60758f;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.12em;
}
.side-menu {
  flex: 1;
  padding: 7px 10px 16px;
  overflow-x: hidden;
  overflow-y: auto;
  background: transparent;
  border-right: 0;
  --el-menu-text-color: #aebdd0;
  --el-menu-hover-text-color: #ffffff;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.07);
  --el-menu-active-color: #ffffff;
  --el-menu-item-height: 46px;
  --el-menu-sub-item-height: 42px;
}
.side-menu::-webkit-scrollbar {
  width: 0;
}
.side-menu :deep(.el-menu) {
  background: rgba(2, 12, 27, 0.28) !important;
  border-radius: 10px;
}
.side-menu :deep(.el-menu-item),
.side-menu :deep(.el-sub-menu__title) {
  position: relative;
  margin: 3px 0;
  border-radius: 9px;
}
.side-menu :deep(.el-menu-item .el-icon),
.side-menu :deep(.el-sub-menu__title .el-icon) {
  font-size: 18px;
}
.side-menu :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  margin: 2px 6px;
  padding-left: 46px !important;
  color: #93a7bf;
  background: transparent;
  border-radius: 8px;
}
.side-menu :deep(.el-sub-menu .el-menu-item .el-icon) {
  position: absolute;
  left: 20px;
  width: 16px;
  font-size: 15px;
}
.side-menu :deep(.el-menu-item:hover),
.side-menu :deep(.el-sub-menu__title:hover) {
  color: white;
  background: rgba(255, 255, 255, 0.07) !important;
}
.side-menu :deep(.el-menu-item.is-active) {
  color: white;
  background: rgba(37, 99, 235, 0.34) !important;
  box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.13);
}
.side-menu :deep(.el-menu-item.is-active::before) {
  position: absolute;
  top: 9px;
  bottom: 9px;
  left: 0;
  width: 3px;
  content: '';
  background: #60a5fa;
  border-radius: 0 4px 4px 0;
}
.side-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #dbeafe;
  background: rgba(255, 255, 255, 0.045);
}
.side-menu.el-menu--collapse {
  width: 52px;
  padding-right: 0;
  padding-left: 0;
  align-self: center;
}
.side-menu.el-menu--collapse :deep(.el-sub-menu__title),
.side-menu.el-menu--collapse :deep(.el-menu-item) {
  padding: 0 16px !important;
}
.collapse-button {
  display: flex;
  height: 50px;
  margin: 0;
  padding: 0 22px;
  flex: 0 0 auto;
  gap: 12px;
  align-items: center;
  color: #8194ac;
  background: rgba(1, 11, 26, 0.25);
  border: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  cursor: pointer;
  transition:
    color 0.18s ease,
    background 0.18s ease;
}
.collapse-button:hover {
  color: white;
  background: rgba(255, 255, 255, 0.06);
}
.collapsed .collapse-button {
  justify-content: center;
  padding: 0;
}
.main-area {
  min-width: 0;
  flex: 1;
}
.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  height: 76px;
  padding: 0 30px;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid var(--color-border-light);
  backdrop-filter: blur(12px);
}
.topbar-eyebrow {
  display: block;
  margin-bottom: 3px;
  color: #98a2b3;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.topbar-title {
  color: #182230;
  font-size: 16px;
  font-weight: 650;
}
.user-menu {
  display: flex;
  padding: 5px 7px 5px 6px;
  gap: 9px;
  align-items: center;
  color: #344054;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
}
.user-menu:hover {
  background: #f8fafc;
  border-color: var(--color-border-light);
}
.user-avatar {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: #2563eb;
  background: #eaf2ff;
  border-radius: 9px;
}
.user-info {
  display: flex;
  min-width: 72px;
  flex-direction: column;
  align-items: flex-start;
}
.user-info strong {
  font-size: 13px;
  font-weight: 600;
}
.user-info small {
  margin-top: 2px;
  color: #98a2b3;
  font-size: 11px;
}
.user-arrow {
  color: #98a2b3;
  font-size: 12px;
}
.content {
  width: 100%;
  max-width: 1480px;
  min-height: calc(100vh - 76px);
  padding: 28px 30px 42px;
  margin: 0 auto;
}
@media (max-width: 860px) {
  .sidebar,
  .sidebar.collapsed {
    width: 64px;
  }
  .brand {
    height: 68px;
    padding: 0 12px;
  }
  .brand-mark {
    width: 40px;
  }
  .topbar {
    height: 68px;
    padding: 0 18px;
  }
  .content {
    min-height: calc(100vh - 68px);
    padding: 22px 18px 36px;
  }
}
@media (max-width: 560px) {
  .sidebar,
  .sidebar.collapsed {
    width: 56px;
  }
  .brand {
    padding: 0 8px;
  }
  .brand-mark {
    width: 40px;
    height: 40px;
  }
  .side-menu.el-menu--collapse {
    width: 48px;
  }
  .side-menu.el-menu--collapse :deep(.el-sub-menu__title),
  .side-menu.el-menu--collapse :deep(.el-menu-item) {
    padding: 0 14px !important;
  }
  .topbar-eyebrow,
  .user-info,
  .user-arrow {
    display: none;
  }
  .topbar {
    padding: 0 12px;
  }
  .topbar-title {
    max-width: 190px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .content {
    padding: 18px 10px 30px;
  }
}
</style>
