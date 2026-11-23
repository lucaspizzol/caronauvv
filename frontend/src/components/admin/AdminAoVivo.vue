<template>
  <!-- Todas as viagens em tempo real, com a posicao do GPS (atualiza sozinho a cada 5 s) -->
  <section aria-labelledby="titulo-ao-vivo">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-2 mb-3">
      <div>
        <h2 id="titulo-ao-vivo" class="h5 fw-bold mb-0"><i class="bi bi-geo-alt-fill me-1 text-danger"></i>Viagens ao vivo</h2>
        <div class="small text-secondary">Acontecendo agora, saindo nas próximas 3 horas e concluídas nas últimas 3 horas.</div>
      </div>
      <AoVivo :atualizado-em="atualizadoEm" />
    </div>

    <AlertaMensagem :texto="erro" @fechar="erro = ''" />
    <div v-if="!painel" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <template v-else>
      <div class="row g-3 mb-3">
        <div v-for="k in indicadores" :key="k.rotulo" class="col-6 col-lg-3">
          <div :class="['card p-3 h-100 indicador', k.classe]">
            <div class="small text-secondary"><span v-if="k.classe === 'agora'" class="ponto-vivo me-1"></span>{{ k.rotulo }}</div>
            <div class="valor">{{ k.valor }}</div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <!-- Mapa: todos os carros em viagem + trajeto da viagem escolhida -->
        <div class="col-lg-7">
          <div class="card p-3 h-100">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <strong class="small"><i class="bi bi-map me-1"></i>{{ escolhida ? `Viagem #${escolhida.id}: ${escolhida.motorista.nome}` : 'Carros em viagem' }}</strong>
              <button v-if="escolhida" type="button" class="btn btn-sm btn-light" @click="escolhidaId = null">Ver todos</button>
            </div>
            <MapaTrilha :trilha="escolhida?.trilha ?? []" :marcas="marcas" :altura="420"
              :descricao="escolhida ? `Trajeto da viagem de ${escolhida.motorista.nome}` : 'Posição dos carros em viagem'" />
          </div>
        </div>

        <!-- Lista das viagens -->
        <div class="col-lg-5">
          <div class="lista d-flex flex-column gap-2">
            <button v-for="v in painel.viagens" :key="v.id" type="button"
              :class="['card viagem text-start p-3', `status-${v.status}`, { escolhida: v.id === escolhidaId }]"
              :aria-pressed="v.id === escolhidaId" @click="escolhidaId = v.id">
              <div class="d-flex justify-content-between align-items-start gap-2">
                <div class="min-w-0">
                  <div class="fw-bold">{{ v.bairro_origem }} <i class="bi bi-arrow-right"></i> {{ v.destino }}</div>
                  <div class="small text-secondary">saída {{ hora(v.data_hora_saida) }} · {{ v.sentido === 'ida' ? 'ida' : 'volta' }}</div>
                </div>
                <StatusBadge :status="v.status" />
              </div>

              <div class="d-flex align-items-center gap-2 mt-2 small">
                <AvatarUsuario :usuario="v.motorista" :tamanho="2" />
                <div class="flex-grow-1 min-w-0">
                  <span class="fw-semibold">{{ v.motorista.nome }}</span>
                  <span v-if="v.veiculo" class="text-secondary"> · {{ v.veiculo.modelo }} <span class="badge text-bg-light border">{{ v.veiculo.placa }}</span></span>
                </div>
                <a :href="`tel:${v.motorista.telefone}`" class="btn btn-sm btn-light" :aria-label="`Ligar para ${v.motorista.nome}`" @click.stop><i class="bi bi-telephone"></i></a>
              </div>

              <div v-if="v.status === 'em_andamento'" class="d-flex flex-wrap gap-3 small mt-2">
                <span><i class="bi bi-stopwatch me-1"></i>{{ v.minutos_em_viagem ?? 0 }} min de viagem</span>
                <span v-if="v.velocidade_kmh !== null"><i class="bi bi-speedometer me-1"></i>{{ numeroBr(v.velocidade_kmh, 0) }} km/h</span>
                <span v-if="v.ultima_posicao" :class="v.ultima_posicao.segundos_atras > 180 ? 'text-danger fw-semibold' : 'text-success'">
                  <i class="bi bi-broadcast me-1"></i>{{ v.ultima_posicao.segundos_atras > 180 ? 'sem sinal há' : 'GPS há' }} {{ tempoAtras(v.ultima_posicao.segundos_atras) }}
                </span>
                <span v-else class="text-warning-emphasis"><i class="bi bi-geo me-1"></i>sem GPS ainda</span>
                <span v-if="v.alertas_abertos" class="badge text-bg-danger"><i class="bi bi-exclamation-triangle me-1"></i>{{ v.alertas_abertos }} alerta(s)</span>
              </div>

              <div v-if="v.passageiros.length" class="d-flex flex-wrap gap-1 mt-2">
                <span v-for="p in v.passageiros" :key="p.solicitacao_id" :class="['badge rounded-pill fw-normal', SITUACAO[p.situacao].classe]"
                  :title="p.entrou_em ? `Entrou ${hora(p.entrou_em)}${p.saiu_em ? ` · saiu ${hora(p.saiu_em)}` : ''}` : SITUACAO[p.situacao].texto">
                  <i :class="['bi me-1', SITUACAO[p.situacao].icone]"></i>{{ p.nome.split(' ')[0] }} · {{ SITUACAO[p.situacao].texto }}
                </span>
              </div>
              <div v-else class="small text-secondary mt-2">Sem passageiro confirmado.</div>
            </button>

            <div v-if="!painel.viagens.length" class="card vazio text-center p-4 text-secondary">
              <i class="bi bi-car-front fs-2 d-block mb-2"></i>Nenhuma viagem agora nem nas próximas 3 horas.
            </div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAoVivo } from '../../composables/useAoVivo'
