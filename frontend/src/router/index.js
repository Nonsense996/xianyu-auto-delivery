import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'accounts', component: () => import('../views/Accounts.vue'), meta: { title: '鱼店管理' } },
      { path: 'products', component: () => import('../views/Products.vue'), meta: { title: '商品与卡密' } },
      { path: 'orders', component: () => import('../views/Orders.vue'), meta: { title: '订单/发货记录' } },
      { path: 'rules', component: () => import('../views/Rules.vue'), meta: { title: '自动回复' } },
      { path: 'logs', component: () => import('../views/Logs.vue'), meta: { title: '运行日志' } },
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(to => {
  if (to.path !== '/login' && !localStorage.getItem('token')) return '/login'
  return true
})

export default router
