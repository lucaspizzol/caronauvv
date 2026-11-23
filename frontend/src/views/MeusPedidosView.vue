<template>
  <div class="container py-4">
    <h1 class="titulo-pagina h3 mb-1">Meus pedidos</h1>
    <p class="text-secondary mb-1">As vagas que você pediu como passageiro.</p>
    <p class="mb-3"><AoVivo :atualizado-em="atualizadoEm" /></p>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <div v-else-if="!pedidos.length" class="card vazio">
      <i class="bi bi-ticket-perforated"></i>
      <p class="fw-semibold mb-1">Você ainda não pediu nenhuma vaga.</p>
      <RouterLink to="/caronas" class="small">Buscar caronas</RouterLink>
    </div>

    <div v-else class="d-flex flex-column gap-3">
      <div v-for="p in pedidos" :key="p.id" :class="['card p-3', { chegou: destacados.has(p.id) }]">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
          <StatusBadge :status="p.status" tipo="pedido" />
          <span v-if="p.carona.status === 'cancelada'" class="small text-danger fw-semibold">
            <i class="bi bi-exclamation-circle me-1"></i>O motorista cancelou esta carona
          </span>
          <span v-else-if="p.carona.status === 'concluida'" class="small text-secondary">Viagem concluída</span>
          <span v-else-if="p.carona.status === 'em_andamento' && p.status === 'aceita'" class="small fw-semibold text-info-emphasis">
            <i class="bi bi-car-front-fill me-1"></i>{{ p.embarcou_em ? 'Você está a bordo. Boa viagem!' : 'O motorista iniciou a viagem. Esteja no ponto!' }}
          </span>
        </div>

        <CaronaInfo :carona="p.carona" />

        <div class="border-top mt-3 pt-3 d-flex flex-wrap align-items-center gap-3">
          <!-- Contato liberado depois do aceite -->
          <template v-if="p.status === 'aceita'">
            <div class="small">
              <span class="fw-semibold">Motorista:</span> {{ telefoneFormatado(p.carona.motorista.telefone) }}
              <a :href="linkWhatsApp(p.carona.motorista.telefone, 'Oi! Sou seu passageiro no CaronaUVV')" target="_blank" rel="noopener" class="ms-2 text-success fw-semibold">
                <i class="bi bi-whatsapp"></i> WhatsApp
              </a>
            </div>
            <div v-if="p.pin_embarque && emAberto(p)" class="small">
              <span class="fw-semibold">PIN de embarque:</span>
              <span class="badge text-bg-dark fs-6 ms-1 font-monospace">{{ p.pin_embarque }}</span>
            </div>
          </template>
          <div v-else-if="p.status === 'pendente'" class="small text-secondary d-flex flex-column gap-1">
            <span>Aguardando o motorista responder. Se ele não responder a tempo, o pedido expira e você é avisado.</span>
            <ContagemRegressiva :ate="p.expira_em" prefixo="O motorista tem" texto-vencido="Prazo encerrado, atualizando..." @venceu="atualizarSilencioso" />
          </div>

          <div v-if="p.endereco_embarque" class="small text-secondary"><i class="bi bi-geo-alt me-1"></i>{{ p.endereco_embarque }}</div>

          <button v-if="p.status === 'aceita' && p.carona.status === 'em_andamento' && p.embarcou_em && !p.desembarcou_em"
                  class="btn btn-sm btn-outline-secondary" :disabled="desembarcando === p.id" @click="desembarcar(p)">
            <i class="bi bi-box-arrow-right me-1"></i>Desembarquei
          </button>
          <span v-else-if="p.desembarcou_em" class="small text-secondary"><i class="bi bi-box-arrow-right me-1"></i>Desceu às {{ hora(p.desembarcou_em) }}</span>
          <button v-if="p.status === 'aceita' && p.carona.status === 'concluida'" class="btn btn-sm btn-outline-primary"
                  :aria-expanded="resumos.has(p.id)" @click="alternarResumo(p.id)">
            <i class="bi bi-graph-up me-1"></i>Resumo da viagem
          </button>
          <RouterLink v-if="podeAvaliar(p)" to="/avaliacoes" class="btn btn-sm btn-warning">
            <i class="bi bi-star-fill me-1"></i>Avaliar {{ p.carona.motorista.nome.split(' ')[0] }}
          </RouterLink>
          <span v-else-if="p.ja_avaliei" class="small text-secondary"><i class="bi bi-star me-1"></i>Você já avaliou esta viagem</span>

          <div class="ms-auto">
            <BotaoConfirmar
              v-if="podeCancelar(p)"
              texto="Desistir da vaga"
              pergunta="Desistir desta carona?"
              icone="bi-x-circle"
              :acao="() => cancelar(p)"
            />
          </div>
        </div>

        <ResumoViagem v-if="resumos.has(p.id)" class="mt-3" :carona-id="p.carona.id" />

        <!-- Pagamento do rateio e seguranca (so com a vaga confirmada) -->
        <div v-if="p.status === 'aceita' && (emAberto(p) || p.carona.status === 'concluida')" class="border-top mt-3 pt-3 d-flex flex-column gap-2">
          <PixPagamento
            v-if="p.carona.valor_por_passageiro > 0"
            :solicitacao-id="p.id"
            :valor="p.carona.valor_por_passageiro"
            :motorista="p.carona.motorista.nome"
            :inicial="p.pagamento"
          />
          <SegurancaViagem v-if="emAberto(p)" :carona-id="p.carona.id" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import AoVivo from '../components/AoVivo.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import CaronaInfo from '../components/CaronaInfo.vue'
