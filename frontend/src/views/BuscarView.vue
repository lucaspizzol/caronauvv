<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap align-items-end justify-content-between gap-2 mb-3">
      <div>
        <h1 class="titulo-pagina h3 mb-1">Buscar caronas</h1>
        <p class="text-secondary mb-0">Caronas com vaga, saindo do seu bairro ou da UVV.</p>
        <AoVivo :atualizado-em="atualizadoEm" />
      </div>
      <RouterLink to="/caronas/nova" class="btn btn-destaque"><i class="bi bi-plus-lg me-1"></i>Oferecer carona</RouterLink>
    </div>

    <!-- FILTROS -->
    <form class="card p-3 mb-4" novalidate @submit.prevent="buscar">
      <div class="row g-2 align-items-end">
        <div class="col-12 col-md-4">
          <label class="form-label" for="f-bairro">Bairro</label>
          <CampoBairro id="f-bairro" v-model="filtros.bairro" />
        </div>
        <div class="col-6 col-md-2">
          <label class="form-label" for="f-sentido">Sentido</label>
          <select id="f-sentido" v-model="filtros.sentido" class="form-select">
            <option value="">Todos</option>
            <option value="ida">Ida (para a UVV)</option>
            <option value="volta">Volta (da UVV)</option>
          </select>
        </div>
        <div class="col-6 col-md-2">
          <label class="form-label" for="f-data">Data</label>
          <input id="f-data" v-model="filtros.data" type="date" :min="hoje" class="form-control" />
        </div>
        <div class="col-6 col-md-2">
          <label class="form-label" for="f-ini">Das</label>
          <input id="f-ini" v-model="filtros.hora_inicio" type="time" :class="['form-control', { 'is-invalid': erroFaixa }]" />
        </div>
        <div class="col-6 col-md-2">
          <label class="form-label" for="f-fim">Até</label>
          <input id="f-fim" v-model="filtros.hora_fim" type="time" :class="['form-control', { 'is-invalid': erroFaixa }]" />
        </div>
        <div v-if="erroFaixa" class="col-12 small text-danger">{{ erroFaixa }}</div>
        <div class="col-12 d-flex gap-2 justify-content-end mt-2">
          <button type="button" class="btn btn-light" @click="limpar">Limpar</button>
          <button type="submit" class="btn btn-primary px-4"><i class="bi bi-search me-1"></i>Buscar</button>
        </div>
      </div>
    </form>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <!-- RESULTADOS -->
    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <div v-else-if="!caronas.length" class="card vazio">
      <i class="bi bi-signpost-split"></i>
      <p class="fw-semibold mb-1">Nenhuma carona encontrada com esses filtros.</p>
      <p class="small mb-0">Tente outro horário ou ofereça você mesmo uma carona.</p>
    </div>

    <template v-else>
      <p class="small text-secondary">{{ caronas.length }} {{ caronas.length === 1 ? 'carona disponível' : 'caronas disponíveis' }}</p>
      <div class="d-flex flex-column gap-3">
        <div v-for="carona in caronas" :key="carona.id" class="card p-3">
          <CaronaInfo :carona="carona" />

          <div class="border-top mt-3 pt-3">
            <div v-if="carona.motorista.id === auth.usuario?.id" class="small text-secondary">
              <i class="bi bi-person-badge me-1"></i>Esta carona é sua. Os pedidos aparecem em
              <RouterLink to="/minhas-caronas">Minhas caronas</RouterLink>.
            </div>

            <div v-else-if="pedidos[carona.id]" class="small text-success fw-semibold">
              <i class="bi bi-check-circle-fill me-1"></i>{{ pedidos[carona.id] }}
              <RouterLink to="/meus-pedidos" class="ms-1">Ver meus pedidos</RouterLink>
            </div>

            <div v-else-if="meusPedidos[carona.id]" class="small fw-semibold" :class="meusPedidos[carona.id] === 'aceita' ? 'text-success' : 'text-warning-emphasis'">
              <i :class="['bi', meusPedidos[carona.id] === 'aceita' ? 'bi-check-circle-fill' : 'bi-hourglass-split', 'me-1']"></i>
              {{ meusPedidos[carona.id] === 'aceita' ? 'Sua vaga nesta carona está confirmada.' : 'Você já pediu vaga nesta carona e está aguardando o motorista.' }}
              <RouterLink to="/meus-pedidos" class="ms-1">Ver meus pedidos</RouterLink>
            </div>

            <form v-else-if="abertaId === carona.id" novalidate @submit.prevent="pedirVaga(carona)">
              <div class="row g-2">
                <div class="col-md-5">
                  <label class="form-label" :for="`emb-${carona.id}`">Onde você embarca? <span class="text-secondary fw-normal">(opcional)</span></label>
                  <input :id="`emb-${carona.id}`" v-model.trim="pedido.endereco_embarque" maxlength="255" class="form-control" placeholder="Ex.: ponto em frente à padaria" />
                </div>
                <div class="col-md-7">
                  <label class="form-label" :for="`msg-${carona.id}`">Mensagem para o motorista <span class="text-secondary fw-normal">(opcional)</span></label>
                  <input :id="`msg-${carona.id}`" v-model.trim="pedido.mensagem" maxlength="300" class="form-control" placeholder="Ex.: estou com mochila pequena" />
                </div>
              </div>
              <div class="d-flex justify-content-end gap-2 mt-2">
                <button type="button" class="btn btn-light btn-sm" @click="abertaId = null">Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm" :disabled="enviando">
                  <span v-if="enviando" class="spinner-border spinner-border-sm me-1"></span>Confirmar pedido
                </button>
              </div>
            </form>

            <div v-else class="d-flex justify-content-between align-items-center">
              <span class="small text-secondary">
                <i class="bi bi-lock me-1"></i>O telefone do motorista aparece depois que ele aceitar.
              </span>
              <button class="btn btn-primary btn-sm px-3 text-nowrap" @click="abrirPedido(carona)">
                <i class="bi bi-hand-index-thumb me-1"></i>Pedir vaga
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import CampoBairro from '../components/CampoBairro.vue'
import AoVivo from '../components/AoVivo.vue'
import CaronaInfo from '../components/CaronaInfo.vue'
import { useAoVivo } from '../composables/useAoVivo'
import api, { mensagemDeErro } from '../services/api'
import { auth, type TipoAviso } from '../stores/auth'
import type { Carona, Sentido, Solicitacao, StatusSolicitacao } from '../types/api'
import { hojeLocal } from '../utils/formato'