import api, { mensagemDeErro } from '../../services/api'
import type { PainelViagens, SituacaoPassageiro } from '../../types/api'
import { hora, numeroBr } from '../../utils/formato'
import AlertaMensagem from '../AlertaMensagem.vue'
import AoVivo from '../AoVivo.vue'
import AvatarUsuario from '../AvatarUsuario.vue'
import MapaTrilha, { type MarcaMapa } from '../MapaTrilha.vue'
import StatusBadge from '../StatusBadge.vue'

const SITUACAO: Record<SituacaoPassageiro, { texto: string; icone: string; classe: string }> = {
  aguardando: { texto: 'aguardando', icone: 'bi-hourglass-split', classe: 'text-bg-light border' },
  a_bordo: { texto: 'a bordo', icone: 'bi-person-check-fill', classe: 'text-bg-success' },
  desembarcou: { texto: 'desembarcou', icone: 'bi-box-arrow-right', classe: 'text-bg-secondary' },
  faltou: { texto: 'faltou', icone: 'bi-person-x', classe: 'text-bg-danger' }
}

const painel = ref<PainelViagens | null>(null)
const escolhidaId = ref<number | null>(null)
const erro = ref('')

const escolhida = computed(() => painel.value?.viagens.find((v) => v.id === escolhidaId.value) ?? null)

const indicadores = computed(() => {
  const t = painel.value?.totais
  return [
    { rotulo: 'Em viagem agora', valor: t?.em_andamento ?? 0, classe: 'agora' },
    { rotulo: 'Passageiros a bordo', valor: t?.passageiros_a_bordo ?? 0, classe: '' },
    { rotulo: 'Saindo em até 3 h', valor: t?.saindo_em_breve ?? 0, classe: '' },
    { rotulo: 'Concluídas (3 h)', valor: t?.concluidas_recentes ?? 0, classe: '' }
  ]
})

// Carros no mapa: a ultima posicao de cada viagem em andamento (ou so da escolhida, com entradas e saidas)
const marcas = computed<MarcaMapa[]>(() => {
  const viagens = painel.value?.viagens ?? []
  const lista = escolhida.value ? [escolhida.value] : viagens.filter((v) => v.status === 'em_andamento')
  return lista
    .filter((v) => v.ultima_posicao)
    .map((v) => ({
      lat: v.ultima_posicao!.lat,
      lng: v.ultima_posicao!.lng,
      tipo: 'carro' as const,
      texto: `${v.motorista.nome} · ${v.veiculo?.placa ?? 'sem placa'} · ${v.passageiros.filter((p) => p.situacao === 'a_bordo').length} a bordo`
    }))
})

function tempoAtras(segundos: number): string {
  if (segundos < 60) return `${segundos} s`
  const minutos = Math.round(segundos / 60)
  return minutos < 60 ? `${minutos} min` : `${Math.round(minutos / 60)} h`
}

async function carregar(): Promise<void> {
  const { data } = await api.get<PainelViagens>('/admin/viagens')
  painel.value = data
  if (escolhidaId.value && !data.viagens.some((v) => v.id === escolhidaId.value)) escolhidaId.value = null
}

const { atualizadoEm } = useAoVivo(carregar)

onMounted(async () => {
  try {
    await carregar()
  } catch (e) {
    erro.value = mensagemDeErro(e)
  }
})
</script>

<style scoped>
.indicador .valor {
  font-size: 1.9rem;
  font-weight: 800;
  color: var(--uvv-azul);
  line-height: 1.1;
}

.indicador.agora {
  border-top: 4px solid var(--bs-success);
}

.ponto-vivo {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--bs-success);
  animation: pulsar 1.6s infinite;
}

@keyframes pulsar {
  0% { box-shadow: 0 0 0 0 rgba(25, 135, 84, 0.6); }
  70% { box-shadow: 0 0 0 8px rgba(25, 135, 84, 0); }
  100% { box-shadow: 0 0 0 0 rgba(25, 135, 84, 0); }
}

.lista {
  max-height: 520px;
  overflow-y: auto;
  padding: 2px;
}

.viagem {
  border-left: 4px solid var(--bs-border-color);
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.viagem:hover {
  box-shadow: 0 0.25rem 0.75rem rgba(11, 42, 91, 0.12);
}

.viagem.status-em_andamento {
  border-left-color: var(--bs-success);
}

.viagem.status-ativa,
.viagem.status-lotada {
  border-left-color: var(--uvv-amarelo);
}

.viagem.escolhida {
  box-shadow: 0 0 0 2px var(--uvv-azul-2);
}

@media (prefers-reduced-motion: reduce) {
  .ponto-vivo {
    animation: none;
  }
  .viagem {
    transition: none;
  }
}
</style>
