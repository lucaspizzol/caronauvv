<template>
  <NavBar v-if="mostrarMenu" />
  <main :class="{ 'com-nav': mostrarMenu }">
    <!-- Regra de confianca: so quem confirmou o e-mail UVV oferece ou pede carona -->
    <div v-if="mostrarMenu && auth.usuario && !auth.usuario.email_verificado && route.name !== 'verificar-email'" class="aviso-email">
      <div class="container d-flex flex-wrap align-items-center gap-2 py-2 small">
        <i class="bi bi-envelope-exclamation-fill"></i>
        <span>Confirme seu e-mail UVV para oferecer e pedir caronas.</span>
        <RouterLink to="/verificar-email" class="btn btn-sm btn-dark ms-auto">Confirmar agora</RouterLink>
      </div>
    </div>
    <div v-if="mostrarMenu && avisoGlobal.texto" class="container pt-3">
      <AlertaMensagem class="mb-0" :texto="avisoGlobal.texto" :tipo="avisoGlobal.tipo" @fechar="avisoGlobal.texto = ''" />
    </div>
    <RouterView />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import AlertaMensagem from './components/AlertaMensagem.vue'
import NavBar from './components/NavBar.vue'
import api from './services/api'
import { atualizarUsuario, auth, avisoGlobal, logado } from './stores/auth'
import type { UsuarioLogado } from './types/api'

const route = useRoute()
const mostrarMenu = computed(() => logado.value && !route.meta.publica)

// Ao abrir/recarregar a pagina, busca os dados atuais do usuario
// (ex.: o admin aprovou o selo de verificado enquanto ele estava fora)
onMounted(async () => {
  if (!logado.value) return
  try {
    const { data } = await api.get<{ usuario: UsuarioLogado }>('/auth/me')
    atualizarUsuario(data.usuario)
  } catch {
    /* token invalido: o interceptor do api.ts ja manda para o login */
  }
})
</script>
