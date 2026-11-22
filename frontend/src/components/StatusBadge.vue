<template>
  <span :class="['badge', `text-bg-${info.cor}`, 'fw-semibold']">{{ info.texto }}</span>
</template>

<script setup>
import { computed } from 'vue'

import { STATUS_CARONA, STATUS_PEDIDO } from '../utils/formato'

const props = defineProps({
  status: { type: String, required: true },
  tipo: { type: String, default: 'carona' } // "carona" ou "pedido"
})

const info = computed(() => {
  const tabela = props.tipo === 'pedido' ? STATUS_PEDIDO : STATUS_CARONA
  return tabela[props.status] || { texto: props.status, cor: 'secondary' }
})
</script>
