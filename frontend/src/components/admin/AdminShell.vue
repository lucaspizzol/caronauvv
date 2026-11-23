<template>
  <!--
    Interface exclusiva da administracao: menu lateral proprio (nada das telas de aluno).
    Computador: menu fixo a esquerda. Celular/tablet: barra no topo + barra de baixo
    com as 4 secoes mais usadas e o botao "Menu", que abre o menu completo.
  -->
  <div class="admin-app">
    <a href="#conteudo-admin" class="pular">Pular para o conteúdo</a>

    <aside id="menu-admin" :class="['lateral', { aberto: menuAberto }]" aria-label="Menu da administração">
      <div class="lateral-topo">
        <RouterLink to="/admin" class="marca text-decoration-none" @click="fechar">
          <i class="bi bi-car-front-fill me-1"></i>Carona<span>UVV</span>
        </RouterLink>
        <span class="selo-admin"><i class="bi bi-shield-lock-fill me-1"></i>Administração</span>
        <button type="button" class="btn btn-link text-white ms-auto d-lg-none p-1" aria-label="Fechar menu" @click="fechar">
          <i class="bi bi-x-lg fs-5"></i>
        </button>
      </div>

      <nav class="lateral-links">
        <div v-for="g in GRUPOS" :key="g" class="grupo">
          <div class="grupo-titulo">{{ g }}</div>
          <RouterLink
            v-for="s in SECOES.filter((x) => x.grupo === g)"
            :key="s.id"
            :to="linkDa(s.id)"
            :class="['item', { ativo: abaAtual === s.id }]"
            :aria-current="abaAtual === s.id ? 'page' : undefined"
            @click="fechar"
          >
            <i :class="['bi', s.icone]"></i>
            <span class="flex-grow-1">{{ s.texto }}</span>
            <span v-if="contador(s.id).n" :class="['badge rounded-pill', `text-bg-${contador(s.id).cor}`]">{{ contador(s.id).n }}</span>
          </RouterLink>
        </div>

        <div class="grupo">
          <div class="grupo-titulo">Conta</div>
          <RouterLink to="/notificacoes" :class="['item', { ativo: route.name === 'notificacoes' }]" @click="fechar">
            <i class="bi bi-bell"></i><span class="flex-grow-1">Notificações</span>
            <span v-if="naoLidas" class="badge rounded-pill text-bg-warning">{{ naoLidas > 9 ? '9+' : naoLidas }}</span>
          </RouterLink>
          <RouterLink to="/perfil" :class="['item', { ativo: route.name === 'perfil' }]" @click="fechar">
            <i class="bi bi-person-gear"></i><span class="flex-grow-1">Meu perfil e segurança</span>
          </RouterLink>
        </div>
      </nav>

      <div class="lateral-rodape">
        <AvatarUsuario :usuario="auth.usuario" :tamanho="2.2" />
        <div class="min-w-0 flex-grow-1">
          <div class="fw-semibold text-truncate">{{ auth.usuario?.nome }}</div>
          <div class="small text-truncate opacity-75">{{ auth.usuario?.email }}</div>
        </div>
        <button type="button" class="btn btn-sm btn-outline-light text-nowrap" @click="fazerLogout">
          <i class="bi bi-box-arrow-right me-1"></i>Sair
        </button>
      </div>
    </aside>
    <div v-if="menuAberto" class="fundo-menu d-lg-none" aria-hidden="true" @click="fechar"></div>

    <div class="principal">
      <!-- Topo do celular/tablet -->
      <header class="topo-celular d-lg-none">
        <button type="button" class="btn btn-link text-white p-1" aria-label="Abrir menu" aria-controls="menu-admin" :aria-expanded="menuAberto" @click="menuAberto = true">
          <i class="bi bi-list fs-3"></i>
        </button>
        <RouterLink to="/admin" class="marca text-decoration-none">Carona<span>UVV</span></RouterLink>
        <span class="selo-admin">Admin</span>
        <RouterLink to="/notificacoes" class="btn btn-link text-white position-relative ms-auto p-1" aria-label="Notificações">
          <i class="bi bi-bell-fill fs-5"></i>
          <span v-if="naoLidas" class="position-absolute top-0 start-100 translate-middle badge rounded-pill text-bg-warning">{{ naoLidas > 9 ? '9+' : naoLidas }}</span>
        </RouterLink>
      </header>

      <main id="conteudo-admin" class="conteudo">
        <slot />
      </main>
    </div>

    <!-- Barra de baixo do celular -->
    <nav class="barra-celular d-flex d-lg-none" aria-label="Seções principais">
      <RouterLink v-for="s in RAPIDAS" :key="s.id" :to="linkDa(s.id)" :class="{ ativo: abaAtual === s.id }">
        <span class="icone-barra">
          <i :class="['bi', s.icone]"></i>
          <span v-if="contador(s.id).n" :class="['ponto', contador(s.id).cor]"></span>
        </span>
        {{ s.curto }}
      </RouterLink>
      <button type="button" :aria-expanded="menuAberto" aria-controls="menu-admin" @click="menuAberto = true">
        <i class="bi bi-three-dots"></i>Menu
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAoVivo } from '../../composables/useAoVivo'
import api from '../../services/api'
import { carregarResumo, contador, ehAba, SECOES, type IdAba } from '../../stores/admin'
import { auth, sair } from '../../stores/auth'
import AvatarUsuario from '../AvatarUsuario.vue'

const GRUPOS = ['Acompanhar', 'Moderar', 'Sistema'] as const
const RAPIDAS: { id: IdAba; icone: string; curto: string }[] = [
  { id: 'resumo', icone: 'bi-grid-1x2', curto: 'Geral' },
  { id: 'aovivo', icone: 'bi-broadcast', curto: 'Ao vivo' },
  { id: 'avaliacoes', icone: 'bi-star-half', curto: 'Notas' },
  { id: 'alertas', icone: 'bi-shield-exclamation', curto: 'Alertas' }
]

