<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap align-items-end justify-content-between gap-2 mb-3">
      <div>
        <h1 class="titulo-pagina h3 mb-1">Minhas caronas</h1>
        <p class="text-secondary mb-0">As caronas que você ofereceu como motorista e os pedidos de vaga.</p>
        <AoVivo :atualizado-em="atualizadoEm" />
      </div>
      <RouterLink to="/caronas/nova" class="btn btn-destaque"><i class="bi bi-plus-lg me-1"></i>Nova carona</RouterLink>
    </div>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <ul class="nav nav-pills mb-3">
      <li class="nav-item">
        <button :class="['nav-link', { active: aba === 'abertas' }]" @click="aba = 'abertas'">
          Em aberto <span class="badge text-bg-light ms-1">{{ abertas.length }}</span>
        </button>
      </li>
      <li class="nav-item">
        <button :class="['nav-link', { active: aba === 'historico' }]" @click="aba = 'historico'">
          Histórico <span class="badge text-bg-light ms-1">{{ historico.length }}</span>
        </button>
      </li>
    </ul>

    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <div v-else-if="!lista.length" class="card vazio">
      <i :class="['bi', aba === 'abertas' ? 'bi-car-front' : 'bi-clock-history']"></i>
      <p class="fw-semibold mb-1">{{ aba === 'abertas' ? 'Você não tem caronas em aberto.' : 'Nenhuma carona no histórico ainda.' }}</p>
      <RouterLink v-if="aba === 'abertas'" to="/caronas/nova" class="small">Oferecer uma carona</RouterLink>
    </div>

    <div v-else class="d-flex flex-column gap-3">
      <div v-for="carona in lista" :key="carona.id" class="card p-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <StatusBadge :status="carona.status" />
          <span v-if="pendentes(carona) > 0" class="badge rounded-pill text-bg-danger">
            {{ pendentes(carona) }} {{ pendentes(carona) === 1 ? 'pedido novo' : 'pedidos novos' }}
          </span>
        </div>

        <CaronaInfo :carona="carona" />

        <!-- Viagem em andamento: GPS ao vivo e seguranca -->
        <div v-if="carona.status === 'em_andamento'" class="alert alert-info mt-3 mb-0 py-2">
          <div class="d-flex flex-wrap align-items-center gap-2">
            <i class="bi bi-car-front-fill"></i>
            <strong>Viagem em andamento.</strong>
            <span class="small">Peça o PIN de cada passageiro quando ele entrar no carro.</span>
            <button v-if="gps.caronaId !== carona.id" class="btn btn-sm btn-outline-primary ms-auto" @click="ligarGps(carona)">
              <i class="bi bi-geo-alt me-1"></i>Compartilhar minha localização
            </button>
            <span v-else class="small fw-semibold text-success ms-auto">
              <i class="bi bi-broadcast me-1"></i>Localização ao vivo ligada
              <span v-if="gps.ultimoEnvio"> · {{ gps.ultimoEnvio }}</span>
              <button class="btn btn-sm btn-link" @click="desligarGps">desligar</button>
            </span>
          </div>
          <div v-if="gps.erro" class="small text-danger mt-1">{{ gps.erro }}</div>
          <div class="mt-2"><SegurancaViagem :carona-id="carona.id" /></div>
        </div>

        <!-- Acoes do motorista -->
        <div class="d-flex flex-wrap gap-2 border-top mt-3 pt-3">
          <button class="btn btn-sm btn-outline-primary" @click="alternarPedidos(carona)">
            <i :class="['bi', abertas_.has(carona.id) ? 'bi-chevron-up' : 'bi-people']"></i>
            Pedidos ({{ (pedidos[carona.id] || []).length }})
          </button>
          <RouterLink v-if="podeEditar(carona)" :to="`/caronas/${carona.id}/editar`" class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-pencil me-1"></i>Editar
          </RouterLink>
          <BotaoConfirmar
            v-if="podeIniciar(carona)"
            texto="Iniciar viagem"
            pergunta="Começar a viagem agora?"
            icone="bi-play-fill"
            classe="btn-primary"
            :acao="() => iniciar(carona)"
          />
          <RouterLink v-if="podeAvaliarPassageiros(carona)" to="/avaliacoes" class="btn btn-sm btn-warning">
            <i class="bi bi-star-fill me-1"></i>Avaliar passageiros
          </RouterLink>
          <BotaoConfirmar
            v-if="podeConcluir(carona)"
            texto="Concluir carona"
            pergunta="A viagem terminou?"
            icone="bi-flag"
            classe="btn-success"
            :acao="() => concluir(carona)"
          />
          <BotaoConfirmar
            v-if="podeEditar(carona)"
            texto="Cancelar"
            pergunta="Cancelar a carona e todos os pedidos?"
            icone="bi-x-circle"
            :acao="() => cancelar(carona)"
          />
        </div>

        <!-- Pedidos recebidos -->
        <div v-if="abertas_.has(carona.id)" class="mt-3">
          <div v-if="!(pedidos[carona.id] || []).length" class="small text-secondary">Nenhum pedido de vaga ainda.</div>
          <div v-for="s in pedidos[carona.id]" :key="s.id" :class="['d-flex flex-wrap align-items-center gap-2 border rounded-3 p-2 mb-2 bg-light-subtle', { chegou: destacados.has(s.id) }]">
            <AvatarUsuario :usuario="s.passageiro" />
            <div class="flex-grow-1" style="min-width: 12rem">
              <div class="fw-semibold">
                <RouterLink :to="`/usuarios/${s.passageiro.id}`" class="text-reset">{{ s.passageiro.nome }}</RouterLink>
                <span class="text-secondary fw-normal small">· {{ s.passageiro.bairro }}</span>
              </div>
              <ReputacaoResumo :usuario="s.passageiro" mostrar-faltas />
              <div v-if="s.endereco_embarque" class="small"><i class="bi bi-geo-alt me-1"></i>{{ s.endereco_embarque }}</div>
              <div v-if="s.mensagem" class="small text-secondary">"{{ s.mensagem }}"</div>
              <div v-if="s.status === 'aceita' && s.passageiro.telefone" class="small mt-1">
                <i class="bi bi-telephone me-1"></i>{{ telefoneFormatado(s.passageiro.telefone) }}
                <a :href="linkWhatsApp(s.passageiro.telefone, `Oi ${s.passageiro.nome.split(' ')[0]}! Sobre a carona do CaronaUVV`)" target="_blank" rel="noopener" class="ms-2 text-success fw-semibold">
                  <i class="bi bi-whatsapp"></i> WhatsApp
                </a>
              </div>
            </div>
            <span v-if="s.embarcou_em" class="badge text-bg-success"><i class="bi bi-person-check-fill me-1"></i>Embarcou</span>
            <span v-else-if="s.faltou" class="badge text-bg-warning">Não apareceu</span>
            <span v-if="s.pagamento?.status === 'pago'" class="badge text-bg-light border text-success"><i class="bi bi-cash-coin me-1"></i>Pago</span>
            <StatusBadge :status="s.status" tipo="pedido" />

            <!-- Embarque: o passageiro fala o PIN e o motorista digita (como no Uber) -->
            <form
              v-if="carona.status === 'em_andamento' && s.status === 'aceita' && !s.embarcou_em && !s.faltou"
              class="d-flex flex-wrap align-items-start gap-2 w-100 mt-1"
              novalidate
              @submit.prevent="confirmarEmbarque(carona, s)"
            >
              <div>
                <input
                  v-model.trim="pins[s.id]"
                  inputmode="numeric"
                  maxlength="4"
                  :aria-label="`PIN de ${s.passageiro.nome}`"
                  placeholder="PIN"
                  :class="['form-control form-control-sm font-monospace text-center', { 'is-invalid': errosPin[s.id] }]"
                  style="width: 6rem"
                />
                <div class="invalid-feedback">{{ errosPin[s.id] }}</div>
              </div>
              <button class="btn btn-sm btn-success" :disabled="respondendo === s.id"><i class="bi bi-person-check me-1"></i>Confirmar embarque</button>
              <BotaoConfirmar texto="Não apareceu" pergunta="Marcar falta?" classe="btn-outline-warning" :acao="() => marcarFalta(carona, s)" />
            </form>

            <div v-if="s.status === 'pendente'" class="d-flex flex-wrap align-items-center gap-2">
              <ContagemRegressiva :ate="s.expira_em" prefixo="Responda em" texto-vencido="Prazo encerrado" @venceu="atualizarSilencioso" />
              <button class="btn btn-sm btn-success" :disabled="respondendo === s.id" @click="responder(carona, s, 'aceitar')">
                <i class="bi bi-check-lg"></i> Aceitar
              </button>
              <button class="btn btn-sm btn-outline-danger" :disabled="respondendo === s.id" @click="responder(carona, s, 'recusar')">
                <i class="bi bi-x-lg"></i> Recusar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import AoVivo from '../components/AoVivo.vue'
