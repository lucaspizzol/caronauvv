<template>
  <div class="campo-sugestao position-relative">
    <div class="input-group">
      <input
        :id="id"
        :value="modelValue"
        type="text"
        role="combobox"
        autocomplete="off"
        maxlength="255"
        aria-autocomplete="list"
        :aria-expanded="aberta"
        :aria-controls="`${id}-lista`"
        :aria-activedescendant="ativo >= 0 ? `${id}-op-${ativo}` : undefined"
        :placeholder="placeholder"
        :class="['form-control', { 'is-invalid': invalido }]"
        @input="digitou(($event.target as HTMLInputElement).value)"
        @blur="fecharDepois"
        @keydown.down.prevent="mover(1)"
        @keydown.up.prevent="mover(-1)"
        @keydown.enter="enter"
        @keydown.esc="fechar"
      />
      <button type="button" class="btn btn-outline-secondary" :aria-expanded="mostrarCep" :aria-controls="`${id}-cep`" @click="mostrarCep = !mostrarCep">
        <i class="bi bi-mailbox me-1" aria-hidden="true"></i>CEP
      </button>
    </div>
    <ul v-show="aberta && ruas.length" :id="`${id}-lista`" role="listbox" class="lista-sugestoes shadow-sm" aria-label="Ruas encontradas">
      <li
        v-for="(r, i) in ruas"
        :id="`${id}-op-${i}`"
        :key="`${r.cep}-${r.rua}-${r.bairro}`"
        role="option"
        :aria-selected="i === ativo"
        :class="{ ativo: i === ativo }"
        @mousedown.prevent="escolher(r)"
        @mousemove="ativo = i"
      >
        <span class="fw-semibold">{{ r.rua }}</span>
        <span class="small text-secondary ms-2">{{ r.bairro }} · {{ r.cidade }}</span>
      </li>
    </ul>

    <!-- div (e nao form): este campo fica dentro do formulario da tela -->
    <div v-if="mostrarCep" :id="`${id}-cep`" class="d-flex gap-2 mt-2">
      <label class="visually-hidden" :for="`${id}-cep-campo`">CEP</label>
      <input :id="`${id}-cep-campo`" v-model.trim="cep" inputmode="numeric" maxlength="9" placeholder="29102-920" class="form-control form-control-sm" style="max-width: 9rem" @keydown.enter.prevent="buscarCep" />
      <button type="button" class="btn btn-sm btn-primary" :disabled="buscando" @click="buscarCep">
        <span v-if="buscando" class="spinner-border spinner-border-sm me-1"></span>Preencher
      </button>
    </div>
    <div class="form-text" aria-live="polite">{{ ajuda }}</div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

import api, { mensagemDeErro } from '../services/api'
import type { CidadeGrandeVitoria, EnderecoCep } from '../types/api'

// ==========================================================
// Campo de rua/endereco com:
// - sugestao de ruas pelo nome (ViaCEP, chamado pelo servidor com cache);
// - botao CEP que preenche rua e bairro.
// Escolher uma rua ou um CEP emite "endereco" para a tela preencher o bairro.
// O numero da casa o aluno completa depois ("Rua Itaúnas, 120").
// ==========================================================
const props = withDefaults(
  defineProps<{ modelValue: string; id: string; cidade?: CidadeGrandeVitoria; invalido?: boolean; placeholder?: string }>(),
  { cidade: 'Vila Velha', invalido: false, placeholder: 'Ex.: Rua Itaúnas, 120' }
)
const emit = defineEmits<{ 'update:modelValue': [valor: string]; endereco: [endereco: EnderecoCep] }>()

const ruas = ref<EnderecoCep[]>([])
const aberta = ref(false)
const ativo = ref(-1)
const mostrarCep = ref(false)
const cep = ref('')
const buscando = ref(false)
const ajuda = ref('')

let espera: ReturnType<typeof setTimeout> | undefined
let pedido = 0

async function carregar(texto: string): Promise<void> {
  // So o nome da rua (sem o numero) e com 3+ letras, como o ViaCEP exige
  const nome = texto.split(',')[0].replace(/\d+/g, '').trim()
  if (nome.length < 3 || texto.includes(',')) {
    ruas.value = []
    return
  }
  const meu = ++pedido
  try {
    const { data } = await api.get<{ ruas: EnderecoCep[]; disponivel: boolean }>('/lugares/ruas', { params: { q: nome, cidade: props.cidade } })
    if (meu !== pedido) return
    ruas.value = data.ruas
    ativo.value = -1
    ajuda.value = data.disponivel ? '' : 'Sugestão de ruas indisponível agora; digite o endereço normalmente.'
  } catch {
    ruas.value = []
  }
}

function digitou(valor: string): void {
  emit('update:modelValue', valor)
  aberta.value = true
  clearTimeout(espera)
  espera = setTimeout(() => void carregar(valor), 500) // espera o aluno parar de digitar
}

function fechar(): void {
  aberta.value = false
  ativo.value = -1
}

function fecharDepois(): void {
  setTimeout(fechar, 120)
}

function mover(passo: number): void {
  const total = ruas.value.length
  if (!total) return
  aberta.value = true
  ativo.value = (ativo.value + passo + total) % total
}

function escolher(r: EnderecoCep): void {
  emit('update:modelValue', `${r.rua}, `)
  emit('endereco', r)
  ajuda.value = `Bairro: ${r.bairro}. Complete com o número (ou um ponto de referência).`
  fechar()
}

function enter(evento: KeyboardEvent): void {
  if (aberta.value && ativo.value >= 0 && ruas.value[ativo.value]) {
    evento.preventDefault()
    escolher(ruas.value[ativo.value])
  }
}

async function buscarCep(): Promise<void> {
  buscando.value = true
  try {
    const { data } = await api.get<{ endereco: EnderecoCep }>(`/lugares/cep/${cep.value.replace(/\D/g, '')}`)
    escolher(data.endereco)
    mostrarCep.value = false
  } catch (e) {
    ajuda.value = mensagemDeErro(e)
  } finally {
    buscando.value = false
  }
}

onBeforeUnmount(() => clearTimeout(espera))
</script>
