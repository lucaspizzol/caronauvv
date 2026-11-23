<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap align-items-end justify-content-between gap-2 mb-3">
      <div>
        <h1 class="titulo-pagina h3 mb-1">Meus pedidos</h1>
        <p class="text-secondary mb-0">As vagas que você pediu como passageiro. <AoVivo :atualizado-em="atualizadoEm" /></p>
      </div>
      <RouterLink to="/caronas" class="btn btn-outline-primary btn-sm"><i class="bi bi-search me-1"></i>Buscar caronas</RouterLink>
    </div>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <!-- Abas: proximas (confirmadas), aguardando resposta e historico -->
    <div class="abas-pedidos nav nav-pills gap-1 mb-3" role="tablist" aria-label="Filtrar pedidos">
      <button
        v-for="a in ABAS" :id="`aba-${a.chave}`" :key="a.chave" type="button" role="tab"
        :aria-selected="aba === a.chave" aria-controls="lista-pedidos"
        :class="['nav-link', { active: aba === a.chave }]" @click="aba = a.chave"
      >
        <i :class="['bi me-1', a.icone]"></i>{{ a.texto }}
        <span :class="['badge rounded-pill ms-1', aba === a.chave ? 'text-bg-light' : 'text-bg-secondary']">{{ grupos[a.chave].length }}</span>
      </button>
    </div>

    <div v-if="carregando" class="d-flex flex-column gap-3" aria-busy="true">
      <div v-for="n in 2" :key="n" class="card p-3 esqueleto"><div></div><div></div><div></div></div>
    </div>

    <!-- Estados vazios com chamada para a acao -->
    <div v-else-if="!grupos[aba].length" id="lista-pedidos" class="card vazio" role="tabpanel" :aria-labelledby="`aba-${aba}`">
      <i :class="['bi', VAZIO[aba].icone]"></i>
      <p class="fw-semibold mb-1">{{ VAZIO[aba].titulo }}</p>
      <p class="small mb-3">{{ VAZIO[aba].texto }}</p>
      <div class="d-flex flex-wrap justify-content-center gap-2">
        <RouterLink to="/caronas" class="btn btn-primary btn-sm"><i class="bi bi-search me-1"></i>Buscar caronas</RouterLink>
        <RouterLink to="/pedir-carona" class="btn btn-outline-primary btn-sm"><i class="bi bi-hand-index-thumb me-1"></i>Pedir carona</RouterLink>
      </div>
    </div>

    <div v-else id="lista-pedidos" class="d-flex flex-column gap-3" role="tabpanel" :aria-labelledby="`aba-${aba}`">
      <article v-for="p in grupos[aba]" :key="p.id" :class="['card cartao-pedido', `faixa-${faixa(p)}`, { chegou: destacados.has(p.id) }]">
        <!-- Status claro no topo -->
        <header class="cabecalho d-flex flex-wrap align-items-center gap-2">
          <StatusBadge :status="p.status" tipo="pedido" />
          <span class="small fw-semibold" :class="mensagem(p).classe"><i :class="['bi me-1', mensagem(p).icone]"></i>{{ mensagem(p).texto }}</span>
        </header>

        <div class="p-3">
          <CaronaInfo :carona="p.carona" />

          <!-- AGUARDANDO: contagem regressiva em destaque -->
          <div v-if="p.status === 'pendente'" class="caixa-espera mt-3">
            <ContagemRegressiva :ate="p.expira_em" prefixo="O motorista tem" texto-vencido="Prazo encerrado, atualizando..." @venceu="atualizarSilencioso" />
            <div class="small text-secondary">para responder. Se não responder, o pedido expira e você é avisado.</div>
          </div>

          <!-- CONFIRMADA: PIN, contato e ponto de embarque -->
          <div v-if="p.status === 'aceita' && emAberto(p)" class="row g-2 mt-2">
            <div v-if="p.pin_embarque" class="col-sm-4">
              <div class="caixa-pin">
                <div class="small text-secondary">PIN de embarque</div>
                <div class="pin font-monospace" :aria-label="`PIN ${p.pin_embarque.split('').join(' ')}`">{{ p.pin_embarque }}</div>
                <div class="small text-secondary">Fale para o motorista ao entrar</div>
              </div>
            </div>
            <div class="col-sm-8 small d-flex flex-column gap-1 justify-content-center">
              <div>
                <i class="bi bi-telephone me-1"></i><span class="fw-semibold">{{ p.carona.motorista.nome.split(' ')[0] }}:</span>
                {{ telefoneFormatado(p.carona.motorista.telefone) }}
                <a :href="linkWhatsApp(p.carona.motorista.telefone, 'Oi! Sou seu passageiro no CaronaUVV')" target="_blank" rel="noopener" class="ms-1 text-success fw-semibold">
                  <i class="bi bi-whatsapp"></i> WhatsApp
                </a>
              </div>
              <div v-if="p.endereco_embarque"><i class="bi bi-geo-alt me-1"></i>Embarque: {{ p.endereco_embarque }}</div>
              <div v-if="p.desembarcou_em" class="text-secondary"><i class="bi bi-box-arrow-right me-1"></i>Desceu às {{ hora(p.desembarcou_em) }}</div>
            </div>
          </div>
          <div v-else-if="p.endereco_embarque && p.status === 'pendente'" class="small text-secondary mt-2"><i class="bi bi-geo-alt me-1"></i>Embarque: {{ p.endereco_embarque }}</div>
        </div>

        <!-- Acoes agrupadas -->
        <footer v-if="temAcoes(p)" class="acoes">
          <div v-if="p.status === 'aceita' && (emAberto(p) || p.carona.status === 'concluida')" class="d-flex flex-column gap-2 w-100">
            <PixPagamento
              v-if="p.carona.valor_por_passageiro > 0"
              :solicitacao-id="p.id" :valor="p.carona.valor_por_passageiro" :motorista="p.carona.motorista.nome" :inicial="p.pagamento"
            />
            <SegurancaViagem v-if="emAberto(p)" :carona-id="p.carona.id" />
          </div>
          <div class="d-flex flex-wrap align-items-center gap-2 w-100">
            <button v-if="p.status === 'aceita' && p.carona.status === 'em_andamento' && p.embarcou_em && !p.desembarcou_em"
                    class="btn btn-sm btn-outline-secondary" :disabled="desembarcando === p.id" @click="desembarcar(p)">
              <i class="bi bi-box-arrow-right me-1"></i>Desembarquei
            </button>
            <button v-if="p.status === 'aceita' && p.carona.status === 'concluida'" class="btn btn-sm btn-outline-primary"
                    :aria-expanded="resumos.has(p.id)" @click="alternarResumo(p.id)">
              <i class="bi bi-graph-up me-1"></i>Resumo da viagem
            </button>
            <RouterLink v-if="podeAvaliar(p)" to="/avaliacoes" class="btn btn-sm btn-warning">
              <i class="bi bi-star-fill me-1"></i>Avaliar {{ p.carona.motorista.nome.split(' ')[0] }}
            </RouterLink>
            <span v-else-if="p.ja_avaliei" class="small text-secondary"><i class="bi bi-star me-1"></i>Você já avaliou</span>
            <div class="ms-auto">
              <BotaoConfirmar v-if="podeCancelar(p)" texto="Desistir" pergunta="Desistir desta carona?" icone="bi-x-circle" :acao="() => cancelar(p)" />
            </div>
          </div>
          <ResumoViagem v-if="resumos.has(p.id)" class="w-100" :carona-id="p.carona.id" />
        </footer>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

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
import { dataCurta, hora, linkWhatsApp, telefoneFormatado } from '../utils/formato'
import { posicaoAtual } from '../utils/gps'

