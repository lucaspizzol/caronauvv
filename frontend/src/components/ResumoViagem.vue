<template>
  <div class="resumo-viagem">
    <div v-if="carregando" class="small text-secondary"><span class="spinner-border spinner-border-sm me-1"></span>Carregando o resumo...</div>
    <div v-else-if="erro" class="small text-danger">{{ erro }}</div>
    <template v-else-if="r">
      <div class="row g-2 mb-3 text-center">
        <div class="col-6 col-md-3">
          <div class="indicador"><div class="valor">{{ minutosTexto(r.duracao_min) }}</div><div class="rotulo">Duração</div></div>
        </div>
        <div class="col-6 col-md-3">
          <div class="indicador"><div class="valor">{{ r.distancia_km ? `${numeroBr(r.distancia_km, 1)} km` : '—' }}</div>
            <div class="rotulo">{{ r.distancia_pela_trilha ? 'Distância (GPS)' : 'Distância (estimada)' }}</div></div>
        </div>
        <div class="col-6 col-md-3">
          <div class="indicador"><div class="valor">{{ r.velocidade_media_kmh ? `${numeroBr(r.velocidade_media_kmh, 0)} km/h` : '—' }}</div><div class="rotulo">Velocidade média</div></div>
        </div>
        <div class="col-6 col-md-3">
          <div class="indicador"><div class="valor">{{ atrasoTexto(r.atraso_saida_min) }}</div><div class="rotulo">Saída x horário</div></div>
        </div>
      </div>

      <div class="table-responsive">
        <table class="table table-sm align-middle small mb-3">
          <caption class="visually-hidden">Entrada e saída de cada passageiro</caption>
          <thead><tr><th scope="col">Passageiro</th><th scope="col">Entrou</th><th scope="col">Saiu</th><th scope="col">A bordo</th><th scope="col">Distância</th></tr></thead>
          <tbody>
            <tr v-for="p in r.passageiros" :key="p.solicitacao_id">
              <td>{{ p.nome }}</td>
              <template v-if="p.faltou"><td colspan="4" class="text-warning-emphasis">Não apareceu</td></template>
              <template v-else>
                <td>{{ p.entrou_em ? hora(p.entrou_em) : '—' }}<i v-if="p.entrada" class="bi bi-geo-alt-fill text-success ms-1" title="Local registrado"></i></td>
                <td>{{ p.saiu_em ? hora(p.saiu_em) : '—' }}<i v-if="p.saida" class="bi bi-geo-alt-fill text-danger ms-1" title="Local registrado"></i></td>
                <td>{{ minutosTexto(p.minutos_a_bordo) }}</td>
                <td>{{ p.km_a_bordo ? `${numeroBr(p.km_a_bordo, 1)} km` : '—' }}</td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>

      <MapaTrilha v-if="r.trilha.length || marcas.length" :trilha="r.trilha" :marcas="marcas" descricao="Mapa com a trilha da viagem e os pontos de entrada e saída" />
      <p v-else class="small text-secondary mb-0"><i class="bi bi-map me-1"></i>Sem trilha GPS (o motorista não compartilhou a localização ou a trilha já foi apagada).</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'

import api, { mensagemDeErro } from '../services/api'
import type { ResumoViagem } from '../types/api'
import { hora, numeroBr } from '../utils/formato'
import type { MarcaMapa } from './MapaTrilha.vue'

// O mapa (Leaflet) so e baixado quando o resumo abre
const MapaTrilha = defineAsyncComponent(() => import('./MapaTrilha.vue'))

const props = defineProps<{ caronaId: number }>()
const r = ref<ResumoViagem | null>(null)
const carregando = ref(true)
const erro = ref('')

const marcas = computed<MarcaMapa[]>(() => {
  const lista: MarcaMapa[] = []
  for (const p of r.value?.passageiros || []) {
    const nome = p.nome.split(' ')[0]
    if (p.entrada) lista.push({ ...p.entrada, texto: `${nome} entrou às ${hora(p.entrou_em)}`, tipo: 'entrada' })
    if (p.saida) lista.push({ ...p.saida, texto: `${nome} saiu às ${hora(p.saiu_em)}`, tipo: 'saida' })
  }
  return lista
})

function minutosTexto(min: number | null): string {
  if (min === null) return '—'
  return min >= 60 ? `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')}` : `${min} min`
}

function atrasoTexto(min: number | null): string {
  if (min === null) return '—'
  if (Math.abs(min) <= 1) return 'No horário'
  return min > 0 ? `${min} min depois` : `${-min} min antes`
}

onMounted(async () => {
  try {
    const { data } = await api.get<{ resumo: ResumoViagem }>(`/caronas/${props.caronaId}/resumo`)
    r.value = data.resumo
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
})
</script>

<style scoped>
.indicador {
  background: var(--bs-tertiary-bg);
  border-radius: var(--bs-border-radius);
  padding: 0.5rem;
}
.indicador .valor { font-weight: 700; font-size: 1.05rem; color: var(--uvv-azul); }
.indicador .rotulo { font-size: 0.75rem; color: var(--bs-secondary-color); }
</style>