import AvatarUsuario from '../components/AvatarUsuario.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import ContagemRegressiva from '../components/ContagemRegressiva.vue'
import CaronaInfo from '../components/CaronaInfo.vue'
import ReputacaoResumo from '../components/ReputacaoResumo.vue'
import SegurancaViagem from '../components/SegurancaViagem.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAoVivo } from '../composables/useAoVivo'
import api, { camposDoErro, mensagemDeErro } from '../services/api'
import type { TipoAviso } from '../stores/auth'
import type { Carona, Solicitacao, StatusCarona } from '../types/api'
import { jaSaiu, linkWhatsApp, telefoneFormatado } from '../utils/formato'
import { regras } from '../utils/validacao'

const route = useRoute()

const caronas = ref<Carona[]>([])
const pedidos = reactive<Record<number, Solicitacao[]>>({}) // carona_id -> lista de solicitacoes
const abertas_ = reactive(new Set<number>()) // caronas com a lista de pedidos aberta
const aba = ref<'abertas' | 'historico'>('abertas')
const carregando = ref(true)
const respondendo = ref<number | null>(null)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })
const destacados = reactive(new Set<number>()) // pedidos que acabaram de chegar (piscam em amarelo)

const EM_ABERTO: StatusCarona[] = ['ativa', 'lotada', 'em_andamento']
const abertas = computed(() =>
  caronas.value.filter((c) => EM_ABERTO.includes(c.status)).sort((a, b) => a.data_hora_saida.localeCompare(b.data_hora_saida))
)
const historico = computed(() => caronas.value.filter((c) => !EM_ABERTO.includes(c.status)))
const lista = computed(() => (aba.value === 'abertas' ? abertas.value : historico.value))