const pedidos = ref<SolicitacaoComCarona[]>([])
const carregando = ref(true)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })
const destacados = reactive(new Set<number>()) // pedidos cujo status acabou de mudar

// ==========================================================
// Abas: proximas (vaga confirmada e viagem por vir/em andamento),
// aguardando resposta do motorista e historico (o resto).
// ==========================================================
type Aba = 'proximas' | 'aguardando' | 'historico'
const ABAS: { chave: Aba; texto: string; icone: string }[] = [
  { chave: 'proximas', texto: 'Próximas', icone: 'bi-calendar-check' },
  { chave: 'aguardando', texto: 'Aguardando', icone: 'bi-hourglass-split' },
  { chave: 'historico', texto: 'Histórico', icone: 'bi-clock-history' }
]
const VAZIO: Record<Aba, { icone: string; titulo: string; texto: string }> = {
  proximas: { icone: 'bi-calendar-check', titulo: 'Nenhuma viagem confirmada.', texto: 'Quando um motorista aceitar seu pedido, a viagem aparece aqui com o PIN de embarque.' },
  aguardando: { icone: 'bi-hourglass', titulo: 'Nenhum pedido esperando resposta.', texto: 'Peça vaga numa carona ou entre na fila do Pedir carona.' },
  historico: { icone: 'bi-clock-history', titulo: 'Seu histórico está vazio.', texto: 'Viagens concluídas, canceladas e pedidos expirados ficam guardados aqui.' }
}
const aba = ref<Aba>('proximas')
let escolheuAba = false
watch(aba, () => { escolheuAba = true })

const emAberto = (p: SolicitacaoComCarona) => ['ativa', 'lotada', 'em_andamento'].includes(p.carona.status)
const podeAvaliar = (p: SolicitacaoComCarona) =>
  p.status === 'aceita' && !p.faltou && p.carona.status === 'concluida' && !p.ja_avaliei
const grupos = computed<Record<Aba, SolicitacaoComCarona[]>>(() => {
  const g: Record<Aba, SolicitacaoComCarona[]> = { proximas: [], aguardando: [], historico: [] }
  for (const p of pedidos.value) {
    if (p.status === 'pendente') g.aguardando.push(p)
    else if (p.status === 'aceita' && emAberto(p)) g.proximas.push(p)
    else g.historico.push(p)
  }
  g.proximas.sort((a, b) => a.carona.data_hora_saida.localeCompare(b.carona.data_hora_saida)) // a mais proxima primeiro
  return g
})

