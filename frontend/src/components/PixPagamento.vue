<template>
  <!-- Rateio da carona: Pix "copia e cola" direto para o motorista -->
  <div class="pix">
    <div v-if="pagamento?.status === 'pago'" class="small text-success fw-semibold">
      <i class="bi bi-check-circle-fill me-1"></i>Pagamento de {{ dinheiro(pagamento.valor) }} informado ({{ pagamento.metodo }}).
    </div>

    <template v-else>
      <button v-if="!aberto" class="btn btn-sm btn-outline-success" @click="abrir">
        <i class="bi bi-qr-code me-1"></i>Pagar {{ dinheiro(valor) }} com Pix
      </button>

      <div v-else class="border rounded-3 p-3 mt-1">
        <AlertaMensagem :texto="erro" @fechar="erro = ''" />
        <div v-if="carregando" class="text-center py-2"><span class="spinner-border spinner-border-sm"></span></div>
        <div v-else-if="pagamento" class="d-flex flex-wrap gap-3 align-items-start">
          <img v-if="qr" :src="qr" alt="QR Code do Pix" width="150" height="150" class="border rounded" />
          <div class="flex-grow-1" style="min-width: 14rem">
            <div class="fw-semibold mb-1">Pix para {{ motorista }} · {{ dinheiro(pagamento.valor) }}</div>
            <div class="pix-codigo border rounded p-2 mb-2">{{ pagamento.pix_copia_cola }}</div>
            <div class="d-flex flex-wrap gap-2">
              <button class="btn btn-sm btn-outline-primary" @click="copiar"><i class="bi bi-clipboard me-1"></i>{{ copiado ? 'Copiado!' : 'Copiar código' }}</button>
              <button class="btn btn-sm btn-success" :disabled="enviando" @click="informar('pix')"><i class="bi bi-check2 me-1"></i>Já paguei</button>
              <button class="btn btn-sm btn-light" :disabled="enviando" @click="informar('dinheiro')">Paguei em dinheiro</button>
            </div>
          </div>
        </div>
        <div v-else-if="erro" class="d-flex gap-2">
          <button class="btn btn-sm btn-light" :disabled="enviando" @click="informar('dinheiro')">Vou pagar em dinheiro</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import api from '../services/api'
import { dinheiro } from '../utils/formato'
import AlertaMensagem from './AlertaMensagem.vue'

const props = defineProps({
  solicitacaoId: { type: Number, required: true },
  valor: { type: Number, required: true },
  motorista: { type: String, default: 'o motorista' },
  inicial: { type: Object, default: null } // pagamento que ja veio da API
})
const emit = defineEmits(['pago'])

const aberto = ref(false)
const carregando = ref(false)
const enviando = ref(false)
const pagamento = ref(props.inicial)
const qr = ref('')
const erro = ref('')
const copiado = ref(false)

async function abrir() {
  aberto.value = true
  carregando.value = true
  try {
    const { data } = await api.get(`/solicitacoes/${props.solicitacaoId}/pix`)
    pagamento.value = data.pagamento
    // QR Code gerado no navegador (biblioteca qrcode, carregada so quando precisa)
    const QRCode = (await import('qrcode')).default
    qr.value = await QRCode.toDataURL(data.pagamento.pix_copia_cola, { margin: 1, width: 300 })
  } catch (e) {
    erro.value = e.mensagem
  } finally {
    carregando.value = false
  }
}

async function copiar() {
  try {
    await navigator.clipboard.writeText(pagamento.value.pix_copia_cola)
    copiado.value = true
    setTimeout(() => (copiado.value = false), 2000)
  } catch {
    erro.value = 'Não deu para copiar automaticamente. Selecione o código e copie.'
  }
}

async function informar(metodo) {
  enviando.value = true
  try {
    const { data } = await api.post(`/solicitacoes/${props.solicitacaoId}/pagamento`, { metodo })
    pagamento.value = data.pagamento
    emit('pago', data.pagamento)
  } catch (e) {
    erro.value = e.mensagem
  } finally {
    enviando.value = false
  }
}
</script>
