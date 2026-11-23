<template>
  <!-- Administrador: interface propria, com menu lateral (sem as telas de aluno) -->
  <AdminShell v-if="mostrarMenu && ehAdmin">
    <AlertaMensagem v-if="avisoGlobal.texto" :texto="avisoGlobal.texto" :tipo="avisoGlobal.tipo" @fechar="avisoGlobal.texto = ''" />
    <RouterView />
  </AdminShell>

  <!-- Aluno -->
  <template v-else>
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
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import AlertaMensagem from './components/AlertaMensagem.vue'
import NavBar from './components/NavBar.vue'
import api from './services/api'
import { atualizarUsuario, auth, avisoGlobal, logado } from './stores/auth'
import type { UsuarioLogado } from './types/api'

// O menu do admin so e baixado por quem e admin
const AdminShell = defineAsyncComponent(() => import('./components/admin/AdminShell.vue'))

const route = useRoute()
// Paginas publicas escondem o menu; a FAQ (comMenu) mostra o menu para quem esta logado
const mostrarMenu = computed(() => logado.value && (!route.meta.publica || Boolean(route.meta.comMenu)))
const ehAdmin = computed(() => Boolean(auth.usuario?.is_admin))

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