const route = useRoute()
const router = useRouter()
const menuAberto = ref(false)

// Secao aberta: /admin -> visao geral, /admin/avaliacoes -> avaliacoes (fora do painel: nenhuma)
const abaAtual = computed<IdAba | null>(() => {
  if (route.name !== 'admin') return null
  return ehAba(route.params.aba) ? route.params.aba : 'resumo'
})
const linkDa = (id: IdAba): string => (id === 'resumo' ? '/admin' : `/admin/${id}`)

function fechar(): void {
  menuAberto.value = false
}
watch(() => route.fullPath, fechar)
// Esc fecha o menu aberto no celular
function aoTeclar(e: KeyboardEvent): void {
  if (e.key === 'Escape') fechar()
}
onMounted(() => window.addEventListener('keydown', aoTeclar))
onBeforeUnmount(() => window.removeEventListener('keydown', aoTeclar))

// Contadores do menu (pendencias) e do sino, atualizados a cada 10 s
const naoLidas = ref(0)
async function atualizar(): Promise<void> {
  const [, notif] = await Promise.all([carregarResumo(), api.get<{ nao_lidas: number }>('/notificacoes/contagem')])
  naoLidas.value = notif.data.nao_lidas
}
const { atualizarAgora } = useAoVivo(atualizar, 10000)
void atualizarAgora()
const pararDeOuvir = router.afterEach((to) => {
  if (to.name === 'notificacoes') naoLidas.value = 0
})
onBeforeUnmount(pararDeOuvir)

async function fazerLogout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } catch {
    /* mesmo se a API falhar, o token e descartado no navegador */
  }
  sair()
  void router.push({ name: 'login' })
}
</script>

<style scoped>
.admin-app {
  --largura-menu: 260px;
  min-height: 100vh;
}

.pular {
  position: absolute;
  left: -999px;
  top: 0.5rem;
  z-index: 2000;
  background: #fff;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
}

.pular:focus {
  left: 0.5rem;
}

/* ----- Menu lateral ----- */
.lateral {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--largura-menu);
  display: flex;
  flex-direction: column;
  color: #fff;
  background: linear-gradient(180deg, var(--uvv-azul) 0%, #0e3170 100%);
  z-index: 1040;
}

.lateral-topo {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
  padding: 1.1rem 1.1rem 0.9rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.marca {
  color: #fff;
  font-weight: 800;
  font-size: 1.25rem;
  letter-spacing: -0.01em;
}

.marca span {
  color: var(--uvv-amarelo);
}

.selo-admin {
  display: inline-flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--uvv-azul);
  background: var(--uvv-amarelo);
  border-radius: 999px;
  padding: 0.15rem 0.55rem;
}

.lateral-links {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0.75rem 1rem;
}

.grupo {
  margin-top: 0.75rem;
}

.grupo-titulo {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(255, 255, 255, 0.55);
  padding: 0 0.6rem 0.3rem;
}

.item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.65rem;
  border-radius: 0.6rem;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-weight: 500;
}

.item i {
  font-size: 1.1rem;
  width: 1.25rem;
  text-align: center;
}

.item:hover,
.item:focus-visible {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.item.ativo {
  background: #fff;
  color: var(--uvv-azul);
  font-weight: 700;
  box-shadow: inset 4px 0 0 var(--uvv-amarelo);
}

.lateral-rodape {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.85rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.12);
  font-size: 0.9rem;
}

.min-w-0 {
  min-width: 0;
}

/* ----- Area do conteudo ----- */
.principal {
  margin-left: var(--largura-menu);
  min-height: 100vh;
}

.conteudo {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem 2rem 2.5rem;
}

/* ----- Celular e tablet ----- */
.topo-celular {
  position: sticky;
  top: 0;
  z-index: 1030;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.75rem;
  background: var(--uvv-azul);
  color: #fff;
}

.barra-celular {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1030;
  background: #fff;
  border-top: 1px solid #e3e8f0;
  padding-bottom: env(safe-area-inset-bottom);
}

.barra-celular a,
.barra-celular button {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  text-align: center;
  font-size: 0.7rem;
  white-space: nowrap;
  color: #56637a;
  text-decoration: none;
  padding: 0.45rem 0 0.35rem;
}

.barra-celular i {
  display: block;
  font-size: 1.25rem;
}

.icone-barra {
  position: relative;
  display: block;
  width: fit-content;
  margin: 0 auto;
}

.barra-celular .ativo {
  color: var(--uvv-azul-2);
  font-weight: 700;
}

.barra-celular .ponto {
  position: absolute;
  top: 0.1rem;
  right: -0.35rem;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  border: 2px solid #fff;
}

.ponto.danger {
  background: #dc3545;
}

.ponto.warning {
  background: #f0ad00;
}

.ponto.success {
  background: #198754;
}

.fundo-menu {
  position: fixed;
  inset: 0;
  background: rgba(8, 20, 45, 0.5);
  z-index: 1035;
}

@media (max-width: 991.98px) {
  .lateral {
    width: min(300px, 86vw);
    transform: translateX(-100%);
    transition: transform 0.2s ease, visibility 0.2s;
    visibility: hidden;
  }

  .lateral.aberto {
    transform: none;
    visibility: visible;
    box-shadow: 0 0 2rem rgba(0, 0, 0, 0.35);
  }

  .principal {
    margin-left: 0;
  }

  .conteudo {
    padding: 1rem 0.85rem 5.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .lateral {
    transition: none;
  }
}
</style>
