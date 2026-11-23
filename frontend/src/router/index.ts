import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { auth, logado } from '../stores/auth'

// Campos extras que cada rota pode ter em `meta` (o TypeScript confere o nome e o tipo)
// publica: abre sem login | livre: abre com ou sem login (link da familia)
// admin: so administradores
declare module 'vue-router' {
  interface RouteMeta {
    titulo?: string // nome da tela na aba do navegador
    publica?: boolean
    livre?: boolean
    comMenu?: boolean // publica, mas mostra o menu para quem esta logado (ex.: perguntas frequentes)
    admin?: boolean
  }
}

// Telas carregadas sob demanda (cada uma vira um arquivo JS separado no build)
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/caronas' },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { titulo: 'Entrar', publica: true } },
  { path: '/cadastro', name: 'cadastro', component: () => import('../views/CadastroView.vue'), meta: { titulo: 'Criar conta', publica: true } },
  { path: '/recuperar-senha', name: 'recuperar-senha', component: () => import('../views/RecuperarSenhaView.vue'), meta: { titulo: 'Esqueci minha senha', publica: true } },
  { path: '/perguntas-frequentes', name: 'faq', component: () => import('../views/FaqView.vue'), meta: { titulo: 'Perguntas frequentes', publica: true, livre: true, comMenu: true } },
  { path: '/acompanhar/:token', name: 'acompanhar', component: () => import('../views/AcompanharView.vue'), props: true, meta: { titulo: 'Acompanhar viagem', publica: true, livre: true } },
  { path: '/verificar-email', name: 'verificar-email', component: () => import('../views/VerificarEmailView.vue'), meta: { titulo: 'Confirmar e-mail' } },
  { path: '/caronas', name: 'buscar', component: () => import('../views/BuscarView.vue'), meta: { titulo: 'Buscar caronas' } },
  { path: '/pedir-carona', name: 'pedir-carona', component: () => import('../views/PedirCaronaView.vue'), meta: { titulo: 'Pedir carona' } },
  { path: '/caronas/nova', name: 'oferecer', component: () => import('../views/CaronaFormView.vue'), meta: { titulo: 'Oferecer carona' } },
  { path: '/caronas/:id/editar', name: 'editar', component: () => import('../views/CaronaFormView.vue'), props: true, meta: { titulo: 'Editar carona' } },
  { path: '/minhas-caronas', name: 'minhas-caronas', component: () => import('../views/MinhasCaronasView.vue'), meta: { titulo: 'Minhas caronas' } },
  { path: '/meus-pedidos', name: 'meus-pedidos', component: () => import('../views/MeusPedidosView.vue'), meta: { titulo: 'Meus pedidos' } },
  { path: '/avaliacoes', name: 'avaliacoes', component: () => import('../views/AvaliacoesView.vue'), meta: { titulo: 'Avaliações' } },
  { path: '/notificacoes', name: 'notificacoes', component: () => import('../views/NotificacoesView.vue'), meta: { titulo: 'Notificações' } },
  { path: '/perfil', name: 'perfil', component: () => import('../views/PerfilView.vue'), meta: { titulo: 'Meu perfil' } },
  { path: '/usuarios/:id', name: 'usuario', component: () => import('../views/PerfilPublicoView.vue'), props: true, meta: { titulo: 'Perfil do aluno' } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { titulo: 'Administração', admin: true } },
  { path: '/:pathMatch(.*)*', name: 'nao-encontrada', component: () => import('../views/NaoEncontradaView.vue'), meta: { titulo: 'Página não encontrada', publica: true, livre: true } }
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

// Nome da tela na aba do navegador ("Minhas caronas · CaronaUVV"): ajuda quem usa varias abas
router.afterEach((to) => {
  document.title = to.meta.titulo ? `${to.meta.titulo} · CaronaUVV` : 'CaronaUVV'
})

export default router