import ContagemRegressiva from '../components/ContagemRegressiva.vue'
import PixPagamento from '../components/PixPagamento.vue'
import ResumoViagem from '../components/ResumoViagem.vue'
import SegurancaViagem from '../components/SegurancaViagem.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAoVivo } from '../composables/useAoVivo'
import api, { mensagemDeErro } from '../services/api'
import type { TipoAviso } from '../stores/auth'
import type { SolicitacaoComCarona } from '../types/api'
import { hora, linkWhatsApp, telefoneFormatado } from '../utils/formato'
import { posicaoAtual } from '../utils/gps'

const pedidos = ref<SolicitacaoComCarona[]>([])
const carregando = ref(true)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })
const destacados = reactive(new Set<number>()) // pedidos cujo status acabou de mudar

const emAberto = (p: SolicitacaoComCarona) => ['ativa', 'lotada', 'em_andamento'].includes(p.carona.status)
const podeAvaliar = (p: SolicitacaoComCarona) =>
  p.status === 'aceita' && !p.faltou && p.carona.status === 'concluida' && !p.ja_avaliei
const podeCancelar = (p: SolicitacaoComCarona) =>
  ['pendente', 'aceita'].includes(p.status) && ['ativa', 'lotada'].includes(p.carona.status)

async function carregar(): Promise<void> {
  carregando.value = true
  try {
    const { data } = await api.get<{ solicitacoes: SolicitacaoComCarona[] }>('/solicitacoes/minhas')
    pedidos.value = data.solicitacoes
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  } finally {
    carregando.value = false
  }
}

// Atualizacao automatica: o passageiro ve o aceite/recusa do motorista sem recarregar
async function atualizarSilencioso(): Promise<void> {
  const antes: Record<number, string> = Object.fromEntries(pedidos.value.map((p) => [p.id, `${p.status}/${p.carona.status}`]))
  const { data } = await api.get<{ solicitacoes: SolicitacaoComCarona[] }>('/solicitacoes/minhas')
  pedidos.value = data.solicitacoes
  for (const p of pedidos.value) {
    if (antes[p.id] && antes[p.id] !== `${p.status}/${p.carona.status}`) {
      destacados.add(p.id)
      setTimeout(() => destacados.delete(p.id), 2500)
    }
  }
}

const { atualizadoEm } = useAoVivo(atualizarSilencioso)

const resumos = reactive(new Set<number>())
function alternarResumo(id: number): void {
  if (resumos.has(id)) resumos.delete(id)
  else resumos.add(id)
}

const desembarcando = ref<number | null>(null)
async function desembarcar(p: SolicitacaoComCarona): Promise<void> {
  desembarcando.value = p.id
  try {
    await api.post(`/solicitacoes/${p.id}/desembarque`, (await posicaoAtual()) || {})
    aviso.texto = 'Desembarque registrado. Chegou bem!'
    aviso.tipo = 'success'
    await carregar()
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  } finally {
    desembarcando.value = null
  }
}

async function cancelar(p: SolicitacaoComCarona): Promise<void> {
  try {
    await api.post(`/solicitacoes/${p.id}/cancelar`)
    aviso.texto = 'Pedido cancelado. A vaga voltou a ficar livre para outros alunos.'
    aviso.tipo = 'success'
    await carregar()
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  }
}

onMounted(carregar)
</script>
