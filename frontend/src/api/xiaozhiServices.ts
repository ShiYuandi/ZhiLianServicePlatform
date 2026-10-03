import { api } from './client'

export const XIAOZHI_SERVICE_IMAGE_SLOTS = [
  { key: 'background_icon', label: '背景图标' },
  { key: 'wake_icon', label: '唤醒图标' },
  { key: 'menu_background', label: '菜单栏背景' },
  { key: 'keyboard_icon', label: '键盘图标' },
  { key: 'voice_icon', label: '语音图标' },
  { key: 'home_icon', label: '首页图标' },
  { key: 'hold_to_talk_background', label: '长按说话背景图标' },
  { key: 'send_icon', label: '点击发送图标' },
] as const

export const XIAOZHI_SERVICE_VIDEO_SLOTS = [
  { key: 'standing_video', label: '站立视频' },
  { key: 'thinking_video', label: '思考视频' },
  { key: 'speaking_video', label: '说话视频' },
] as const

export const XIAOZHI_SERVICE_ASSET_SLOTS = [
  ...XIAOZHI_SERVICE_IMAGE_SLOTS,
  ...XIAOZHI_SERVICE_VIDEO_SLOTS,
] as const

export type XiaozhiServiceAssetSlot = (typeof XIAOZHI_SERVICE_ASSET_SLOTS)[number]['key']

export interface XiaozhiServiceAsset {
  id: number
  slot: XiaozhiServiceAssetSlot
  originalFilename: string
  contentType: string
  sizeBytes: number
  etag: string
  url: string
}

export interface XiaozhiServiceListItem {
  id: number
  serviceCode: string
  serviceName: string
  digitalHumanName?: string
  agentName: string
  agentId: string
  deviceEnabled: boolean
  published: boolean
  completeness: number
  updatedAt: string
  qaTableId?: number
  qaTableName?: string
  aiReplyEnabled: boolean
  defaultReplyText?: string
  llmModelId?: number
  llmModelName?: string
  llmProvider?: string
  llmConfigured: boolean
}

export interface XiaozhiServiceConfig extends XiaozhiServiceListItem {
  title: string
  subtitle?: string
  questions: string[]
  voiceWakeupEnabled: boolean
  wakeWord?: string
  wakeListeningTexts: string[]
  wakeRequirementCount: number
  llmEnabled?: boolean
  assets: XiaozhiServiceAsset[]
  createdAt: string
}

export interface XiaozhiServicePayload {
  serviceCode?: string
  serviceName: string
  digitalHumanName?: string
  title: string
  subtitle?: string
  questions: string[]
  voiceWakeupEnabled: boolean
  wakeWord?: string
  wakeListeningTexts: string[]
  wakeRequirementCount: number
  agentName: string
  agentId: string
  deviceEnabled: boolean
  qaTableId?: number
  aiReplyEnabled: boolean
  defaultReplyText?: string
  llmModelId?: number
}

interface Page<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

export async function listXiaozhiServices(params: Record<string, unknown>) {
  return (await api.get<Page<XiaozhiServiceListItem>>('/api/admin/xiaozhi-services', { params }))
    .data
}
export async function getXiaozhiService(id: number) {
  return (await api.get<XiaozhiServiceConfig>(`/api/admin/xiaozhi-services/${id}`)).data
}
export async function createXiaozhiService(data: XiaozhiServicePayload) {
  return (await api.post<XiaozhiServiceConfig>('/api/admin/xiaozhi-services', data)).data
}
export async function updateXiaozhiService(id: number, data: XiaozhiServicePayload) {
  return (await api.put<XiaozhiServiceConfig>(`/api/admin/xiaozhi-services/${id}`, data)).data
}
export async function deleteXiaozhiService(id: number) {
  return api.delete(`/api/admin/xiaozhi-services/${id}`)
}
export async function publishXiaozhiService(id: number) {
  return (await api.post<XiaozhiServiceConfig>(`/api/admin/xiaozhi-services/${id}/publish`)).data
}
export async function unpublishXiaozhiService(id: number) {
  return (await api.post<XiaozhiServiceConfig>(`/api/admin/xiaozhi-services/${id}/unpublish`)).data
}
export async function uploadXiaozhiServiceAsset(
  id: number,
  slot: XiaozhiServiceAssetSlot,
  file: File,
) {
  const form = new FormData()
  form.append('file', file)
  return (
    await api.post<{ asset: XiaozhiServiceAsset }>(
      `/api/admin/xiaozhi-services/${id}/assets/${slot}`,
      form,
    )
  ).data
}
export async function deleteXiaozhiServiceAsset(id: number, slot: XiaozhiServiceAssetSlot) {
  return api.delete(`/api/admin/xiaozhi-services/${id}/assets/${slot}`)
}