const pendentes = (c: Carona) => (pedidos[c.id] || []).filter((s) => s.status === 'pendente').length
const JANELA_INICIO_MS = 30 * 60 * 1000 // pode iniciar 30 min antes da saida
const aceitos = (c: Carona) => (pedidos[c.id] || []).filter((s) => s.status === 'aceita')
const podeEditar = (c: Carona) => ['ativa', 'lotada'].includes(c.status) && !jaSaiu(c.data_hora_saida)
const podeIniciar = (c: Carona) =>
  ['ativa', 'lotada'].includes(c.status) &&
  aceitos(c).length > 0 &&
  new Date(c.data_hora_saida).getTime() - JANELA_INICIO_MS <= Date.now()
const podeConcluir = (c: Carona) => c.status === 'em_andamento' || (EM_ABERTO.includes(c.status) && jaSaiu(c.data_hora_saida))
const podeAvaliarPassageiros = (c: Carona) =>
  c.status === 'concluida' && aceitos(c).some((s) => !s.faltou && !s.ja_avaliei)

const pins = reactive<Record<number, string>>({}) // solicitacao_id -> PIN digitado
const errosPin = reactive<Record<number, string | null>>({})

function avisar(texto: string, tipo: TipoAviso = 'success'): void {
  aviso.texto = texto
  aviso.tipo = tipo
}

async function carregarPedidos(carona: Carona): Promise<void> {
  const { data } = await api.get<{ solicitacoes: Solicitacao[] }>(`/caronas/${carona.id}/solicitacoes`)
  pedidos[carona.id] = data.solicitacoes
}

async function carregar(): Promise<void> {
  carregando.value = true
  try {
    const { data } = await api.get<{ caronas: Carona[] }>('/caronas/minhas')
    caronas.value = data.caronas
    // Ja traz os pedidos das caronas em aberto, para mostrar quantos estao esperando resposta
    // (e das concluidas recentes, para o botao "Avaliar passageiros")
    const recentes = historico.value.filter((c) => c.status === 'concluida').slice(0, 5)
    await Promise.all([...abertas.value, ...recentes].map(carregarPedidos))
    abertas.value.filter((c) => pendentes(c) > 0 || c.status === 'em_andamento').forEach((c) => abertas_.add(c.id))
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    carregando.value = false
  }
}

// Atualizacao automatica: busca de novo as caronas e os pedidos e destaca os novos
async function atualizarSilencioso(): Promise<void> {
  const pendentesAntes = new Set(
    Object.values(pedidos).flat().filter((s) => s.status === 'pendente').map((s) => s.id)
  )
  const primeiraVez = !Object.keys(pedidos).length
  const { data } = await api.get<{ caronas: Carona[] }>('/caronas/minhas')
  caronas.value = data.caronas
  await Promise.all(abertas.value.map(carregarPedidos))
  if (primeiraVez) return
  for (const c of abertas.value) {
    const novos = (pedidos[c.id] || []).filter((s) => s.status === 'pendente' && !pendentesAntes.has(s.id))
    if (novos.length) {
      abertas_.add(c.id)
      novos.forEach((s) => {
        destacados.add(s.id)
        setTimeout(() => destacados.delete(s.id), 2500)
      })
    }
  }
}

const { atualizadoEm } = useAoVivo(atualizarSilencioso)

