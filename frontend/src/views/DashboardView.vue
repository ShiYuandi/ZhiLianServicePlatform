<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Connection, DataLine, Document, Files, Link, SuccessFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDashboard, type DashboardStats } from '../api/dashboard'
import { errorMessage } from '../api/client'

const stats = ref<DashboardStats>({
  qaTableCount: 0,
  qaItemCount: 0,
  deviceMappingCount: 0,
  database: 'checking',
})
const loading = ref(true)
onMounted(async () => {
  try {
    stats.value = await getDashboard()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-header">
    <div>
      <h1>概览</h1>
      <p class="page-subtitle">统一查看小智中间件、AI 模型、问答知识库与前端 AI 服务的配置状态</p>
    </div>
    <div class="live-badge"><span></span>服务状态实时更新</div>
  </div>
  <div v-loading="loading" class="stats-grid">
    <div class="stat-card">
      <span class="stat-icon blue"><Files /></span>
      <div class="stat-content">
        <span>问答表</span>
        <div>
          <strong>{{ stats.qaTableCount }}</strong
          ><small>张</small>
        </div>
      </div>
      <span class="stat-foot">固定问答知识集合</span>
    </div>
    <div class="stat-card">
      <span class="stat-icon cyan"><Document /></span>
      <div class="stat-content">
        <span>问答数据</span>
        <div>
          <strong>{{ stats.qaItemCount }}</strong
          ><small>条</small>
        </div>
      </div>
      <span class="stat-foot">已维护的问题与答案</span>
    </div>
    <div class="stat-card">
      <span class="stat-icon violet"><Connection /></span>
      <div class="stat-content">
        <span>设备映射</span>
        <div>
          <strong>{{ stats.deviceMappingCount }}</strong
          ><small>个</small>
        </div>
      </div>
      <span class="stat-foot">已配置的小智设备</span>
    </div>
    <div class="stat-card">
      <span :class="['stat-icon', stats.database === 'ok' ? 'green' : 'red']">
        <SuccessFilled v-if="stats.database === 'ok'" />
        <DataLine v-else />
      </span>
      <div class="stat-content">
        <span>数据库连接</span>
        <div>
          <strong class="status" :class="{ error: stats.database !== 'ok' }">{{
            stats.database === 'ok' ? '正常' : '异常'
          }}</strong>
        </div>
      </div>
      <span class="stat-foot">MySQL 持久化存储</span>
    </div>
  </div>
  <div class="panel api-panel">
    <div class="api-icon"><Link /></div>
    <div class="api-content">
      <h3>智联服务台能力概览</h3>
      <p class="page-subtitle">
        平台统一管理小智设备接入与问答路由，并维护大语言模型、语音识别和图像生成模型。
        前端通过服务编码调用已配置的能力，模型密钥由平台安全保管，业务数据持久化存储于 MySQL。
      </p>
    </div>
    <div class="api-routes">
      <code>设备添加：POST /api/device/add</code>
      <code>小智问答：POST /v1/chat/completions</code>
      <code>前端配置：/api/xiaozhi-services/config?serviceName=...</code>
    </div>
  </div>
</template>

<style scoped>
.live-badge {
  display: inline-flex;
  padding: 7px 11px;
  gap: 8px;
  align-items: center;
  color: #47637c;
  background: white;
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  box-shadow: var(--shadow-card);
  font-size: 12px;
}
.live-badge span {
  width: 7px;
  height: 7px;
  background: #12a36d;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(18, 163, 109, 0.1);
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}
.stat-card {
  position: relative;
  display: grid;
  min-height: 176px;
  padding: 21px;
  grid-template-columns: 44px 1fr;
  grid-template-rows: 1fr auto;
  gap: 0 14px;
  overflow: hidden;
  background: white;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}
.stat-card:hover {
  border-color: #dbe5f4;
  box-shadow: 0 12px 30px rgba(16, 24, 40, 0.07);
  transform: translateY(-2px);
}
.stat-card::after {
  position: absolute;
  top: -28px;
  right: -28px;
  width: 90px;
  height: 90px;
  content: '';
  background: #f5f8ff;
  border-radius: 50%;
}
.stat-icon {
  z-index: 1;
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 12px;
  font-size: 21px;
}
.stat-icon.blue {
  color: #2563eb;
  background: #eaf2ff;
}
.stat-icon.cyan {
  color: #0891b2;
  background: #e6f8fc;
}
.stat-icon.violet {
  color: #7c3aed;
  background: #f1eafe;
}
.stat-icon.green {
  color: #079669;
  background: #e7f8f1;
}
.stat-icon.red {
  color: #dc2626;
  background: #fef2f2;
}
.stat-icon svg,
.api-icon svg {
  width: 1em;
  height: 1em;
}
.stat-content {
  z-index: 1;
  display: flex;
  flex-direction: column;
}
.stat-content > span {
  color: #667085;
  font-size: 13px;
  font-weight: 500;
}
.stat-content > div {
  display: flex;
  margin-top: 9px;
  gap: 6px;
  align-items: baseline;
}
.stat-content strong {
  color: #101828;
  font-size: 31px;
  font-weight: 700;
  letter-spacing: -0.04em;
}
.stat-content small {
  color: #98a2b3;
}
.stat-content .status {
  color: #079669;
  font-size: 24px;
}
.stat-content .status.error {
  color: #dc2626;
}
.stat-foot {
  grid-column: 1 / -1;
  padding-top: 17px;
  color: #98a2b3;
  border-top: 1px solid #f0f2f5;
  font-size: 12px;
}
.api-panel {
  display: flex;
  gap: 16px;
  align-items: center;
}
.api-icon {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  place-items: center;
  color: #2563eb;
  background: #eaf2ff;
  border-radius: 12px;
  font-size: 20px;
}
.api-content {
  min-width: 0;
  flex: 1;
}
.api-content h3 {
  margin-bottom: 2px;
}
.api-content p {
  margin-top: 0;
}
.api-panel code {
  padding: 9px 12px;
  white-space: nowrap;
}
.api-routes {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 7px;
  align-items: flex-end;
}
@media (max-width: 1100px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 720px) {
  .live-badge {
    display: none;
  }
  .api-panel {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .api-panel code {
    width: 100%;
    overflow: auto;
  }
  .api-routes {
    width: 100%;
    align-items: stretch;
  }
}
@media (max-width: 500px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
