import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'pets',
        name: 'Pets',
        component: () => import('../views/Pets.vue'),
        meta: { title: '宠物管理' },
      },
      {
        path: 'medical',
        name: 'Medical',
        component: () => import('../views/Medical.vue'),
        meta: { title: '诊疗记录' },
      },
      {
        path: 'vaccines',
        name: 'Vaccines',
        component: () => import('../views/Vaccines.vue'),
        meta: { title: '疫苗接种' },
      },
      {
        path: 'drugs',
        name: 'Drugs',
        component: () => import('../views/Drugs.vue'),
        meta: { title: '药品库存' },
      },
      {
        path: 'staff',
        name: 'Staff',
        component: () => import('../views/Staff.vue'),
        meta: { title: '员工管理', admin: true },
      },
      {
        path: 'ai',
        name: 'AI',
        component: () => import('../views/AI.vue'),
        meta: { title: 'AI 工作台' },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/Knowledge.vue'),
        meta: { title: '知识库' },
      },
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('../views/Calendar.vue'),
        meta: { title: '日程日历' },
      },
      {
        path: 'soap/:id?',
        name: 'SOAP',
        component: () => import('../views/SOAPCase.vue'),
        meta: { title: 'SOAP 病历' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.guest && token) {
    return next('/dashboard')
  }

  if (!to.meta.guest && !token) {
    return next('/login')
  }

  if (to.meta.admin) {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (user && user.role !== 'admin') {
      return next('/dashboard')
    }
  }

  next()
})

export default router
