import { createRouter, createWebHistory } from 'vue-router'

import { logado } from '../stores/auth'

// Telas carregadas sob demanda (cada uma vira um arquivo JS separado no build)
const routes = [
  { path: '/', redirect: '/caronas' },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { publica: true } },
  { path: '/cadastro', name: 'cadastro', component: () => import('../views/CadastroView.vue'), meta: { publica: true } },
  { path: '/caronas', name: 'buscar', component: () => import('../views/BuscarView.vue') },
  { path: '/caronas/nova', name: 'oferecer', component: () => import('../views/CaronaFormView.vue') },
  { path: '/caronas/:id/editar', name: 'editar', component: () => import('../views/CaronaFormView.vue'), props: true },
  { path: '/minhas-caronas', name: 'minhas-caronas', component: () => import('../views/MinhasCaronasView.vue') },
  { path: '/meus-pedidos', name: 'meus-pedidos', component: () => import('../views/MeusPedidosView.vue') },
  { path: '/perfil', name: 'perfil', component: () => import('../views/PerfilView.vue') },
  { path: '/:pathMatch(.*)*', name: 'nao-encontrada', component: () => import('../views/NaoEncontradaView.vue'), meta: { publica: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

// Rotas protegidas: sem login vai para /login e volta depois
router.beforeEach((to) => {
  if (!to.meta.publica && !logado.value) {
    return { name: 'login', query: { volta: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'cadastro') && logado.value) {
    return { name: 'buscar' }
  }
})

export default router
