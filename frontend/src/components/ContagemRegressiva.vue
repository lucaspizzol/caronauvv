<template>
  <span v-if="restante" :class="['contagem', { urgente }]" role="timer" :aria-label="`${prefixo} ${restante}`">
    <i class="bi bi-hourglass-split me-1" aria-hidden="true"></i>{{ prefixo }} <strong class="font-monospace">{{ restante }}</strong>
  </span>
  <span v-else class="contagem text-secondary"><i class="bi bi-hourglass-bottom me-1" aria-hidden="true"></i>{{ textoVencido }}</span>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import type { DataIso } from '../types/api'
import { paraData, tempoRestante } from '../utils/formato'

// ==========================================================
// Contagem regressiva ate `ate` (ex.: o prazo de 30 min para o
// motorista responder o pedido). Atualiza a cada segundo e avisa
// (evento "venceu") quando chega a zero, para a tela recarregar.
// ==========================================================
const props = withDefaults(defineProps<{ ate: DataIso | null; prefixo?: string; textoVencido?: string }>(), {
  prefixo: 'Expira em',
  textoVencido: 'Prazo encerrado'
})
const emit = defineEmits<{ venceu: [] }>()

const agora = ref(new Date())
const restante = computed(() => tempoRestante(props.ate, agora.value))
const urgente = computed(() => {
  const fim = paraData(props.ate)
  return fim !== null && fim.getTime() - agora.value.getTime() < 5 * 60 * 1000
})

let timer: ReturnType<typeof setInterval> | undefined
let avisou = false
onMounted(() => {
  timer = setInterval(() => {
    agora.value = new Date()
    if (!restante.value && !avisou) {
      avisou = true
      emit('venceu')
    }
  }, 1000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.contagem { font-size: 0.875rem; }
.contagem.urgente { color: var(--bs-danger-text-emphasis); font-weight: 600; }
</style>
