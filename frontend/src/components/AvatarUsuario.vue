<template>
  <!-- Foto de perfil do aluno; sem foto (ou se ela nao carregar), mostra as iniciais -->
  <span class="avatar" :style="estilo">
    <img v-if="comFoto" :src="src" :alt="`Foto de ${usuario?.nome || 'usuário'}`" loading="lazy" @error="falhou = true" />
    <template v-else>{{ iniciais(usuario?.nome) }}</template>
  </span>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { PessoaComFoto } from '../types/api'
import { iniciais, urlFoto } from '../utils/formato'

const props = withDefaults(
  defineProps<{
    usuario?: PessoaComFoto | null // precisa de .nome e .foto_url
    tamanho?: number // em rem
  }>(),
  { usuario: null, tamanho: 2.5 }
)

const falhou = ref(false)
const src = computed(() => urlFoto(props.usuario?.foto_url))
const comFoto = computed(() => Boolean(src.value) && !falhou.value)
watch(src, () => (falhou.value = false))

const estilo = computed(() => ({
  width: `${props.tamanho}rem`,
  height: `${props.tamanho}rem`,
  fontSize: `${(props.tamanho * 0.36).toFixed(2)}rem`
}))
</script>
