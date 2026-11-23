<template>
  <!--
    Caronas por dia de saida nos ultimos 30 dias (uma serie: nao precisa de legenda).
    Passe o mouse (ou o Tab do teclado) numa coluna para ver o dia com concluidas,
    canceladas e as demais; "Ver em tabela" mostra os mesmos numeros sem grafico.
  -->
  <div class="grafico">
    <p class="resumo-grafico mb-2">
      <strong>{{ total }}</strong> {{ total === 1 ? 'carona' : 'caronas' }} nos últimos 30 dias
      <span class="text-secondary">· {{ concluidas }} {{ concluidas === 1 ? 'concluída' : 'concluídas' }} · {{ canceladas }} {{ canceladas === 1 ? 'cancelada' : 'canceladas' }}</span>
    </p>

    <p v-if="!total" class="small text-secondary mb-0">Nenhuma carona saiu nos últimos 30 dias.</p>

    <template v-else>
      <div class="area" role="img" :aria-label="descricao">
        <div class="eixo-y" aria-hidden="true">
          <span v-for="m in escala.marcas" :key="m" :style="{ bottom: `${(m / escala.topo) * 100}%` }">{{ m }}</span>
        </div>
        <div
          class="plot"
          tabindex="0"
          aria-label="Use as setas para ver cada dia"
          @mouseleave="foco = null"
          @focus="foco = foco ?? dias.length - 1"
          @blur="foco = null"
          @keydown.left.prevent="mover(-1)"
          @keydown.right.prevent="mover(1)"
        >
          <div v-for="m in escala.marcas" :key="m" class="grade" :style="{ bottom: `${(m / escala.topo) * 100}%` }"></div>
          <div class="colunas">
            <div v-for="(d, i) in dias" :key="d.dia" class="slot" @mouseenter="foco = i">
              <div v-if="d.total" :class="['coluna', { ativa: foco === i }]" :style="{ height: `${(d.total / escala.topo) * 100}%` }"></div>
            </div>
          </div>
          <div v-if="foco !== null && diaEmFoco" class="dica" :style="posicaoDica" role="status" aria-live="polite">
            <div class="fw-semibold">{{ dataCurtaNumericaSemAno(diaEmFoco.dia) }} · {{ diaEmFoco.total }} {{ diaEmFoco.total === 1 ? 'carona' : 'caronas' }}</div>
            <div v-if="diaEmFoco.total" class="text-white-50">
              {{ diaEmFoco.concluidas }} concluída(s) · {{ diaEmFoco.canceladas }} cancelada(s)<span v-if="diaEmFoco.outras"> · {{ diaEmFoco.outras }} ativa(s)</span>
            </div>
          </div>
        </div>
      </div>
      <div class="eixo-x" aria-hidden="true">
        <span v-for="(d, i) in dias" :key="d.dia">{{ i % 7 === 1 || i === dias.length - 1 ? (i === dias.length - 1 ? 'hoje' : diaMes(d.dia)) : '' }}</span>
      </div>

      <details class="mt-2 small">
        <summary class="text-secondary">Ver em tabela</summary>
        <div class="table-responsive mt-2" style="max-height: 240px">
          <table class="table table-sm mb-0">
            <thead>
              <tr><th>Dia</th><th class="text-end">Total</th><th class="text-end">Concluídas</th><th class="text-end">Canceladas</th><th class="text-end">Ativas</th></tr>
            </thead>
            <tbody>
              <tr v-for="d in diasComCarona" :key="d.dia">
                <td>{{ dataCurtaNumericaSemAno(d.dia) }}</td>
                <td class="text-end">{{ d.total }}</td>
                <td class="text-end">{{ d.concluidas }}</td>
                <td class="text-end">{{ d.canceladas }}</td>
                <td class="text-end">{{ d.outras }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import type { CaronasDoDia } from '../../types/api'
import { diaMes, escalaEixo } from '../../utils/painel'

const props = defineProps<{ dias: CaronasDoDia[] }>()

const foco = ref<number | null>(null)

const total = computed(() => props.dias.reduce((s, d) => s + d.total, 0))
const concluidas = computed(() => props.dias.reduce((s, d) => s + d.concluidas, 0))
const canceladas = computed(() => props.dias.reduce((s, d) => s + d.canceladas, 0))
const escala = computed(() => escalaEixo(Math.max(0, ...props.dias.map((d) => d.total))))
const diasComCarona = computed(() => [...props.dias].reverse().filter((d) => d.total))
const diaEmFoco = computed(() => (foco.value === null ? null : props.dias[foco.value] ?? null))

const DIAS_SEMANA = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']
function dataCurtaNumericaSemAno(iso: string): string {
  const [a, m, d] = iso.split('-').map(Number)
  return `${DIAS_SEMANA[new Date(a!, m! - 1, d!).getDay()]}, ${diaMes(iso)}`
}

// Teclado: setas andam pelos dias (uma parada de Tab so, em vez de 30)
function mover(passo: number): void {
  const atual = foco.value ?? props.dias.length - 1
  foco.value = Math.min(props.dias.length - 1, Math.max(0, atual + passo))
}

const descricao = computed(
  () => `Gráfico de colunas: ${total.value} caronas nos últimos 30 dias, ${concluidas.value} concluídas e ${canceladas.value} canceladas.`
)

// A dica fica sobre a coluna, sem sair pelas bordas do grafico
const posicaoDica = computed(() => {
  const n = props.dias.length || 1
  const centro = ((foco.value ?? 0) + 0.5) / n
  if (centro < 0.2) return { left: '0' }
  if (centro > 0.8) return { right: '0' }
  return { left: `${centro * 100}%`, transform: 'translateX(-50%)' }
})
</script>

<style scoped>
/* Cor validada (dataviz): #2f5fb3 passa na faixa de luminosidade e no contraste 3:1 sobre o fundo do bloco */
.grafico {
  --serie: #2f5fb3;
  --serie-foco: #163f82;
  --grade: rgba(11, 42, 91, 0.1);
}

.resumo-grafico {
  font-size: 0.9rem;
}

.area {
  display: flex;
  gap: 0.5rem;
  height: 160px;
}

.eixo-y {
  position: relative;
  width: 1.5rem;
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--bs-secondary-color);
}

