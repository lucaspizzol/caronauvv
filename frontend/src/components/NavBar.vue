<template>
  <!-- Menu do computador -->
  <nav class="navbar navbar-expand-md navbar-dark navbar-uvv sticky-top">
    <div class="container">
      <RouterLink class="navbar-brand marca" to="/caronas">
        <i class="bi bi-car-front-fill me-1"></i>Carona<span>UVV</span>
      </RouterLink>

      <ul class="navbar-nav me-auto d-none d-md-flex">
        <li v-for="item in itens" :key="item.to" class="nav-item">
          <RouterLink class="nav-link px-3" :to="item.to">
            <i :class="['bi', item.icone, 'me-1']"></i>{{ item.texto }}
          </RouterLink>
        </li>
      </ul>

      <div class="d-flex align-items-center gap-2">
        <RouterLink to="/perfil" class="text-white text-decoration-none d-flex align-items-center gap-2">
          <span class="avatar" style="width: 2rem; height: 2rem; font-size: 0.8rem">{{ iniciais(auth.usuario?.nome) }}</span>
          <span class="d-none d-lg-inline small">{{ primeiroNome }}</span>
        </RouterLink>
        <button class="btn btn-sm btn-outline-light" title="Sair" @click="fazerLogout">
          <i class="bi bi-box-arrow-right"></i><span class="d-none d-sm-inline ms-1">Sair</span>
        </button>
      </div>
    </div>
  </nav>

  <!-- Menu do celular (barra inferior) -->
  <nav class="nav-celular d-flex d-md-none">
    <RouterLink v-for="item in itensCelular" :key="item.to" :to="item.to">
      <i :class="['bi', item.icone]"></i>{{ item.curto || item.texto }}
    </RouterLink>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import api from '../services/api'
import { auth, sair } from '../stores/auth'
import { iniciais } from '../utils/formato'

const router = useRouter()

const itens = [
  { to: '/caronas', texto: 'Buscar caronas', curto: 'Buscar', icone: 'bi-search' },
  { to: '/caronas/nova', texto: 'Oferecer carona', curto: 'Oferecer', icone: 'bi-plus-circle' },
  { to: '/minhas-caronas', texto: 'Minhas caronas', curto: 'Motorista', icone: 'bi-car-front' },
  { to: '/meus-pedidos', texto: 'Meus pedidos', curto: 'Pedidos', icone: 'bi-ticket-perforated' }
]
const itensCelular = [...itens, { to: '/perfil', texto: 'Perfil', icone: 'bi-person-circle' }]

const primeiroNome = computed(() => (auth.usuario?.nome || '').split(' ')[0])

async function fazerLogout() {
  try {
    await api.post('/auth/logout')
  } catch {
    /* mesmo se a API falhar, o token e descartado no navegador */
  }
  sair()
  router.push({ name: 'login' })
}
</script>
