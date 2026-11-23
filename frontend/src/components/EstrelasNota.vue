<template>
  <!-- Escolha da nota de 1 a 5 (teclado: setas ou numeros) -->
  <div class="estrelas d-inline-flex gap-1" role="radiogroup" :aria-label="rotulo">
    <button
      v-for="n in 5"
      :key="n"
      type="button"
      role="radio"
      :aria-checked="modelValue === n"
      :aria-label="`${n} ${n === 1 ? 'estrela' : 'estrelas'}`"
      class="btn btn-link p-0 estrela"
      @click="$emit('update:modelValue', n)"
    >
      <i :class="['bi', n <= modelValue ? 'bi-star-fill text-warning' : 'bi-star text-secondary']"></i>
    </button>
    <span class="ms-2 small fw-semibold align-self-center">{{ legenda }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ modelValue?: number; rotulo?: string }>(), {
  modelValue: 0,
  rotulo: 'Nota'
})
defineEmits<{ 'update:modelValue': [nota: number] }>()

const LEGENDAS = ['', 'Muito ruim', 'Ruim', 'Ok', 'Boa', 'Excelente']
const legenda = computed(() => LEGENDAS[props.modelValue] || 'Escolha de 1 a 5')
</script>