// Primeira visita: abre na aba que tem algo para ver
function escolherAbaInicial(): void {
  if (escolheuAba) return
  aba.value = grupos.value.proximas.length ? 'proximas' : grupos.value.aguardando.length ? 'aguardando' : 'historico'
  escolheuAba = false
}

function faixa(p: SolicitacaoComCarona): string {
  if (p.status === 'pendente') return 'espera'
  if (p.status === 'aceita' && emAberto(p)) return 'ok'
  return 'fim'
}

function mensagem(p: SolicitacaoComCarona): { texto: string; icone: string; classe: string } {
  if (p.carona.status === 'cancelada') return { texto: 'O motorista cancelou esta carona', icone: 'bi-exclamation-circle', classe: 'text-danger' }
  if (p.carona.status === 'em_andamento' && p.status === 'aceita') {
    return p.embarcou_em
      ? { texto: p.desembarcou_em ? 'Você já desceu do carro' : 'Você está a bordo. Boa viagem!', icone: 'bi-car-front-fill', classe: 'text-info-emphasis' }
      : { texto: 'O motorista iniciou a viagem. Esteja no ponto!', icone: 'bi-broadcast', classe: 'text-info-emphasis' }
  }
  if (p.carona.status === 'concluida') return { texto: p.status === 'aceita' ? 'Viagem concluída' : 'Carona já aconteceu', icone: 'bi-flag', classe: 'text-secondary' }
  if (p.status === 'pendente') return { texto: 'Esperando o motorista responder', icone: 'bi-hourglass-split', classe: 'text-warning-emphasis' }
  if (p.status === 'aceita') return { texto: `Sai ${dataCurta(p.carona.data_hora_saida).toLowerCase()} às ${hora(p.carona.data_hora_saida)}`, icone: 'bi-calendar-event', classe: 'text-success' }
  if (p.status === 'expirada') return { texto: 'O motorista não respondeu a tempo', icone: 'bi-hourglass-bottom', classe: 'text-secondary' }
  if (p.status === 'recusada') return { texto: 'O motorista não aceitou', icone: 'bi-x-circle', classe: 'text-secondary' }
  return { texto: 'Você desistiu', icone: 'bi-x-circle', classe: 'text-secondary' }
}

function temAcoes(p: SolicitacaoComCarona): boolean {
  return p.status === 'aceita' || podeCancelar(p)
}

const podeCancelar = (p: SolicitacaoComCarona) =>
  ['pendente', 'aceita'].includes(p.status) && ['ativa', 'lotada'].includes(p.carona.status)

async function carregar(): Promise<void> {
  carregando.value = true
  try {
    const { data } = await api.get<{ solicitacoes: SolicitacaoComCarona[] }>('/solicitacoes/minhas')
    pedidos.value = data.solicitacoes
    escolherAbaInicial()
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

<style scoped>
.abas-pedidos { flex-wrap: nowrap; }
.abas-pedidos .nav-link { flex: 1 1 0; min-width: 0; white-space: nowrap; padding: 0.45rem 0.4rem; font-size: 0.9rem; border: 1px solid var(--bs-border-color); background: var(--bs-body-bg); color: var(--bs-body-color); }
@media (max-width: 400px) { .abas-pedidos .nav-link .bi { display: none; } }
.abas-pedidos .nav-link.active { background: var(--uvv-azul-2); border-color: var(--uvv-azul-2); color: #fff; }
.cartao-pedido { overflow: hidden; border-left: 4px solid transparent; }
.cartao-pedido.faixa-ok { border-left-color: var(--bs-success); }
.cartao-pedido.faixa-espera { border-left-color: var(--uvv-amarelo); }
.cartao-pedido.faixa-fim { border-left-color: var(--bs-border-color); }
.cabecalho { padding: 0.6rem 1rem; background: var(--bs-tertiary-bg); border-bottom: 1px solid var(--bs-border-color-translucent); }
.caixa-espera { background: #fff8e1; border: 1px solid #ffe08a; border-radius: var(--bs-border-radius); padding: 0.6rem 0.8rem; }
.caixa-pin { background: var(--uvv-azul); color: #fff; border-radius: var(--bs-border-radius-lg); padding: 0.6rem; text-align: center; }
.caixa-pin .text-secondary { color: rgba(255, 255, 255, 0.75) !important; }
.caixa-pin .pin { font-size: 1.9rem; font-weight: 800; letter-spacing: 0.35em; color: var(--uvv-amarelo); margin-right: -0.35em; }
.acoes { display: flex; flex-direction: column; gap: 0.75rem; padding: 0.75rem 1rem; border-top: 1px solid var(--bs-border-color-translucent); background: var(--bs-body-bg); }
.esqueleto div { height: 0.9rem; border-radius: 4px; background: linear-gradient(90deg, #eef1f6, #f8f9fb, #eef1f6); background-size: 200% 100%; animation: brilho 1.2s infinite; margin-bottom: 0.6rem; }
.esqueleto div:nth-child(2) { width: 70%; }
.esqueleto div:nth-child(3) { width: 40%; }
@keyframes brilho { from { background-position: 200% 0; } to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .esqueleto div { animation: none; } }
</style>
