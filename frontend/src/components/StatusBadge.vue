<template>
  <span :class="['badge', `text-bg-${info.cor}`, 'fw-semibold']">{{ info.texto }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { STATUS_CARONA, STATUS_PEDIDO, type InfoStatus } from '../utils/formato'

const props = withDefaults(
  defineProps<{
    status: string
    tipo?: 'carona' | 'pedido'
  }>(),
  { tipo: 'carona' }
)

const info = computed<InfoStatus>(() => {
  const tabela: Record<string, InfoStatus> = props.tipo === 'pedido' ? STATUS_PEDIDO : STATUS_CARONA
  return tabela[props.status] || { texto: props.status, cor: 'secondary' }
})
</script>