.eixo-y span {
  position: absolute;
  right: 0;
  transform: translateY(50%);
  font-variant-numeric: tabular-nums;
}

.plot {
  position: relative;
  flex: 1;
  min-width: 0;
}

/* Grade: linha fina e discreta, solida */
.grade {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--grade);
}

.colunas {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  gap: 2px; /* espaco de 2 px entre colunas vizinhas */
}

/* O alvo do mouse e o espaco inteiro do dia, nao so a coluna */
.slot {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  cursor: default;
}

.plot:focus-visible {
  outline: 2px solid var(--serie-foco);
  outline-offset: 4px;
  border-radius: 4px;
}

.coluna {
  width: 100%;
  max-width: 24px;
  background: var(--serie);
  border-radius: 4px 4px 0 0; /* ponta arredondada, base reta */
}

.coluna.ativa {
  background: var(--serie-foco);
}

.dica {
  position: absolute;
  top: -0.5rem;
  z-index: 2;
  padding: 0.4rem 0.6rem;
  border-radius: 0.5rem;
  background: #0b2a5b;
  color: #fff;
  font-size: 0.78rem;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.2);
}

.eixo-x {
  display: flex;
  gap: 2px;
  margin-left: 2rem;
  margin-top: 0.3rem;
  font-size: 0.7rem;
  color: var(--bs-secondary-color);
}

.eixo-x span {
  flex: 1;
  min-width: 0;
  overflow: visible;
  white-space: nowrap;
  text-align: center;
}
</style>
