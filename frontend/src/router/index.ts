import { createRouter, createWebHistory } from 'vue-router'
import { currentAdmin } from '../api/auth'

const router = createRouter({
  history: createWebHistory('/admin'),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('../layouts/AdminLayout.vue'),
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
        {
          path: 'qa-tables',
          name: 'qa-tables',
          component: () => import('../views/QaTablesView.vue'),
        },
        {
          path: 'qa-tables/:id',
          name: 'qa-editor',
          component: () => import('../views/QaEditorView.vue'),
        },
        {
          path: 'xiaozhi-services',
          name: 'xiaozhi-services',
          component: () => import('../views/XiaozhiServicesView.vue'),
        },
        {
          path: 'device-add',
          name: 'device-add',
          component: () => import('../views/DeviceAddView.vue'),
        },
        {
          path: 'xiaozhi-services/new',
          name: 'xiaozhi-service-new',
          component: () => import('../views/XiaozhiServiceEditorView.vue'),
        },
        {
          path: 'xiaozhi-services/:id',
          name: 'xiaozhi-service-edit',
          component: () => import('../views/XiaozhiServiceEditorView.vue'),
        },
        {
          path: 'ai-models/llm',
          name: 'llm-models',
          component: () => import('../views/LlmModelsView.vue'),
        },
        {
          path: 'ai-models/speech-recognition',
          name: 'speech-recognition-models',
          component: () => import('../views/SpeechModelsView.vue'),
        },
        {
          path: 'ai-models/image-generation',
          name: 'image-generation-models',
          component: () => import('../views/ImageModelsView.vue'),
        },
        {
          path: 'frontend-ai-services',
          name: 'frontend-ai-services',
          component: () => import('../views/FrontendAiServicesView.vue'),
        },
        {
          path: 'external-api-proxies',
          name: 'external-api-proxies',
          component: () => import('../views/ExternalApiProxiesView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/AccountSettingsView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  try {
    await currentAdmin()
    return true
  } catch {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
