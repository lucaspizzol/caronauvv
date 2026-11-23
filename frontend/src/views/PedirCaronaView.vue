<template>
  <div class="container py-4">
    <h1 class="titulo-pagina h3 mb-1">Pedir carona</h1>
    <p class="text-secondary mb-3">
      Não achou carona? Entre na fila: quando um motorista oferecer carona do seu bairro nesse horário, você é avisado e,
      nos primeiros {{ minutosPrioridade }} minutos, só quem estava na fila consegue pedir a vaga.
    </p>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <div class="row g-4">
      <!-- FORMULARIO -->
      <div class="col-lg-5">
        <form class="card p-3" novalidate @submit.prevent="entrar">
          <h2 class="h6 fw-bold mb-3"><i class="bi bi-hand-index-thumb me-1 text-primary"></i>Preciso de carona</h2>

          <div class="btn-group w-100 mb-3" role="group" aria-label="Sentido">
            <input id="pc-ida" v-model="form.sentido" type="radio" class="btn-check" value="ida" />
            <label class="btn btn-outline-primary" for="pc-ida"><i class="bi bi-house me-1"></i>Para a UVV</label>
            <input id="pc-volta" v-model="form.sentido" type="radio" class="btn-check" value="volta" />
            <label class="btn btn-outline-primary" for="pc-volta"><i class="bi bi-mortarboard me-1"></i>Da UVV para casa</label>
          </div>

          <div class="mb-3">
            <label class="form-label" for="pc-bairro">{{ form.sentido === 'ida' ? 'Saindo de qual bairro?' : 'Indo para qual bairro?' }}</label>
            <CampoBairro id="pc-bairro" v-model="form.bairro" :invalido="Boolean(erros.bairro)" />
            <div v-if="erros.bairro" class="invalid-feedback d-block">{{ erros.bairro }}</div>
          </div>

          <div class="row g-2 mb-3">
            <div class="col-12">
              <label class="form-label" for="pc-data">Dia</label>
              <input id="pc-data" v-model="form.data" type="date" :min="hoje" :max="limiteData" :class="['form-control', { 'is-invalid': erros.data }]" />
              <div class="invalid-feedback">{{ erros.data }}</div>
            </div>
            <div class="col-6">
              <label class="form-label" for="pc-ini">Das</label>
              <input id="pc-ini" v-model="form.hora_inicio" type="time" :class="['form-control', { 'is-invalid': erros.hora_inicio }]" />
              <div class="invalid-feedback">{{ erros.hora_inicio }}</div>
            </div>
            <div class="col-6">
              <label class="form-label" for="pc-fim">Até</label>
              <input id="pc-fim" v-model="form.hora_fim" type="time" :class="['form-control', { 'is-invalid': erros.hora_fim }]" />
              <div class="invalid-feedback">{{ erros.hora_fim }}</div>
            </div>
          </div>

          <button class="btn btn-primary w-100" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-people me-1"></i>Entrar na fila
          </button>
          <p class="form-text mb-0 mt-2">
            Até 3 pedidos abertos. A fila é por ordem de chegada; quem faltou numa viagem nos últimos 30 dias perde a prioridade.
          </p>
        </form>
      </div>

      <!-- MEUS PEDIDOS DE CARONA -->
      <div class="col-lg-7">
        <h2 class="h6 fw-bold mb-3">Meus pedidos de carona</h2>
        <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>
        <div v-else-if="!pedidos.length" class="card vazio">
          <i class="bi bi-people"></i>
          <p class="fw-semibold mb-1">Você não está em nenhuma fila.</p>
          <p class="small mb-0">Preencha o formulário: avisamos quando aparecer carona.</p>
        </div>
        <div v-else class="d-flex flex-column gap-2">
          <div v-for="p in pedidos" :key="p.id" :class="['card p-3', { 'opacity-75': p.status !== 'aberto' }]">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
              <StatusBadge :status="p.status" tipo="fila" />
              <span v-if="p.status === 'aberto' && p.posicao" class="badge rounded-pill text-bg-light border">
                {{ p.posicao }}º da fila
              </span>
              <span class="ms-auto small text-secondary">{{ dataCurta(p.data) }}</span>
            </div>
            <div class="fw-semibold">
              {{ p.sentido === 'ida' ? `${p.bairro} → UVV` : `UVV → ${p.bairro}` }}
              <span class="text-secondary fw-normal">· {{ p.hora_inicio }} às {{ p.hora_fim }}</span>
            </div>
            <div v-if="p.status === 'aberto'" class="small mt-1 d-flex flex-wrap gap-3 align-items-center">
              <RouterLink v-if="p.caronas_compativeis" :to="{ name: 'buscar', query: { bairro: p.bairro, sentido: p.sentido, data: p.data, hora_inicio: p.hora_inicio, hora_fim: p.hora_fim } }" class="fw-semibold">
                <i class="bi bi-car-front me-1"></i>{{ p.caronas_compativeis }} {{ p.caronas_compativeis === 1 ? 'carona disponível' : 'caronas disponíveis' }}
              </RouterLink>
              <span v-else class="text-secondary"><i class="bi bi-hourglass-split me-1"></i>Aguardando um motorista</span>
              <span v-if="p.sem_prioridade_por_falta" class="text-warning-emphasis">
                <i class="bi bi-exclamation-triangle me-1"></i>Sem prioridade por falta recente
              </span>
              <BotaoConfirmar class="ms-auto" texto="Sair da fila" pergunta="Sair desta fila?" icone="bi-x-circle" :acao="() => cancelar(p)" />
            </div>
            <div v-else-if="p.status === 'atendido'" class="small mt-1">
              <RouterLink to="/meus-pedidos"><i class="bi bi-ticket-perforated me-1"></i>Ver a vaga em Meus pedidos</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import CampoBairro from '../components/CampoBairro.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAoVivo } from '../composables/useAoVivo'
