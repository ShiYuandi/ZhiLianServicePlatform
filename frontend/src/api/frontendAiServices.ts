import { api } from './client'

export interface FrontendAiService {
  id: number
  serviceName: string
  serviceCode: string
  enabled: boolean
  remark?: string
  apiKeyHint: string
  apiKeyVersion: number
  rateLimitPerMinute: number
  maxInflightTasks: number
  allowedOrigins: string[]
  speechModelId?: number
  speechModelName?: string
  speechProvider?: string
  imageModelId?: number
  imageModelName?: string
  imageProvider?: string
  createdAt: string
  updatedAt: string
}

export interface FrontendAiServicePayload {
  serviceName: string
  serviceCode?: string
  enabled: boolean
  remark?: string
  rateLimitPerMinute: number
  maxInflightTasks: number
  allowedOrigins: string[]
  speechModelId?: number
  imageModelId?: number
}

export interface FrontendAiServiceCreated extends FrontendAiService {
  apiKey: string
}

interface Page<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

const path = '/api/admin/frontend-ai-services'

export async function listFrontendAiServices(params: Record<string, unknown>) {
  return (await api.get<Page<FrontendAiService>>(path, { params })).data
}

export async function getFrontendAiService(id: number) {
  return (await api.get<FrontendAiService>(`${path}/${id}`)).data
}

export async function createFrontendAiService(data: FrontendAiServicePayload) {
  return (await api.post<FrontendAiServiceCreated>(path, data)).data
}

export async function updateFrontendAiService(id: number, data: FrontendAiServicePayload) {
  return (await api.put<FrontendAiService>(`${path}/${id}`, data)).data
}

export async function rotateFrontendAiServiceKey(id: number) {
  return (
    await api.post<{ apiKey: string; apiKeyHint: string; apiKeyVersion: number }>(
      `${path}/${id}/rotate-api-key`,
    )
  ).data
}

export async function archiveFrontendAiService(id: number) {
  return api.delete(`${path}/${id}`)
}
