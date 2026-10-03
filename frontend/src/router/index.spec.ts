import { describe, expect, it } from 'vitest'
import router from './index'

describe('后台路由', () => {
  it('只保留新的小智服务和 AI 模型入口', () => {
    const paths = router.getRoutes().map((route) => route.path)

    expect(paths).toContain('/xiaozhi-services')
    expect(paths).toContain('/ai-models/llm')
    expect(paths).toContain('/ai-models/speech-recognition')
    expect(paths).toContain('/ai-models/image-generation')
    expect(paths).not.toContain('/projects')
    expect(paths.every((path) => !path.startsWith('/projects/'))).toBe(true)
  })
})