import api, { mensagemDeErro } from '../services/api'
import { auth, type TipoAviso } from '../stores/auth'
import type { ErrosCampos, PedidoCarona, Sentido } from '../types/api'
import { dataCurta, hojeLocal } from '../utils/formato'
import { errosDoServidor, regras, validar } from '../utils/validacao'

// ==========================================================
// "Pedir carona": o aluno entra na fila do bairro/horario e acompanha
// a posicao. A regra de prioridade fica no servidor (caronas/fila.py).
// ==========================================================
interface FormFila {
  bairro: string
  sentido: Sentido
  data: string
  hora_inicio: string
  hora_fim: string
}

const route = useRoute()
const hoje = hojeLocal()
const limiteData = hojeLocal(30)
const minutosPrioridade = 15
const texto = (v: unknown): string => (typeof v === 'string' ? v : '')

const form = reactive<FormFila>({
  bairro: texto(route.query.bairro) || auth.usuario?.bairro || '',
  sentido: route.query.sentido === 'volta' ? 'volta' : 'ida',
  data: texto(route.query.data) || hojeLocal(1),
  hora_inicio: texto(route.query.hora_inicio) || '06:30',
  hora_fim: texto(route.query.hora_fim) || '07:30'
})
const erros = ref<ErrosCampos>({})
const enviando = ref(false)
const pedidos = ref<PedidoCarona[]>([])
const carregando = ref(true)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

function avisar(mensagem: string, tipo: TipoAviso = 'success'): void {
  aviso.texto = mensagem
  aviso.tipo = tipo
}

async function carregar(): Promise<void> {
  const { data } = await api.get<{ pedidos: PedidoCarona[] }>('/pedidos-carona/minhas')
  pedidos.value = data.pedidos
}

useAoVivo(carregar, 15000)

async function entrar(): Promise<void> {
  erros.value = validar(form, {
    bairro: [regras.obrigatorio, regras.bairro],
    data: [regras.obrigatorio],
    hora_inicio: [regras.obrigatorio],
    hora_fim: [regras.obrigatorio, (v) => (String(v) > form.hora_inicio ? null : 'Precisa ser depois do início.')]
  })
  if (Object.keys(erros.value).length) return
  enviando.value = true
  try {
    const { data } = await api.post<{ pedido: PedidoCarona }>('/pedidos-carona', form)
    avisar(`Pronto! Você é o ${data.pedido.posicao}º da fila. Avisamos quando aparecer carona.`)
    await carregar()
  } catch (e) {
    erros.value = errosDoServidor(e, ['bairro', 'sentido', 'data', 'hora_inicio', 'hora_fim'])
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    enviando.value = false
  }
}

async function cancelar(p: PedidoCarona): Promise<void> {
  try {
    await api.post(`/pedidos-carona/${p.id}/cancelar`)
    avisar('Você saiu da fila.')
    await carregar()
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

onMounted(async () => {
  try {
    await carregar()
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    carregando.value = false
  }
})
</script>
