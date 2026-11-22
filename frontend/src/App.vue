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
    <RouterView />
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import NavBar from './components/NavBar.vue'
import { auth, logado } from './stores/auth'

const route = useRoute()
const mostrarMenu = computed(() => logado.value && !route.meta.publica)
</script>