const hoje = hojeLocal()

interface Filtros {
  bairro: string
  sentido: '' | Sentido
  data: string
  hora_inicio: string
  hora_fim: string
}

const FILTROS_VAZIOS: Filtros = { bairro: '', sentido: '', data: '', hora_inicio: '', hora_fim: '' }

const filtros = reactive<Filtros>({ ...FILTROS_VAZIOS })
let aplicados: Partial<Filtros> = {} // filtros da ultima busca (a atualizacao automatica usa estes, nao o que esta sendo digitado)
const caronas = ref<Carona[]>([])
const carregando = ref(true)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'danger' })
const erroFaixa = ref('')

const abertaId = ref<number | null>(null)
const pedido = reactive({ endereco_embarque: '', mensagem: '' })
const pedidos = reactive<Record<number, string>>({}) // carona_id -> texto de confirmacao
const meusPedidos = ref<Record<number, StatusSolicitacao>>({}) // carona_id -> status do meu pedido em aberto (pendente/aceita)

async function carregarMeusPedidos(): Promise<void> {
  const { data } = await api.get<{ solicitacoes: Solicitacao[] }>('/solicitacoes/minhas')
  meusPedidos.value = Object.fromEntries(
    data.solicitacoes.filter((s) => ['pendente', 'aceita'].includes(s.status)).map((s) => [s.carona_id, s.status])
  )
}
const enviando = ref(false)

async function buscar(): Promise<void> {
  erroFaixa.value = ''
  if (filtros.hora_inicio && filtros.hora_fim && filtros.hora_inicio > filtros.hora_fim) {
    erroFaixa.value = 'O horário inicial precisa ser antes do final.'
    return
  }
  carregando.value = true
  aviso.texto = ''
  try {
    // Envia so os filtros preenchidos (GET /api/caronas?bairro=...&data=...)
    const params: Partial<Filtros> = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v))
    aplicados = params
    const [{ data }] = await Promise.all([api.get<{ caronas: Carona[] }>('/caronas', { params }), carregarMeusPedidos()])
    caronas.value = data.caronas
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
    caronas.value = []
  } finally {
    carregando.value = false
  }
}

function limpar(): void {
  Object.assign(filtros, FILTROS_VAZIOS)
  void buscar()
}

function abrirPedido(carona: Carona): void {
  abertaId.value = carona.id
  pedido.endereco_embarque = ''
  pedido.mensagem = ''
}

async function pedirVaga(carona: Carona): Promise<void> {
  enviando.value = true
  aviso.texto = ''
  try {
    const { data } = await api.post<{ solicitacao: Solicitacao }>(`/caronas/${carona.id}/solicitacoes`, pedido)
    pedidos[carona.id] =
      data.solicitacao.status === 'aceita'
        ? 'Vaga confirmada na hora (reserva automática)!'
        : 'Pedido enviado! Agora é só aguardar o motorista aceitar.'
    abertaId.value = null
    if (data.solicitacao.status === 'aceita') void buscar()
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  } finally {
    enviando.value = false
  }
}

// Atualizacao automatica: novas caronas aparecem e as lotadas somem sozinhas
async function atualizarSilencioso(): Promise<void> {
  if (carregando.value) return
  const [{ data }] = await Promise.all([api.get<{ caronas: Carona[] }>('/caronas', { params: aplicados }), carregarMeusPedidos()])
  caronas.value = data.caronas
  if (abertaId.value && !caronas.value.some((c) => c.id === abertaId.value)) abertaId.value = null
}

const { atualizadoEm } = useAoVivo(atualizarSilencioso)

onMounted(buscar)
</script>
