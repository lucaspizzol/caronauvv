<template>
  <!-- Controle de avaliacoes em tempo real (atualiza sozinho a cada 5 s) -->
  <section aria-labelledby="titulo-avaliacoes">
    <!-- titulo e descricao ficam no cabecalho do painel; aqui so o indicador "ao vivo" -->
    <h2 id="titulo-avaliacoes" class="visually-hidden">Controle de avaliações</h2>
    <div class="d-flex justify-content-end mb-2">
      <AoVivo :atualizado-em="atualizadoEm" />
    </div>

    <!-- Alerta na hora: nota abaixo do limite que acabou de chegar -->
    <TransitionGroup name="alerta-nota" tag="div" aria-live="assertive">
      <div v-for="n in novasBaixas" :key="n.id" class="alert alert-danger d-flex align-items-start gap-2 shadow-sm" role="alert">
        <i class="bi bi-exclamation-octagon-fill fs-5"></i>
        <div class="flex-grow-1">
          <strong>Avaliação baixa agora:</strong> nota {{ n.nota }} para
          <RouterLink :to="`/usuarios/${n.avaliado.id}`" class="alert-link">{{ n.avaliado.nome }}</RouterLink> ({{ n.papel_avaliado }}),
          dada por {{ n.avaliador.nome }}<span v-if="n.comentario">: “{{ n.comentario }}”</span>.
          <span v-if="!n.avaliado.is_active" class="badge text-bg-dark ms-1">excluído(a) automaticamente</span>
        </div>
        <button type="button" class="btn-close" aria-label="Fechar aviso" @click="dispensar(n.id)"></button>
      </div>
    </TransitionGroup>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />
    <div v-if="!painel" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <template v-else>
      <!-- Indicadores -->
      <div class="row g-3 mb-3">
        <div class="col-6 col-lg-3">
          <div class="card p-3 h-100 indicador destaque">
            <div class="small text-secondary">Média geral</div>
            <div class="d-flex align-items-baseline gap-2">
              <span class="valor">{{ nota(painel.estatisticas.media_geral) }}</span>
              <Estrelas :valor="painel.estatisticas.media_geral ?? 0" />
            </div>
            <div class="small text-secondary">{{ painel.estatisticas.total }} avaliações no total</div>
          </div>
        </div>
        <div class="col-6 col-lg-3">
          <div class="card p-3 h-100 indicador">
            <div class="small text-secondary">Últimas 24 h</div>
            <div class="valor">{{ painel.estatisticas.ultimas_24h }}</div>
            <div class="small text-secondary">avaliações novas</div>
          </div>
        </div>
        <div class="col-6 col-lg-3">
          <button type="button" :class="['card p-3 h-100 indicador w-100 text-start', { alerta: painel.estatisticas.alertas_abertos }]" @click="emit('abrir', 'alertas')">
            <div class="small text-secondary">Alertas de nota baixa</div>
            <div class="valor">{{ painel.estatisticas.alertas_abertos }}</div>
            <div class="small text-secondary">abertos · ver na aba Alertas <i class="bi bi-arrow-right"></i></div>
          </button>
        </div>
        <div class="col-6 col-lg-3">
          <div :class="['card p-3 h-100 indicador', { alerta: painel.excluidos.length }]">
            <div class="small text-secondary">Excluídos automaticamente</div>
            <div class="valor">{{ painel.excluidos.length }}</div>
            <div class="small text-secondary">por média abaixo de {{ nota(painel.regras.media_minima) }}</div>
          </div>
        </div>
      </div>

      <div class="regras small mb-3">
        <i class="bi bi-sliders me-1"></i>Regras automáticas: nota abaixo de <strong>{{ nota(painel.regras.nota_alerta) }}</strong> gera alerta;
        média abaixo de <strong>{{ nota(painel.regras.media_minima) }}</strong>
        (a partir de {{ painel.regras.minimo_avaliacoes }} {{ painel.regras.minimo_avaliacoes === 1 ? 'avaliação' : 'avaliações' }})
        exclui o aluno do app. Mude na aba <button type="button" class="btn btn-link btn-sm p-0 align-baseline" @click="emit('abrir', 'regras')">Regras</button>.
      </div>

      <div class="row g-3">
        <!-- Feed -->
        <div class="col-lg-8">
          <div class="card h-100">
            <div class="card-header bg-white d-flex flex-wrap justify-content-between align-items-center gap-2">
              <strong><i class="bi bi-broadcast me-1 text-danger"></i>Avaliações em tempo real</strong>
              <div class="form-check form-switch mb-0">
                <input id="so-baixas" v-model="soBaixas" class="form-check-input" type="checkbox" @change="atualizarAgora" />
                <label class="form-check-label small" for="so-baixas">Só notas abaixo de {{ nota(painel.regras.nota_alerta) }}</label>
              </div>
            </div>
            <ul class="list-unstyled mb-0 feed">
              <li v-for="a in painel.avaliacoes" :key="a.id" :class="['item', corDaNota(a.nota), { nova: recentes.has(a.id) }]">
                <div class="d-flex gap-2 align-items-start">
                  <AvatarUsuario :usuario="a.avaliado" :tamanho="2.4" />
                  <div class="flex-grow-1 min-w-0">
                    <div class="d-flex flex-wrap align-items-center gap-2">
                      <RouterLink :to="`/usuarios/${a.avaliado.id}`" class="fw-semibold text-reset">{{ a.avaliado.nome }}</RouterLink>
                      <span class="badge rounded-pill text-bg-light border">{{ a.papel_avaliado }}</span>
                      <span v-if="!a.avaliado.is_active" class="badge rounded-pill text-bg-dark">fora do app</span>
                      <span v-if="!a.revelada" class="badge rounded-pill text-bg-light border" title="O aluno ainda não vê esta nota (avaliação às cegas)"><i class="bi bi-eye-slash me-1"></i>às cegas</span>
                    </div>
                    <div class="small text-secondary">
                      de {{ a.avaliador.nome }} · {{ a.carona.bairro_origem }} → {{ a.carona.destino }} · {{ dataHora(a.criada_em) }}
                    </div>
                    <div v-if="a.comentario" class="mt-1">“{{ a.comentario }}”</div>
                    <div v-if="a.tags.length" class="d-flex flex-wrap gap-1 mt-1">
                      <span v-for="t in a.tags" :key="t" class="badge rounded-pill text-bg-light border fw-normal">{{ t }}</span>
                    </div>
                  </div>
                  <div class="text-end">
                    <div class="nota-grande">{{ a.nota }}</div>
                    <Estrelas :valor="a.nota" pequeno />
                  </div>
                </div>
              </li>
              <li v-if="!painel.avaliacoes.length" class="vazio py-5 text-center text-secondary">
                <i class="bi bi-star d-block fs-2 mb-2"></i>{{ soBaixas ? 'Nenhuma nota baixa. Ótimo sinal!' : 'Nenhuma avaliação ainda.' }}
              </li>
            </ul>
          </div>
        </div>

        <div class="col-lg-4 d-flex flex-column gap-3">
          <!-- Distribuicao das notas -->
          <div class="card p-3">
            <h3 class="h6 fw-bold mb-2">Distribuição das notas</h3>
            <div v-for="n in [5, 4, 3, 2, 1]" :key="n" class="d-flex align-items-center gap-2 mb-1 small">
              <span class="text-nowrap" style="width: 2.4rem">{{ n }} <i class="bi bi-star-fill text-warning"></i></span>
              <div class="progress flex-grow-1" style="height: 10px" role="progressbar" :aria-label="`Notas ${n}`"
                :aria-valuenow="contagem(n)" aria-valuemin="0" :aria-valuemax="painel.estatisticas.total">
                <div :class="['progress-bar', n >= 4 ? 'bg-success' : n === 3 ? 'bg-warning' : 'bg-danger']" :style="{ width: `${percentual(n)}%` }"></div>
              </div>
              <span class="text-end" style="width: 1.8rem">{{ contagem(n) }}</span>
            </div>
          </div>

          <!-- Em risco -->
          <div class="card p-3">
            <h3 class="h6 fw-bold mb-1"><i class="bi bi-graph-down-arrow me-1 text-danger"></i>Alunos em risco</h3>
            <p class="small text-secondary mb-2">Média abaixo de {{ nota(painel.regras.nota_alerta) }}. Abaixo de {{ nota(painel.regras.media_minima) }}, o app exclui.</p>
            <div v-for="u in painel.em_risco" :key="u.id" class="mb-2">
              <div class="d-flex align-items-center gap-2 small">
                <AvatarUsuario :usuario="u" :tamanho="1.8" />
                <RouterLink :to="`/usuarios/${u.id}`" class="fw-semibold text-reset flex-grow-1 text-truncate">{{ u.nome }}</RouterLink>
                <span :class="u.media < painel.regras.media_minima ? 'text-danger fw-bold' : 'text-warning-emphasis fw-semibold'">{{ nota(u.media) }}</span>
                <span class="text-secondary">({{ u.avaliacoes }})</span>
              </div>
              <div class="progress mt-1" style="height: 5px" role="progressbar" :aria-label="`Média de ${u.nome}`">
                <div :class="['progress-bar', u.media < painel.regras.media_minima ? 'bg-danger' : 'bg-warning']" :style="{ width: `${(u.media / 5) * 100}%` }"></div>
              </div>
              <div v-if="!u.is_active" class="small text-danger mt-1"><i class="bi bi-person-x me-1"></i>Fora do app</div>
            </div>
            <p v-if="!painel.em_risco.length" class="small text-success mb-0"><i class="bi bi-check-circle me-1"></i>Ninguém com média baixa.</p>
          </div>

          <!-- Excluidos -->
          <div v-if="painel.excluidos.length" class="card p-3">
            <h3 class="h6 fw-bold mb-2"><i class="bi bi-person-x me-1"></i>Excluídos automaticamente</h3>
            <div v-for="u in painel.excluidos" :key="u.id" class="border rounded-3 p-2 mb-2 small">
              <div class="d-flex align-items-center gap-2">
                <AvatarUsuario :usuario="u" :tamanho="1.8" />
                <span class="fw-semibold flex-grow-1">{{ u.nome }}</span>
                <span v-if="u.is_active" class="badge text-bg-success">reativado</span>
              </div>
              <div class="text-secondary mt-1">{{ u.motivo }}<span v-if="u.suspenso_em"> · {{ dataHora(u.suspenso_em) }}</span></div>
              <BotaoConfirmar v-if="!u.is_active" class="mt-2" texto="Reativar" pergunta="Reativar a conta?" icone="bi-arrow-counterclockwise"
                classe="btn-outline-success" :acao="() => reativar(u.id)" />
            </div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref, type FunctionalComponent } from 'vue'

