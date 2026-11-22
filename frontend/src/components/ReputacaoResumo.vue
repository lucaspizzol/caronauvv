<template>
  <!-- Resumo de confianca: nota, nivel de experiencia e selo de verificado -->
  <span class="reputacao d-inline-flex flex-wrap align-items-center gap-1 small">
    <span class="fw-semibold text-nowrap" :title="titulo">
      <i class="bi bi-star-fill text-warning"></i>
      {{ nota(rep?.nota_media) }}<span v-if="rep?.total_avaliacoes" class="text-secondary fw-normal"> ({{ rep.total_avaliacoes }})</span>
    </span>
    <span v-if="rep?.nivel" class="badge rounded-pill text-bg-light border">{{ rep.nivel }}</span>
    <i v-if="usuario?.verificado" class="bi bi-patch-check-fill text-primary" title="Perfil verificado pela UVV"></i>
    <span v-if="mostrarFaltas && rep?.faltas" class="badge rounded-pill text-bg-warning" title="Vezes que confirmou a vaga e não apareceu">
      {{ rep.faltas }} {{ rep.faltas === 1 ? 'falta' : 'faltas' }}
    </span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

import { nota } from '../utils/formato'

const props = defineProps({
  usuario: { type: Object, default: null }, // dict do usuario com .reputacao
  mostrarFaltas: { type: Boolean, default: false }
})

const rep = computed(() => props.usuario?.reputacao)
const titulo = computed(() => {
  const r = rep.value
  if (!r) return ''
  const viagens = r.viagens_motorista + r.viagens_passageiro
  return `${viagens} ${viagens === 1 ? 'viagem' : 'viagens'} no CaronaUVV`
})
</script>
