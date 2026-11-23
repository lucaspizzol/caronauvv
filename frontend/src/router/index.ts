import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { auth, logado } from '../stores/auth'

// Campos extras que cada rota pode ter em `meta` (o TypeScript confere o nome e o tipo)
// publica: abre sem login | livre: abre com ou sem login (link da familia)
// admin: so administradores
declare module 'vue-router' {
  interface RouteMeta {
    publica?: boolean
    livre?: boolean
    admin?: boolean
  }
}

// Telas carregadas sob demanda (cada uma vira um arquivo JS separado no build)
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/caronas' },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { publica: true } },
  { path: '/cadastro', name: 'cadastro', component: () => import('../views/CadastroView.vue'), meta: { publica: true } },
  { path: '/recuperar-senha', name: 'recuperar-senha', component: () => import('../views/RecuperarSenhaView.vue'), meta: { publica: true } },
  { path: '/acompanhar/:token', name: 'acompanhar', component: () => import('../views/AcompanharView.vue'), props: true, meta: { publica: true, livre: true } },
  { path: '/verificar-email', name: 'verificar-email', component: () => import('../views/VerificarEmailView.vue') },
  { path: '/caronas', name: 'buscar', component: () => import('../views/BuscarView.vue') },
  { path: '/caronas/nova', name: 'oferecer', component: () => import('../views/CaronaFormView.vue') },
  { path: '/caronas/:id/editar', name: 'editar', component: () => import('../views/CaronaFormView.vue'), props: true },
  { path: '/minhas-caronas', name: 'minhas-caronas', component: () => import('../views/MinhasCaronasView.vue') },
  { path: '/meus-pedidos', name: 'meus-pedidos', component: () => import('../views/MeusPedidosView.vue') },
  { path: '/avaliacoes', name: 'avaliacoes', component: () => import('../views/AvaliacoesView.vue') },
  { path: '/notificacoes', name: 'notificacoes', component: () => import('../views/NotificacoesView.vue') },
  { path: '/perfil', name: 'perfil', component: () => import('../views/PerfilView.vue') },
  { path: '/usuarios/:id', name: 'usuario', component: () => import('../views/PerfilPublicoView.vue'), props: true },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { admin: true } },
  { path: '/:pathMatch(.*)*', name: 'nao-encontrada', component: () => import('../views/NaoEncontradaView.vue'), meta: { publica: true, livre: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to) => (to.hash ? { el: to.hash } : { top: 0 })
})

// Telas de quem ainda nao entrou: quem ja esta logado vai direto para a busca
const ROTAS_DE_ENTRADA = ['login', 'cadastro', 'recuperar-senha']

// Rotas protegidas: sem login vai para /login e volta depois
router.beforeEach((to) => {
  if (!to.meta.publica && !logado.value) {
    return { name: 'login', query: { volta: to.fullPath } }
  }
  if (ROTAS_DE_ENTRADA.includes(String(to.name)) && logado.value) {
    return { name: 'buscar' }
  }
  if (to.meta.admin && !auth.usuario?.is_admin) {
    return { name: 'buscar' }
  }
  return true
})

export default router