import { useAoVivo } from '../../composables/useAoVivo'
import api, { mensagemDeErro } from '../../services/api'
import type { TipoAviso } from '../../stores/auth'
import type { AvaliacaoAdmin, PainelAvaliacoes } from '../../types/api'
import { dataHora, nota } from '../../utils/formato'
import AlertaMensagem from '../AlertaMensagem.vue'
import AoVivo from '../AoVivo.vue'
import AvatarUsuario from '../AvatarUsuario.vue'
import BotaoConfirmar from '../BotaoConfirmar.vue'

const emit = defineEmits<{ abrir: [aba: 'alertas' | 'regras'] }>()

/** Estrelas de 0 a 5 (meia estrela para medias como 4,5). */
const Estrelas: FunctionalComponent<{ valor: number; pequeno?: boolean }> = (props) =>
  h(
    'span',
    { class: ['estrelas text-warning text-nowrap', { small: props.pequeno }], 'aria-label': `${nota(props.valor)} de 5 estrelas` },
    [1, 2, 3, 4, 5].map((i) =>
      h('i', { class: ['bi', props.valor >= i ? 'bi-star-fill' : props.valor >= i - 0.5 ? 'bi-star-half' : 'bi-star'], 'aria-hidden': 'true' })
    )
  )
Estrelas.props = ['valor', 'pequeno']

