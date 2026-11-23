<template>
  <div class="campo-sugestao position-relative">
    <input
      :id="id"
      ref="campo"
      :value="modelValue"
      type="text"
      role="combobox"
      autocomplete="off"
      maxlength="100"
      aria-autocomplete="list"
      :aria-expanded="aberta"
      :aria-controls="`${id}-lista`"
      :aria-activedescendant="ativo >= 0 ? `${id}-op-${ativo}` : undefined"
      :aria-describedby="avisoRua ? `${id}-aviso` : undefined"
      :placeholder="placeholder"
      :class="['form-control', { 'is-invalid': invalido || avisoRua }]"
      @input="digitou(($event.target as HTMLInputElement).value)"
      @focus="abrir"
      @blur="fecharDepois"
      @keydown.down.prevent="mover(1)"
      @keydown.up.prevent="mover(-1)"
      @keydown.enter="enter"
      @keydown.esc="fechar"
    />
    <ul v-show="aberta && sugestoes.length" :id="`${id}-lista`" role="listbox" class="lista-sugestoes shadow-sm" :aria-label="`Bairros que combinam com ${modelValue || 'o que você digitou'}`">
      <li
        v-for="(b, i) in sugestoes"
        :id="`${id}-op-${i}`"
        :key="`${b.nome}-${b.cidade}`"
        role="option"
        :aria-selected="i === ativo"
        :class="{ ativo: i === ativo }"
        @mousedown.prevent="escolher(b)"
        @mousemove="ativo = i"
      >
        <span class="fw-semibold">{{ b.nome }}</span>
        <span class="small text-secondary ms-2">{{ b.cidade }} · ~{{ numeroBr(b.distancia_uvv_km, 1) }} km da UVV</span>
      </li>
    </ul>
    <div v-if="avisoRua" :id="`${id}-aviso`" class="invalid-feedback d-block">
      Isto parece um endereço. Aqui vai só o bairro (ex.: Itapuã); a rua vai no campo de rua/endereço.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import api from '../services/api'
import type { BairroSugestao } from '../types/api'
import { pareceEndereco } from '../utils/bairros'
import { numeroBr } from '../utils/formato'

// ==========================================================
// Campo "Bairro" com sugestoes enquanto digita (combobox acessivel):
// setas sobem/descem, Enter escolhe, Esc fecha. As sugestoes vem do
// servidor (todos os bairros da Grande Vitoria, sem diferenciar acento).
// O aluno pode digitar um bairro que nao esta na lista.
// ==========================================================
const props = withDefaults(defineProps<{ modelValue: string; id: string; invalido?: boolean; placeholder?: string }>(), {
  invalido: false,
  placeholder: 'Ex.: Itapuã'
})
const emit = defineEmits<{ 'update:modelValue': [valor: string]; escolher: [bairro: BairroSugestao] }>()

const sugestoes = ref<BairroSugestao[]>([])
const aberta = ref(false)
const ativo = ref(-1)
const avisoRua = computed(() => pareceEndereco(props.modelValue))

let espera: ReturnType<typeof setTimeout> | undefined
let pedido = 0 // ignora respostas antigas que chegam depois das novas

async function carregar(texto: string): Promise<void> {
  const meu = ++pedido
  try {
    const { data } = await api.get<{ bairros: BairroSugestao[] }>('/lugares/bairros', { params: { q: texto, limite: 8 } })
    if (meu !== pedido) return
    sugestoes.value = data.bairros
    ativo.value = -1
  } catch {
    sugestoes.value = [] // sem sugestoes o campo continua funcionando como texto livre
  }
}

function digitou(valor: string): void {
  emit('update:modelValue', valor)
  aberta.value = true
  clearTimeout(espera)
  espera = setTimeout(() => void carregar(valor), 200)
}

function abrir(): void {
  aberta.value = true
  if (!sugestoes.value.length) void carregar(props.modelValue)
}

function fechar(): void {
  aberta.value = false
  ativo.value = -1
}

function fecharDepois(): void {
  setTimeout(fechar, 120)
}

function mover(passo: number): void {
  if (!aberta.value) aberta.value = true
  const total = sugestoes.value.length
  if (!total) return
  ativo.value = (ativo.value + passo + total) % total
}

function escolher(b: BairroSugestao): void {
  emit('update:modelValue', b.nome)
  emit('escolher', b)
  fechar()
}

function enter(evento: KeyboardEvent): void {
  if (aberta.value && ativo.value >= 0 && sugestoes.value[ativo.value]) {
    evento.preventDefault() // nao envia o formulario: so escolhe a sugestao
    escolher(sugestoes.value[ativo.value])
  }
}

onBeforeUnmount(() => clearTimeout(espera))
</script>
