import { api } from './client'

export type ModelCapability = 'llm' | 'speech-recognition' | 'image-generation'
export type ModelProvider = 'openai' | 'dify' | 'baidu' | 'volcengine'

export interface AiModelListItem {
  id: number
  modelName: string
  modelCode: string
  provider: ModelProvider
  sortOrder: number
  enabled: boolean
  updatedAt: string
}

export interface AiModelDetail extends AiModelListItem {
  docUrl?: string
  remark?: string
  credentialConfigured: boolean
  createdAt: string
  baseUrl?: string
  upstreamModel?: string
  apiKeyMasked?: string
  timeoutSeconds?: number
  mode?: 'chat-messages' | 'workflows/run'
  appId?: string
  secretKeyMasked?: string
  accessTokenMasked?: string
  resourceId?: string
  language?: string
  boostingTableName?: string
  correctTableName?: string
  devPid?: number
  apiUrl?: string
  defaultWidth?: number
  defaultHeight?: number
  watermark?: boolean
}

export interface AiModelPayload {
  modelName: string
  modelCode?: string
  provider: ModelProvider
  sortOrder: number
  docUrl?: string
  remark?: string
  enabled: boolean
  baseUrl?: string
  upstreamModel?: string
  apiKey?: string
  timeoutSeconds?: number
  mode?: 'chat-messages' | 'workflows/run'
  appId?: string
  secretKey?: string
  accessToken?: string
  resourceId?: string
  language?: string
  boostingTableName?: string
  correctTableName?: string
  devPid?: number
  apiUrl?: string
  defaultWidth?: number
  defaultHeight?: number
  watermark?: boolean
}

interface Page<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

const paths: Record<ModelCapability, string> = {
  llm: '/api/admin/ai-models/llm',
  'speech-recognition': '/api/admin/ai-models/speech-recognition',
  'image-generation': '/api/admin/ai-models/image-generation',
}

export async function listAiModels(capability: ModelCapability, params: Record<string, unknown>) {
  return (await api.get<Page<AiModelListItem>>(paths[capability], { params })).data
}
export async function getAiModel(capability: ModelCapability, id: number) {
  return (await api.get<AiModelDetail>(`${paths[capability]}/${id}`)).data
}
export async function createAiModel(capability: ModelCapability, data: AiModelPayload) {
  return (await api.post<AiModelDetail>(paths[capability], data)).data
}
export async function updateAiModel(capability: ModelCapability, id: number, data: AiModelPayload) {
  return (await api.put<AiModelDetail>(`${paths[capability]}/${id}`, data)).data
}
export async function setAiModelStatus(capability: ModelCapability, id: number, enabled: boolean) {
  return (
    await api.put<{ message: string; affectedServiceCount: number }>(
      `${paths[capability]}/${id}/status`,
      { enabled },
    )
  ).data
}
export async function archiveAiModel(capability: ModelCapability, id: number) {
  return api.delete(`${paths[capability]}/${id}`)
}
export async function testAiModelConnection(capability: ModelCapability, id: number) {
  return api.post(`${paths[capability]}/${id}/test-connection`)
}