const painel = ref<PainelAvaliacoes | null>(null)
const soBaixas = ref(false)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })
const novasBaixas = ref<AvaliacaoAdmin[]>([]) // alertas na tela (nota baixa que acabou de chegar)
const recentes = reactive(new Set<number>()) // destaque amarelo das avaliacoes novas
let vistas: Set<number> | null = null // ids ja vistos (null = primeira carga, sem alerta)

const corDaNota = (n: number) => (n <= 2 ? 'nota-ruim' : n === 3 ? 'nota-media' : n === 4 ? 'nota-boa' : 'nota-otima')
const contagem = (n: number) => painel.value?.estatisticas.distribuicao[String(n) as '1' | '2' | '3' | '4' | '5'] ?? 0
const percentual = (n: number) => (painel.value?.estatisticas.total ? (contagem(n) / painel.value.estatisticas.total) * 100 : 0)

async function carregar(): Promise<void> {
  const params = soBaixas.value && painel.value ? { nota_maxima: Math.ceil(painel.value.regras.nota_alerta) - 1 } : {}
  const { data } = await api.get<PainelAvaliacoes>('/admin/avaliacoes', { params })
  if (vistas) {
    for (const a of data.avaliacoes.filter((x) => !vistas!.has(x.id))) {
      recentes.add(a.id)
      setTimeout(() => recentes.delete(a.id), 4000)
      if (a.nota < data.regras.nota_alerta) novasBaixas.value = [a, ...novasBaixas.value].slice(0, 3)
    }
  }
  vistas = new Set([...(vistas ?? []), ...data.avaliacoes.map((a) => a.id)])
  painel.value = data
}

