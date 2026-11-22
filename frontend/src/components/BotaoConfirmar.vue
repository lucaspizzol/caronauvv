<template>
  <!-- Acao destrutiva em dois cliques, sem janela de confirm() do navegador -->
  <span v-if="!confirmando">
    <button type="button" :class="['btn', 'btn-sm', classe]" :disabled="carregando" @click="confirmando = true">
      <i v-if="icone" :class="['bi', icone, 'me-1']"></i>{{ texto }}
    </button>
  </span>
  <span v-else class="d-inline-flex align-items-center gap-1 flex-wrap">
    <span class="small fw-semibold">{{ pergunta }}</span>
    <button type="button" class="btn btn-sm btn-danger" :disabled="carregando" @click="confirmar">
      <span v-if="carregando" class="spinner-border spinner-border-sm me-1"></span>Sim
    </button>
    <button type="button" class="btn btn-sm btn-light" :disabled="carregando" @click="confirmando = false">Não</button>
  </span>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  texto: { type: String, required: true },
  pergunta: { type: String, default: 'Tem certeza?' },
  icone: { type: String, default: '' },
  classe: { type: String, default: 'btn-outline-danger' },
  acao: { type: Function, required: true }
})

const confirmando = ref(false)
const carregando = ref(false)

async function confirmar() {
  carregando.value = true
  try {
    await props.acao()
  } finally {
    carregando.value = false
    confirmando.value = false
  }
}
</script>