async function alternarPedidos(carona: Carona): Promise<void> {
  if (abertas_.has(carona.id)) {
    abertas_.delete(carona.id)
    return
  }
  try {
    if (!pedidos[carona.id]) await carregarPedidos(carona)
    abertas_.add(carona.id)
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

function substituir(carona: Carona): void {
  const i = caronas.value.findIndex((c) => c.id === carona.id)
  if (i >= 0) caronas.value[i] = carona
}

async function responder(carona: Carona, solicitacao: Solicitacao, acao: 'aceitar' | 'recusar'): Promise<void> {
  respondendo.value = solicitacao.id
  try {
    await api.post(`/solicitacoes/${solicitacao.id}/${acao}`)
    await carregarPedidos(carona)
    const { data } = await api.get<{ carona: Carona }>(`/caronas/${carona.id}`)
    substituir(data.carona)
    avisar(acao === 'aceitar' ? `Vaga confirmada para ${solicitacao.passageiro.nome}.` : 'Pedido recusado.')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    respondendo.value = null
  }
}

async function cancelar(carona: Carona): Promise<void> {
  try {
    const { data } = await api.post<{ carona: Carona }>(`/caronas/${carona.id}/cancelar`)
    substituir(data.carona)
    await carregarPedidos(carona)
    avisar('Carona cancelada. Os passageiros veem o cancelamento em "Meus pedidos".')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function concluir(carona: Carona): Promise<void> {
  try {
    const { data } = await api.post<{ carona: Carona }>(`/caronas/${carona.id}/concluir`)
    substituir(data.carona)
    await carregarPedidos(carona)
    if (gps.caronaId === carona.id) desligarGps()
    avisar('Carona concluída! Agora vocês podem se avaliar em "Avaliações".')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

// ==========================================================
// CICLO DA VIAGEM
// ==========================================================
async function iniciar(carona: Carona): Promise<void> {
  try {
    const { data } = await api.post<{ carona: Carona }>(`/caronas/${carona.id}/iniciar`)
    substituir(data.carona)
    await carregarPedidos(carona)
    abertas_.add(carona.id)
    avisar('Viagem iniciada! Os passageiros foram avisados. Confirme o PIN de cada um no embarque.')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function confirmarEmbarque(carona: Carona, s: Solicitacao): Promise<void> {
  errosPin[s.id] = regras.pin(pins[s.id])
  if (errosPin[s.id]) return
  respondendo.value = s.id
  try {
    await api.post(`/solicitacoes/${s.id}/embarque`, { pin: pins[s.id] })
    await carregarPedidos(carona)
    avisar(`${s.passageiro.nome.split(' ')[0]} embarcou. PIN conferido!`)
  } catch (e) {
    errosPin[s.id] = camposDoErro(e).pin || mensagemDeErro(e)
  } finally {
    respondendo.value = null
  }
}

async function marcarFalta(carona: Carona, s: Solicitacao): Promise<void> {
  try {
    await api.post(`/solicitacoes/${s.id}/falta`)
    await carregarPedidos(carona)
    avisar(`Falta registrada para ${s.passageiro.nome.split(' ')[0]}.`, 'warning')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

// ==========================================================
// GPS AO VIVO (aparece no link da familia)
// Envia a posicao do celular do motorista no maximo a cada 15 s.
// ==========================================================
const gps = reactive<{ caronaId: number | null; watchId: number | null; ultimoEnvio: string; erro: string }>({
  caronaId: null,
  watchId: null,
  ultimoEnvio: '',
  erro: ''
})
let ultimoEnvioMs = 0

function ligarGps(carona: Carona): void {
  gps.erro = ''
  if (!navigator.geolocation) {
    gps.erro = 'Este navegador não tem GPS.'
    return
  }
  desligarGps()
  gps.caronaId = carona.id
  gps.watchId = navigator.geolocation.watchPosition(
    async (p) => {
      if (Date.now() - ultimoEnvioMs < 15000) return
      ultimoEnvioMs = Date.now()
      try {
        await api.post(`/caronas/${carona.id}/posicao`, { lat: p.coords.latitude, lng: p.coords.longitude })
        gps.ultimoEnvio = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      } catch (e) {
        gps.erro = mensagemDeErro(e)
      }
    },
    () => {
      gps.erro = 'Permita o acesso à localização no navegador para compartilhar o trajeto.'
      desligarGps()
    },
    { enableHighAccuracy: true }
  )
}

function desligarGps(): void {
  if (gps.watchId !== null) navigator.geolocation.clearWatch(gps.watchId)
  gps.watchId = null
  gps.caronaId = null
}

onBeforeUnmount(desligarGps)

onMounted(async () => {
  if (route.query.ok === 'criada') avisar('Carona publicada! Ela já aparece na busca dos outros alunos.')
  if (route.query.ok === 'editada') avisar('Carona atualizada.')
  await carregar()
})
</script>
