<template>
  <!-- Menu do aluno no computador (o administrador usa o AdminShell, com menu proprio) -->
  <nav class="navbar navbar-expand-lg navbar-dark navbar-uvv sticky-top">
    <div class="container">
      <RouterLink class="navbar-brand marca" to="/caronas">
        <i class="bi bi-car-front-fill me-1"></i>Carona<span>UVV</span>
      </RouterLink>

      <ul class="navbar-nav me-auto d-none d-lg-flex">
        <li v-for="item in itens" :key="item.to" class="nav-item">
          <RouterLink class="nav-link px-2 px-xxl-3 text-nowrap" :to="item.to">
            <i :class="['bi', item.icone, 'me-1']"></i><span :class="`d-none d-${largo}-inline`">{{ item.texto }}</span><span :class="`d-${largo}-none`">{{ item.curto }}</span>
          </RouterLink>
        </li>
      </ul>

      <div class="d-flex align-items-center gap-2">
        <RouterLink to="/perguntas-frequentes" class="btn btn-sm btn-link text-white" title="Perguntas frequentes" aria-label="Perguntas frequentes">
          <i class="bi bi-question-circle fs-5"></i>
        </RouterLink>
        <RouterLink to="/notificacoes" class="btn btn-sm btn-link text-white position-relative sino" title="Notificações" aria-label="Notificações">
          <i class="bi bi-bell-fill fs-5"></i>
          <span v-if="naoLidas > 0" class="position-absolute top-0 start-100 translate-middle badge rounded-pill text-bg-warning">
            {{ naoLidas > 9 ? '9+' : naoLidas }}
          </span>
        </RouterLink>
        <RouterLink to="/perfil" class="text-white text-decoration-none d-flex align-items-center gap-2" title="Meu perfil" aria-label="Meu perfil">
          <AvatarUsuario :usuario="auth.usuario" :tamanho="2" />
          <span :class="`d-none d-${largo}-inline small text-truncate`" style="max-width: 7rem">{{ primeiroNome }}</span>
        </RouterLink>
        <button class="btn btn-sm btn-outline-light text-nowrap" title="Sair" aria-label="Sair" @click="fazerLogout">
          <i class="bi bi-box-arrow-right"></i><span class="d-none d-xxl-inline ms-1">Sair</span>
        </button>
      </div>
    </div>
  </nav>

  <!-- Menu do celular e do tablet (barra inferior) -->
  <nav class="nav-celular d-flex d-lg-none">
    <RouterLink v-for="item in itensCelular" :key="item.to" :to="item.to">
      <i :class="['bi', item.icone]"></i>{{ item.curto || item.texto }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAoVivo } from '../composables/useAoVivo'
import api from '../services/api'
import { auth, sair } from '../stores/auth'
import AvatarUsuario from './AvatarUsuario.vue'

interface ItemMenu {
  to: string
  texto: string
  curto?: string // nome curto para telas medias
  icone: string
}

const router = useRouter()

const itens: ItemMenu[] = [
  { to: '/caronas', texto: 'Buscar caronas', curto: 'Buscar', icone: 'bi-search' },
  { to: '/pedir-carona', texto: 'Pedir carona', curto: 'Pedir', icone: 'bi-hand-index-thumb' },
  { to: '/caronas/nova', texto: 'Oferecer carona', curto: 'Oferecer', icone: 'bi-plus-circle' },
  { to: '/minhas-caronas', texto: 'Minhas caronas', curto: 'Motorista', icone: 'bi-car-front' },
  { to: '/meus-pedidos', texto: 'Meus pedidos', curto: 'Pedidos', icone: 'bi-ticket-perforated' },
  { to: '/avaliacoes', texto: 'Avaliações', curto: 'Avaliar', icone: 'bi-star' }
]
// Celular: no maximo 5 itens na barra de baixo (o perfil fica na foto, no topo)
const itensCelular: ItemMenu[] = itens.slice(0, 5)

const primeiroNome = computed(() => (auth.usuario?.nome || '').split(' ')[0])
// Com 6 itens, os nomes completos so cabem em telas bem largas (>= 1400 px)
const largo = 'xxl'

// Sino: numero de notificacoes nao lidas, atualizado a cada 10 s
const naoLidas = ref(0)
async function contar(): Promise<void> {
  const { data } = await api.get<{ nao_lidas: number }>('/notificacoes/contagem')
  naoLidas.value = data.nao_lidas
}
const { atualizarAgora } = useAoVivo(contar, 10000)
void atualizarAgora()
router.afterEach((to) => {
  if (to.name === 'notificacoes') naoLidas.value = 0
})

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
