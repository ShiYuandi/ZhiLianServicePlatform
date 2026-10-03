import { config, shallowMount } from '@vue/test-utils'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import AiModelManagementView from './AiModelManagementView.vue'

vi.mock('../api/aiModels', () => ({
  archiveAiModel: vi.fn(),
  createAiModel: vi.fn(),
  getAiModel: vi.fn(),
  listAiModels: vi.fn().mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0 }),
  setAiModelStatus: vi.fn(),
  testAiModelConnection: vi.fn(),
  updateAiModel: vi.fn(),
}))

beforeAll(() => {
  config.global.renderStubDefaultSlot = true
})

function mountView(capability: 'llm' | 'speech-recognition' | 'image-generation') {
  return shallowMount(AiModelManagementView, {
    props: {
      capability,
      title: '模型管理',
      description: '测试说明',
    },
    global: {
      stubs: {
        ElAlert: {
          name: 'ElAlert',
          props: ['title'],
          template: '<div>{{ title }}<slot /></div>',
        },
        ElFormItem: {
          name: 'ElFormItem',
          props: ['label'],
          template: '<label>{{ label }}<slot /></label>',
        },
        ElInput: {
          name: 'ElInput',
          props: ['placeholder'],
          template: '<input :placeholder="placeholder" />',
        },
        ElTableColumn: { template: '<div />' },
      },
    },
  })
}

async function changeProvider(
  wrapper: ReturnType<typeof mountView>,
  provider: 'dify' | 'volcengine',
) {
  ;(
    wrapper.vm as unknown as {
      form: { provider: 'openai' | 'dify' | 'baidu' | 'volcengine' }
    }
  ).form.provider = provider
  await wrapper.vm.$nextTick()
}

describe('AI 模型管理', () => {
  it('大语言模型可在 OpenAI 与 Dify 字段之间切换', async () => {
    const wrapper = mountView('llm')

    expect(wrapper.text()).toContain('上游模型名称')
    expect(wrapper.text()).not.toContain('Dify 应用模式')

    await changeProvider(wrapper, 'dify')

    expect(wrapper.text()).toContain('Dify 应用模式')
    expect(wrapper.text()).not.toContain('上游模型名称')
  })

  it('语音识别模型可在百度与火山字段之间切换', async () => {
    const wrapper = mountView('speech-recognition')

    expect(wrapper.text()).toContain('Secret Key')
    expect(wrapper.text()).not.toContain('Access Token')

    await changeProvider(wrapper, 'volcengine')

    expect(wrapper.text()).toContain('Access Token')
    expect(wrapper.text()).toContain('资源 ID')
    expect(wrapper.text()).not.toContain('Secret Key')
  })

  it('图像生成模型显示 Seedream 调用参数', () => {
    const wrapper = mountView('image-generation')

    expect(wrapper.text()).toContain('Seedream 实际模型 ID')
    expect(wrapper.text()).toContain('默认宽度')
    expect(wrapper.text()).toContain('添加水印')
  })

  it('供应器编码统一转换为中文名称', () => {
    const wrapper = mountView('speech-recognition')
    const view = wrapper.vm as unknown as {
      providerLabel: (provider: 'baidu' | 'volcengine') => string
    }

    expect(view.providerLabel('baidu')).toBe('百度智能云')
    expect(view.providerLabel('volcengine')).toBe('火山引擎')
  })

  it('密钥输入提示编辑时留空保持原值', async () => {
    const models = await import('../api/aiModels')
    vi.mocked(models.getAiModel).mockResolvedValueOnce({
      id: 1,
      modelName: '展厅模型',
      modelCode: 'hall-model',
      provider: 'openai',
      sortOrder: 0,
      enabled: true,
      updatedAt: '2026-08-27T00:00:00Z',
      createdAt: '2026-08-27T00:00:00Z',
      credentialConfigured: true,
      apiKeyMasked: 'sk-****1234',
      baseUrl: 'https://example.com/v1',
      upstreamModel: 'example-model',
    })
    const wrapper = mountView('llm')

    await (wrapper.vm as unknown as { openEdit: (row: object) => Promise<void> }).openEdit({
      id: 1,
    })
    await wrapper.vm.$nextTick()

    const placeholders = wrapper
      .findAllComponents({ name: 'ElInput' })
      .map((input) => String(input.props('placeholder') || ''))
    expect(placeholders.some((value) => value.includes('留空保持原值'))).toBe(true)
  })
})
