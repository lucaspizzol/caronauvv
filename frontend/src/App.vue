<template>
  <NavBar v-if="mostrarMenu" />
  <main :class="{ 'com-nav': mostrarMenu }">
    <RouterView />
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import NavBar from './components/NavBar.vue'
import { logado } from './stores/auth'

const route = useRoute()
const mostrarMenu = computed(() => logado.value && !route.meta.publica)
</script>
