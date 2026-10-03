import { config, shallowMount } from '@vue/test-utils'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import XiaozhiServiceEditorView from './XiaozhiServiceEditorView.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'xiaozhi-service-new', params: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('../api/qa', () => ({
  listQaTables: vi.fn().mockResolvedValue({ items: [], page: 1, pageSize: 100, total: 0 }),
}))

vi.mock('../api/aiModels', () => ({
  listAiModels: vi.fn().mockResolvedValue({ items: [], page: 1, pageSize: 100, total: 0 }),
}))

vi.mock('../api/xiaozhiServices', () => ({
  XIAOZHI_SERVICE_IMAGE_SLOTS: [
    { key: 'background_icon', label: '背景图标' },
    { key: 'wake_icon', label: '唤醒图标' },
  ],
  XIAOZHI_SERVICE_VIDEO_SLOTS: [
    { key: 'standing_video', label: '站立视频' },
    { key: 'thinking_video', label: '思考视频' },
    { key: 'speaking_video', label: '说话视频' },
  ],
  createXiaozhiService: vi.fn(),
  deleteXiaozhiServiceAsset: vi.fn(),
  getXiaozhiService: vi.fn(),
  publishXiaozhiService: vi.fn(),
  unpublishXiaozhiService: vi.fn(),
  updateXiaozhiService: vi.fn(),
  uploadXiaozhiServiceAsset: vi.fn(),
}))

beforeAll(() => {
  config.global.renderStubDefaultSlot = true
})

describe('小智中间件服务编辑器', () => {
  function mountEditor() {
    return shallowMount(XiaozhiServiceEditorView, {
      global: {
        stubs: {
          ElAlert: {
            props: ['title'],
            template: '<div>{{ title }}<slot /></div>',
          },
          ElFormItem: {
            props: ['label'],
            template: '<label>{{ label }}<slot /></label>',
          },
        },
      },
    })
  }

  it('只绑定独立大语言模型，不直接维护模型连接凭据', () => {
    const wrapper = mountEditor()
    const text = wrapper.text()

    expect(text).toContain('绑定模型')
    expect(text).toContain('AI 能力管理 → 大语言模型')
    expect(text).not.toContain('API 密钥')
    expect(text).not.toContain('基础 URL')
    expect(text).not.toContain('供应器')
  })

  it('关闭真实大模型后改为填写默认回复词', async () => {
    const wrapper = mountEditor()
    expect(wrapper.text()).toContain('绑定模型')

    await wrapper.findComponent({ name: 'ElSwitch' }).vm.$emit('update:modelValue', false)
    await nextTick()

    expect(wrapper.text()).toContain('默认回复词')
    expect(wrapper.text()).not.toContain('绑定模型')
  })

  it('页面使用小智中间件服务文案', () => {
    const wrapper = mountEditor()

    expect(wrapper.text()).toContain('新建小智中间件服务')
    expect(wrapper.text()).toContain('服务标识')
    expect(wrapper.text()).not.toContain('数字人项目')
    expect(wrapper.classes()).not.toContain('project-editor-grid')
  })

  it('图片和视频均为选填并提供三个视频槽位', () => {
    const wrapper = mountEditor()
    const text = wrapper.text()

    expect(text).toContain('服务图片')
    expect(text).toContain('服务视频')
    expect(text).toContain('站立视频')
    expect(text).toContain('思考视频')
    expect(text).toContain('说话视频')
    expect(text).toContain('选填')
  })
})
