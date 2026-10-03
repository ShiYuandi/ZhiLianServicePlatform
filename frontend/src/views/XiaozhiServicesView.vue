<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteXiaozhiService,
  listXiaozhiServices,
  publishXiaozhiService,
  unpublishXiaozhiService,
  type XiaozhiServiceListItem,
} from '../api/xiaozhiServices'
import { errorMessage } from '../api/client'

const router = useRouter()
const rows = ref<XiaozhiServiceListItem[]>([])
const total = ref(0)
const page = ref(1)
const keyword = ref('')
const loading = ref(false)
const pageSize = 20

async function load() {
  loading.value = true
  try {
    const data = await listXiaozhiServices({
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
function search() {
  page.value = 1
  void load()
}
async function changePublish(row: XiaozhiServiceListItem) {
  try {
    if (row.published) await unpublishXiaozhiService(row.id)
    else await publishXiaozhiService(row.id)
    ElMessage.success(row.published ? '已停止发布' : '已发布')
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
async function remove(row: XiaozhiServiceListItem) {
  try {
    await ElMessageBox.confirm(
      `删除“${row.serviceName}”会同时删除设备映射和全部图片、视频，且不可恢复。`,
      '确认删除服务',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteXiaozhiService(row.id)
    ElMessage.success('小智中间件服务、设备映射和媒体已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}
onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>小智中间件服务</h1>
      <p class="page-subtitle">维护数字人页面、设备智能体、问答表和大语言模型绑定</p>
    </div>
    <el-button type="primary" @click="router.push({ name: 'xiaozhi-service-new' })"
      >新建服务</el-button
    >
  </div>
  <div class="panel">
    <div class="toolbar" style="margin-bottom: 16px">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索服务编码或名称"
        style="width: 280px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button @click="search">搜索</el-button>
      <span class="page-subtitle">共 {{ total }} 个服务</span>
    </div>
    <el-table v-loading="loading" :data="rows" empty-text="还没有小智中间件服务">
      <el-table-column prop="serviceName" label="服务名称" min-width="170" />
      <el-table-column prop="serviceCode" label="服务编码" min-width="150">
        <template #default="{ row }"
          ><code>{{ row.serviceCode }}</code></template
        >
      </el-table-column>
      <el-table-column prop="agentName" label="设备名称" min-width="150" />
      <el-table-column label="配置完整度" width="140">
        <template #default="{ row }"
          ><el-progress :percentage="row.completeness" :stroke-width="8"
        /></template>
      </el-table-column>
      <el-table-column label="状态" width="150">
        <template #default="{ row }">
          <el-tag :type="row.published ? 'success' : 'info'">{{
            row.published ? '已发布' : '草稿'
          }}</el-tag>
          <el-tag :type="row.deviceEnabled ? 'success' : 'warning'" style="margin-left: 6px">{{
            row.deviceEnabled ? '设备启用' : '设备停用'
          }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="router.push({ name: 'xiaozhi-service-edit', params: { id: row.id } })"
            >编辑</el-button
          >
          <el-button link @click="changePublish(row)">{{
            row.published ? '停止发布' : '发布'
          }}</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
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
</template>
