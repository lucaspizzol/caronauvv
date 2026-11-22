<template>
  <!-- Seguranca durante a viagem: link da familia e botao de emergencia -->
  <div class="d-flex flex-wrap align-items-center gap-2">
    <button class="btn btn-sm btn-outline-primary" :disabled="gerando" @click="compartilhar">
      <i class="bi bi-share me-1"></i>Compartilhar viagem
    </button>
    <BotaoConfirmar
      texto="Emergência"
      pergunta="Acionar a emergência?"
      icone="bi-exclamation-octagon-fill"
      classe="btn-sos"
      :acao="emergencia"
    />
  </div>

  <!-- Link gerado -->
  <div v-if="link" class="border rounded-3 p-3 mt-2 small">
    <div class="fw-semibold mb-1"><i class="bi bi-people me-1"></i>Quem tiver este link acompanha a viagem (sem precisar de conta):</div>
    <div class="input-group input-group-sm mb-2">
      <input class="form-control font-monospace" :value="link" readonly aria-label="Link da viagem" />
      <button class="btn btn-outline-secondary" @click="copiar">{{ copiado ? 'Copiado!' : 'Copiar' }}</button>
      <a :href="link" target="_blank" rel="noopener" class="btn btn-outline-secondary">Abrir</a>
    </div>
    <div class="d-flex flex-wrap gap-2">
      <a v-for="c in contatos" :key="c.id" :href="linkWhatsApp(c.telefone, mensagem)" target="_blank" rel="noopener" class="btn btn-sm btn-success">
        <i class="bi bi-whatsapp me-1"></i>Enviar para {{ c.nome }}
      </a>
      <a :href="linkWhatsApp('', mensagem)" target="_blank" rel="noopener" class="btn btn-sm btn-outline-success">
        <i class="bi bi-whatsapp me-1"></i>Escolher contato
      </a>
      <RouterLink v-if="!contatos.length" to="/perfil#seguranca" class="small align-self-center">Cadastrar contatos de confiança</RouterLink>
    </div>
  </div>

  <!-- Emergencia acionada -->
  <div v-if="sos" class="alert alert-danger mt-2 mb-0">
    <div class="fw-bold mb-1"><i class="bi bi-exclamation-octagon-fill me-1"></i>Emergência registrada. A administração do CaronaUVV foi avisada.</div>
    <div class="d-flex flex-wrap gap-2 mt-2">
      <a href="tel:190" class="btn btn-danger"><i class="bi bi-telephone-fill me-1"></i>Ligar 190 (Polícia)</a>
      <a v-for="c in sos.contatos" :key="c.id" :href="linkWhatsApp(c.telefone, `EMERGÊNCIA: preciso de ajuda na carona. ${link || ''}`)" target="_blank" rel="noopener" class="btn btn-outline-danger">
        <i class="bi bi-whatsapp me-1"></i>Avisar {{ c.nome }}
      </a>
    </div>
  </div>
  <AlertaMensagem :texto="erro" @fechar="erro = ''" />
</template>

<script setup>
import { computed, ref } from 'vue'

import api from '../services/api'
import { linkWhatsApp } from '../utils/formato'
import AlertaMensagem from './AlertaMensagem.vue'
import BotaoConfirmar from './BotaoConfirmar.vue'

const props = defineProps({ caronaId: { type: Number, required: true } })

const link = ref('')
const contatos = ref([])
const gerando = ref(false)
const copiado = ref(false)
const sos = ref(null)
const erro = ref('')

const mensagem = computed(() => `Estou numa carona do CaronaUVV. Acompanhe por aqui: ${link.value}`)

async function compartilhar() {
  gerando.value = true
  try {
    const [{ data }, c] = await Promise.all([
      api.post(`/caronas/${props.caronaId}/compartilhar`),
      api.get('/contatos')
    ])
    link.value = `${location.origin}${data.link.caminho}`
    contatos.value = c.data.contatos
  } catch (e) {
    erro.value = e.mensagem
  } finally {
    gerando.value = false
  }
}

async function copiar() {
  try {
    await navigator.clipboard.writeText(link.value)
    copiado.value = true
    setTimeout(() => (copiado.value = false), 2000)
  } catch {
    /* o campo continua visivel para copiar manualmente */
  }
}

function posicaoAtual() {
  // Tenta mandar a localizacao junto (ate 4 s); se o navegador negar, vai sem
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({})
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve({}),
      { timeout: 4000 }
    )
  })
}

async function emergencia() {
  try {
    const posicao = await posicaoAtual()
    const { data } = await api.post(`/caronas/${props.caronaId}/sos`, posicao)
    sos.value = data
  } catch (e) {
    erro.value = e.mensagem
  }
}
</script>
