<template>
  <span class="ao-vivo small text-secondary" :title="`Atualiza sozinho a cada ${segundos} segundos`">
    <span class="pulso"></span>Ao vivo<span v-if="atualizadoEm" class="d-none d-sm-inline"> · {{ horario }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

import { INTERVALO_PADRAO } from '../composables/useAoVivo'

const props = defineProps({ atualizadoEm: { type: Date, default: null } })
const segundos = INTERVALO_PADRAO / 1000
const horario = computed(() =>
  props.atualizadoEm ? props.atualizadoEm.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''
)
</script>
