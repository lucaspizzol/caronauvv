<template>
  <div v-if="texto" :class="['alert', `alert-${tipo}`, 'd-flex', 'align-items-start', 'gap-2', 'py-2']" role="alert">
    <i :class="['bi', tipo === 'success' ? 'bi-check-circle-fill' : tipo === 'info' ? 'bi-info-circle-fill' : 'bi-exclamation-triangle-fill', 'mt-1']"></i>
    <div class="flex-grow-1">{{ texto }}</div>
    <button type="button" class="btn-close btn-sm" aria-label="Fechar" @click="$emit('fechar')"></button>
  </div>
</template>

<script setup lang="ts">
import type { TipoAviso } from '../stores/auth'

withDefaults(defineProps<{ texto?: string; tipo?: TipoAviso }>(), {
  texto: '',
  tipo: 'danger'
})
defineEmits<{ fechar: [] }>()
</script>