function dispensar(id: number): void {
  novasBaixas.value = novasBaixas.value.filter((n) => n.id !== id)
}

async function reativar(id: number): Promise<void> {
  try {
    await api.post(`/admin/usuarios/${id}/suspender`, { ativo: true })
    aviso.texto = 'Conta reativada. O aluno já pode entrar de novo.'
    aviso.tipo = 'success'
    await carregar()
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  }
}

const { atualizadoEm, atualizarAgora } = useAoVivo(carregar)

onMounted(async () => {
  try {
    await carregar()
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
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

.indicador.destaque {
  border-top: 4px solid var(--uvv-amarelo);
}

.indicador.alerta {
  border-top: 4px solid var(--bs-danger);
}

.indicador.alerta .valor {
  color: var(--bs-danger);
}

button.indicador {
  cursor: pointer;
}

button.indicador:hover {
  box-shadow: 0 0.25rem 0.75rem rgba(11, 42, 91, 0.12);
}

.regras {
  background: #f1f4fa;
  border-radius: 0.6rem;
  padding: 0.5rem 0.75rem;
}

.feed {
  max-height: 640px;
  overflow-y: auto;
}

.feed .item {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--bs-border-color);
  border-left: 4px solid transparent;
  transition: background-color 0.6s;
}

.feed .item.nota-ruim {
  border-left-color: var(--bs-danger);
  background: #fff5f5;
}

.feed .item.nota-media {
  border-left-color: var(--bs-warning);
}

.feed .item.nota-boa {
  border-left-color: var(--uvv-azul-2);
}

.feed .item.nota-otima {
  border-left-color: var(--bs-success);
}

.feed .item.nova {
  background: #fff8e1;
}

.nota-grande {
  font-size: 1.6rem;
  font-weight: 800;
  line-height: 1;
  color: var(--uvv-azul);
}

.nota-ruim .nota-grande {
  color: var(--bs-danger);
}

.alerta-nota-enter-active {
  transition: all 0.35s ease;
}

.alerta-nota-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .feed .item,
  .alerta-nota-enter-active {
    transition: none;
  }
}
</style>
