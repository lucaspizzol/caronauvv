<template>
  <!-- "Que horas voce vai sair?": caronas compativeis + onibus (estimativa) -->
  <section class="card p-3" aria-labelledby="plano-titulo">
    <h2 id="plano-titulo" class="h6 fw-bold mb-2"><i class="bi bi-clock me-1 text-primary"></i>Que horas você vai sair?</h2>
    <div class="d-flex flex-wrap align-items-end gap-2 mb-3">
      <div>
        <label class="form-label small mb-1" for="plano-hora">Saída {{ sentido === 'ida' ? 'de casa' : 'da UVV' }}</label>
        <input id="plano-hora" v-model="horaSaida" type="time" class="form-control form-control-sm" style="width: 8rem" />
      </div>
      <span class="small text-secondary pb-1">{{ dataCurta(data) }} · {{ sentido === 'ida' ? `${bairro || 'seu bairro'} → UVV` : `UVV → ${bairro || 'seu bairro'}` }}</span>
    </div>

    <div v-if="!bairro" class="small text-secondary">Escolha o bairro para ver as recomendações.</div>
    <template v-else>
      <!-- (a) Caronas -->
      <h3 class="h6 small fw-bold text-uppercase text-secondary mb-2">Caronas perto desse horário</h3>
      <div v-if="carregando" class="small text-secondary mb-3"><span class="spinner-border spinner-border-sm me-1"></span>Procurando...</div>
      <div v-else-if="caronas.length" class="d-flex flex-column gap-1 mb-3">
        <RouterLink
          v-for="c in caronas.slice(0, 3)" :key="c.id"
          :to="{ name: 'buscar', query: { bairro, sentido, data } }"
          class="carona-curta text-decoration-none"
        >
          <strong>{{ hora(c.data_hora_saida) }}</strong> · {{ c.motorista.nome.split(' ')[0] }} ·
          {{ c.vagas_restantes }} {{ c.vagas_restantes === 1 ? 'vaga' : 'vagas' }} · {{ dinheiro(c.valor_por_passageiro) }}
          <i class="bi bi-chevron-right float-end"></i>
        </RouterLink>
      </div>
      <p v-else class="small text-secondary mb-3">
        Nenhuma carona entre {{ faixa.inicio }} e {{ faixa.fim }}. Entre na fila ao lado para ser avisado.
      </p>

      <!-- (b) Onibus -->
      <h3 class="h6 small fw-bold text-uppercase text-secondary mb-2">
        Ônibus <span class="badge text-bg-warning text-dark ms-1">estimativa</span>
      </h3>
      <div v-if="onibus" class="small">
        <p class="mb-2">{{ onibus.caminho }}</p>
        <ul class="list-unstyled mb-2">
          <li v-for="l in onibus.linhas_do_bairro.slice(0, 3)" :key="`b${l.numero}`">
            <span class="badge text-bg-secondary me-1">{{ l.numero }}</span>{{ l.nome }}
          </li>
          <li v-for="l in onibus.linhas_ate_uvv" :key="`u${l.numero}`">
            <span class="badge text-bg-primary me-1">{{ l.numero }}</span>{{ l.nome }}
          </li>
        </ul>
        <p class="text-secondary mb-1"><i class="bi bi-info-circle me-1"></i>{{ onibus.aviso }}</p>
        <a :href="onibus.link_oficial" target="_blank" rel="noopener" class="fw-semibold">
          Ver horários oficiais <i class="bi bi-box-arrow-up-right"></i>
        </a>
        <p class="text-secondary mt-1 mb-0" style="font-size: 0.75rem">Fonte das linhas: {{ onibus.fonte }}.</p>
      </div>
      <p v-else class="small text-secondary mb-0">Sem sugestão de ônibus para esse bairro.</p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import api from '../services/api'
import type { Carona, RecomendacaoOnibus, Sentido } from '../types/api'
import { dataCurta, dinheiro, hora } from '../utils/formato'

// ==========================================================
// Recomendacoes para o horario de saida do aluno:
// (a) caronas ate 30 min antes/depois; (b) onibus que costumam servir o trajeto.
// Onibus e ESTIMATIVA: o Transcol nao publica horarios em dados abertos, entao
// a tela nunca mostra horario de onibus e manda conferir no app oficial.
// ==========================================================
const props = defineProps<{ bairro: string; sentido: Sentido; data: string; horaInicial: string }>()

const horaSaida = ref(props.horaInicial || '07:00')
const caronas = ref<Carona[]>([])
const onibus = ref<RecomendacaoOnibus | null>(null)
const carregando = ref(false)

function somarMinutos(hhmm: string, minutos: number): string {
  const [h, m] = hhmm.split(':').map(Number)
  const total = Math.min(Math.max(h * 60 + m + minutos, 0), 23 * 60 + 59)
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}
const faixa = computed(() => ({ inicio: somarMinutos(horaSaida.value, -30), fim: somarMinutos(horaSaida.value, 30) }))

let espera: ReturnType<typeof setTimeout> | undefined
async function recomendar(): Promise<void> {
  if (!props.bairro || !horaSaida.value) return
  carregando.value = true
  try {
    const [rc, ro] = await Promise.allSettled([
      api.get<{ caronas: Carona[] }>('/caronas', {
        params: { bairro: props.bairro, sentido: props.sentido, data: props.data, hora_inicio: faixa.value.inicio, hora_fim: faixa.value.fim }
      }),
      api.get<RecomendacaoOnibus>('/lugares/onibus', {
        params: { bairro: props.bairro, sentido: props.sentido, hora: Number(horaSaida.value.slice(0, 2)) }
      })
    ])
    caronas.value = rc.status === 'fulfilled' ? rc.value.data.caronas : []
    onibus.value = ro.status === 'fulfilled' ? ro.value.data : null
  } finally {
    carregando.value = false
  }
}

watch(() => props.horaInicial, (h) => { if (h) horaSaida.value = h })
watch(
  () => [props.bairro, props.sentido, props.data, horaSaida.value],
  () => {
    clearTimeout(espera)
    espera = setTimeout(() => void recomendar(), 500)
  },
  { immediate: true }
)
</script>

<style scoped>
.carona-curta {
  display: block;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--bs-border-color);
  border-radius: var(--bs-border-radius);
  color: inherit;
  font-size: 0.875rem;
}
.carona-curta:hover,
.carona-curta:focus-visible {
  border-color: var(--uvv-azul-2);
  background: rgba(22, 63, 130, 0.05);
}
</style>
