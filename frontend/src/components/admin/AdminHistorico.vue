<template>
  <!-- Historico da administracao: linha do tempo de tudo que foi feito no painel -->
  <section aria-labelledby="titulo-historico">
    <h2 id="titulo-historico" class="visually-hidden">Histórico da administração</h2>

    <div class="filtros mb-3">
      <label class="visually-hidden" for="filtro-acao">Tipo de ação</label>
      <select id="filtro-acao" v-model="filtro" class="form-select form-select-sm">
        <option value="">Todas as ações</option>
        <option v-for="(d, id) in ACOES" :key="id" :value="id">{{ d.filtro }}</option>
      </select>
      <label class="visually-hidden" for="filtro-periodo">Período</label>
      <select id="filtro-periodo" v-model.number="dias" class="form-select form-select-sm">
        <option :value="7">Últimos 7 dias</option>
        <option :value="30">Últimos 30 dias</option>
        <option :value="90">Últimos 90 dias</option>
      </select>
      <span class="contagem small text-secondary">{{ acoes.length }} {{ acoes.length === 1 ? 'registro' : 'registros' }}</span>
    </div>

    <AlertaMensagem :texto="erro" @fechar="erro = ''" />
    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <div v-else-if="!acoes.length" class="vazio">
      <i class="bi bi-clock-history"></i>
      <p class="mb-0">Nenhuma ação {{ filtro ? 'deste tipo ' : '' }}no período.</p>
    </div>

    <div v-else class="linha-do-tempo">
      <section v-for="g in grupos" :key="g.rotulo" class="dia" :aria-label="g.rotulo">
        <h3 class="dia-titulo">{{ g.rotulo }}</h3>
        <ol class="list-unstyled mb-0">
          <li v-for="a in g.acoes" :key="a.id" class="item">
            <span :class="['icone', ACOES[a.acao].cor]" aria-hidden="true"><i :class="['bi', ACOES[a.acao].icone]"></i></span>
            <div class="min-w-0 flex-grow-1">
              <div class="frase">
                <strong :class="{ 'text-secondary': !a.admin }">{{ autorDa(a) }}</strong>
                {{ ACOES[a.acao].verbo }}
                <template v-if="a.alvo">
                  <RouterLink v-if="a.alvo.id" :to="`/usuarios/${a.alvo.id}`" class="fw-semibold">{{ a.alvo.nome }}</RouterLink>
                  <strong v-else>{{ a.alvo.nome }}</strong>
                </template>
              </div>
              <div v-if="a.detalhe" class="detalhe">{{ a.detalhe }}</div>
            </div>
            <time class="horario" :datetime="a.criado_em">{{ hora(a.criado_em) }}</time>
          </li>
        </ol>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import api, { mensagemDeErro } from '../../services/api'
import type { AcaoAdmin, TipoAcaoAdmin } from '../../types/api'
import { hora } from '../../utils/formato'
import { ACOES, agruparPorDia, autorDa } from '../../utils/painel'
import AlertaMensagem from '../AlertaMensagem.vue'

const acoes = ref<AcaoAdmin[]>([])
const filtro = ref<TipoAcaoAdmin | ''>('')
const dias = ref(30)
const carregando = ref(true)
const erro = ref('')

const grupos = computed(() => agruparPorDia(acoes.value))

async function carregar(): Promise<void> {
  carregando.value = true
  erro.value = ''
  try {
    const { data } = await api.get<{ acoes: AcaoAdmin[] }>('/admin/historico', {
      params: { acao: filtro.value || undefined, dias: dias.value }
    })
    acoes.value = data.acoes
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
}

watch([filtro, dias], () => void carregar(), { immediate: true })
</script>

<style scoped>
.filtros {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.filtros .form-select {
  width: auto;
  min-width: 11rem;
}

.contagem {
  margin-left: auto;
}

.vazio {
  text-align: center;
  padding: 2.5rem 1rem;
  border-radius: 1rem;
  background: #eef3fa;
  color: var(--bs-secondary-color);
}

.vazio i {
  display: block;
  font-size: 2rem;
  margin-bottom: 0.25rem;
}

.linha-do-tempo {
  display: grid;
  gap: 1rem;
}

.dia {
  padding: 0.9rem 1.1rem 0.4rem;
  border-radius: 1rem;
  background: #eef3fa;
}

.dia-titulo {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--bs-secondary-color);
  margin-bottom: 0.5rem;
}

.item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.6rem 0;
  border-top: 1px solid rgba(11, 42, 91, 0.08);
}

.item:first-child {
  border-top: 0;
}

.icone {
  flex-shrink: 0;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 0.65rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.icone.verde { background: #e1f4e8; color: #198754; }
.icone.vermelho { background: #fbe3e5; color: #c42b3a; }
.icone.amarelo { background: #fff3cd; color: #946c00; }
.icone.azul { background: #e3ecfb; color: var(--uvv-azul-2); }

.frase {
  line-height: 1.35;
}

.detalhe {
  font-size: 0.82rem;
  color: var(--bs-secondary-color);
  overflow-wrap: anywhere;
}

.horario {
  flex-shrink: 0;
  font-size: 0.8rem;
  color: var(--bs-secondary-color);
  font-variant-numeric: tabular-nums;
}

.min-w-0 {
  min-width: 0;
}

@media (max-width: 575.98px) {
  .filtros .form-select {
    flex: 1;
    min-width: 0;
  }

  .contagem {
    flex-basis: 100%;
    margin-left: 0;
  }
}
</style>
