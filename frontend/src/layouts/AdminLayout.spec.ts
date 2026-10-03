import { shallowMount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'
import layoutSource from './AdminLayout.vue?raw'
import AdminLayout from './AdminLayout.vue'

vi.mock('../api/auth', () => ({ logout: vi.fn() }))

async function mountLayout(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/',
        component: { template: '<div />' },
        children: [
          { path: 'ai-models/llm', name: 'llm-models', component: { template: '<div />' } },
        ],
      },
    ],
  })
  await router.push(path)
  await router.isReady()
  return shallowMount(AdminLayout, {
    global: {
      plugins: [router],
      stubs: {
        ElMenu: {
          props: ['defaultActive'],
          template: '<nav :data-active="defaultActive"><slot /></nav>',
        },
        ElMenuItem: {
          props: ['index'],
          template:
            '<div class="menu-item" :data-index="index"><slot /><slot name="title" /></div>',
        },
        ElSubMenu: {
          props: ['index'],
          template:
            '<section class="sub-menu" :data-index="index"><slot name="title" /><slot /></section>',
        },
        ElIcon: { template: '<i><slot /></i>' },
        ElDropdown: { template: '<div><slot /><slot name="dropdown" /></div>' },
        ElDropdownMenu: { template: '<div><slot /></div>' },
        ElDropdownItem: { template: '<div><slot /></div>' },
        RouterView: { template: '<div />' },
      },
    },
  })
}

describe('后台导航', () => {
  it('按当前 AI 模型路由设置菜单选中项', async () => {
    const wrapper = await mountLayout('/ai-models/llm')

    expect(wrapper.find('nav').attributes('data-active')).toBe('/ai-models/llm')
    expect(wrapper.find('[data-index="/ai-models/llm"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('大语言模型')
  })

  it('AI 子菜单使用深色背景并为选中项提供高亮条', () => {
    expect(layoutSource).toContain('background: rgba(2, 12, 27, 0.28) !important')
    expect(layoutSource).toContain('.el-menu-item.is-active::before')
    expect(layoutSource).toContain('popper-class="sidebar-model-popper"')
    expect(layoutSource).not.toContain('background: white')
  })
})
