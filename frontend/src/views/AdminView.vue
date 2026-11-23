<template>
  <div class="container py-4">
    <h1 class="titulo-pagina h3 mb-1">Painel da administração</h1>
    <p class="text-secondary">Indicadores, moderação, segurança e regras do CaronaUVV.</p>

    <ul class="nav nav-pills mb-3 flex-nowrap overflow-auto">
      <li v-for="a in ABAS" :key="a.id" class="nav-item">
        <button :class="['nav-link text-nowrap', { active: aba === a.id }]" @click="trocarAba(a.id)">
          <i :class="['bi me-1', a.icone]"></i>{{ a.texto }}
          <span v-if="a.id === 'usuarios' && r?.usuarios.verificacoes_pendentes" class="badge text-bg-warning ms-1">{{ r.usuarios.verificacoes_pendentes }}</span>
          <span v-if="a.id === 'denuncias' && r?.confianca.denuncias_abertas" class="badge text-bg-danger ms-1">{{ r.confianca.denuncias_abertas }}</span>
          <span v-if="a.id === 'alertas' && r?.confianca.alertas_aguardando" class="badge text-bg-danger ms-1">{{ r.confianca.alertas_aguardando }}</span>
        </button>
      </li>
    </ul>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />
    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <!-- ===================== VISAO GERAL ===================== -->
    <template v-else-if="aba === 'resumo' && r">
      <div class="row g-3">
        <div v-for="k in kpis" :key="k.rotulo" class="col-6 col-lg-3">
          <div :class="['card p-3 h-100 kpi', k.classe]">
            <div class="small text-secondary">{{ k.rotulo }}</div>
            <div class="valor">{{ k.valor }}</div>
            <div class="small text-secondary">{{ k.detalhe }}</div>
          </div>
        </div>
      </div>
      <div class="row g-3 mt-1">
        <div class="col-md-6">
          <div class="card p-3 h-100">
            <h2 class="h6 fw-bold"><i class="bi bi-search me-1"></i>Demanda sem oferta (30 dias)</h2>
            <p class="small text-secondary">Bairros que os alunos buscaram e não acharam carona. Bom lugar para incentivar motoristas.</p>
            <p v-if="!r.demanda_sem_oferta.length" class="small mb-0">Nenhuma busca sem resultado.</p>
            <div v-for="d in r.demanda_sem_oferta" :key="d.bairro" class="mb-2">
              <div class="d-flex justify-content-between small"><span>{{ d.bairro }}</span><strong>{{ d.buscas }}</strong></div>
              <div class="progress" style="height: 6px" role="progressbar" :aria-label="`Buscas em ${d.bairro}`">
                <div class="progress-bar bg-danger" :style="{ width: `${(d.buscas / maxDemanda) * 100}%` }"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card p-3 h-100">
            <h2 class="h6 fw-bold"><i class="bi bi-geo-alt me-1"></i>Bairros com mais caronas oferecidas</h2>
            <div v-for="d in r.bairros_com_mais_oferta" :key="d.bairro" class="mb-2">
              <div class="d-flex justify-content-between small"><span>{{ d.bairro }}</span><strong>{{ d.caronas }}</strong></div>
              <div class="progress" style="height: 6px" role="progressbar" :aria-label="`Caronas em ${d.bairro}`">
                <div class="progress-bar" :style="{ width: `${(d.caronas / maxOferta) * 100}%` }"></div>
              </div>
            </div>
            <h2 class="h6 fw-bold mt-3">Caronas por status</h2>
            <div class="d-flex flex-wrap gap-2">
              <span v-for="(n, status) in r.caronas.por_status" :key="status" class="d-inline-flex align-items-center gap-1">
                <StatusBadge :status="status" /> <strong class="small">{{ n }}</strong>
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ===================== USUARIOS ===================== -->
    <template v-else-if="aba === 'usuarios'">
      <form class="d-flex gap-2 mb-3" @submit.prevent="carregarUsuarios">
        <input v-model.trim="busca" class="form-control" placeholder="Nome, e-mail ou matrícula" aria-label="Buscar usuário" />
        <div class="form-check form-switch align-self-center text-nowrap">
          <input id="so-pend" v-model="soPendentes" class="form-check-input" type="checkbox" @change="carregarUsuarios" />
          <label class="form-check-label small" for="so-pend">Só pedidos de verificação</label>
        </div>
        <button class="btn btn-primary"><i class="bi bi-search"></i></button>
      </form>
      <div class="card">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0 small">
            <thead><tr><th>Aluno</th><th>Matrícula</th><th>Situação</th><th class="text-end">Ações</th></tr></thead>
            <tbody>
              <tr v-for="u in usuarios" :key="u.id">
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <AvatarUsuario :usuario="u" :tamanho="2.2" />
                    <div>
                      <RouterLink :to="`/usuarios/${u.id}`" class="fw-semibold">{{ u.nome }}</RouterLink>
                      <div class="text-secondary">{{ u.email }}</div>
                    </div>
                  </div>
                </td>
                <td class="font-monospace">{{ u.matricula }}</td>
                <td>
                  <span v-if="!u.is_active" class="badge text-bg-danger">Suspenso</span>
                  <span v-else-if="u.verificado" class="badge text-bg-primary"><i class="bi bi-patch-check-fill me-1"></i>Verificado</span>
                  <span v-else-if="u.verificacao_solicitada_em" class="badge text-bg-warning">Pediu verificação</span>
                  <span v-else class="badge text-bg-light border">Comum</span>
                  <span v-if="!u.email_verificado" class="badge text-bg-light border ms-1">e-mail pendente</span>
                  <span v-if="u.is_admin" class="badge text-bg-dark ms-1">admin</span>
                  <span v-if="u.dois_fatores" class="badge text-bg-light border ms-1" title="Usa aplicativo autenticador"><i class="bi bi-shield-lock-fill me-1"></i>2 etapas</span>
                </td>
                <td class="text-end text-nowrap">
                  <button v-if="u.verificacao_solicitada_em && !u.verificado" class="btn btn-sm btn-success me-1" @click="verificar(u, true)">Aprovar selo</button>
                  <button v-if="u.verificacao_solicitada_em && !u.verificado" class="btn btn-sm btn-light me-1" @click="verificar(u, false)">Recusar</button>
                  <BotaoConfirmar v-if="u.foto_url" class="me-1" texto="Remover foto" pergunta="Remover a foto?" icone="bi-person-x" classe="btn-outline-secondary" :acao="() => removerFoto(u)" />
                  <BotaoConfirmar v-if="u.dois_fatores && u.id !== auth.usuario?.id" class="me-1" texto="Desligar 2 etapas" pergunta="Desligar o autenticador dele(a)?" icone="bi-shield-x" classe="btn-outline-secondary" :acao="() => resetar2fa(u)" />
                  <button v-if="u.is_active && !u.is_admin" class="btn btn-sm btn-outline-danger" @click="suspender(u, false)">Suspender</button>
                  <button v-if="!u.is_active" class="btn btn-sm btn-outline-success" @click="suspender(u, true)">Reativar</button>
                </td>
              </tr>
              <tr v-if="!usuarios.length"><td colspan="4" class="text-center text-secondary py-4">Nenhum usuário encontrado.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- ===================== DENUNCIAS ===================== -->
    <template v-else-if="aba === 'denuncias'">
      <div v-if="!denuncias.length" class="card vazio"><i class="bi bi-flag"></i><p class="mb-0">Nenhuma denúncia.</p></div>
      <div v-for="d in denuncias" :key="d.id" class="card p-3 mb-3">
        <div class="d-flex flex-wrap justify-content-between gap-2">
          <div>
            <span :class="['badge me-2', d.status === 'encerrada' ? 'text-bg-secondary' : 'text-bg-danger']">{{ d.status.replace('_', ' ') }}</span>
            <strong>{{ textoMotivo(d.motivo) }}</strong>
          </div>
          <span class="small text-secondary">{{ dataHora(d.criada_em) }}</span>
        </div>
        <div class="small mt-2">
          <RouterLink :to="`/usuarios/${d.denunciante.id}`">{{ d.denunciante.nome }}</RouterLink> denunciou
          <RouterLink :to="`/usuarios/${d.denunciado.id}`" class="fw-semibold">{{ d.denunciado.nome }}</RouterLink>
          <span v-if="!d.denunciado.is_active" class="badge text-bg-danger ms-1">suspenso</span>
          <span v-if="d.carona_id" class="text-secondary"> · carona #{{ d.carona_id }}</span>
        </div>
        <div v-if="d.descricao" class="small fst-italic mt-1">"{{ d.descricao }}"</div>
        <div v-if="d.resolucao" class="small mt-2"><strong>Resolução:</strong> {{ d.resolucao }}</div>

        <form v-if="d.status !== 'encerrada'" class="row g-2 mt-2" @submit.prevent="analisar(d)">
          <div class="col-md-6">
            <input v-model.trim="resolucoes[d.id]" class="form-control form-control-sm" placeholder="Resolução (obrigatória para encerrar)" aria-label="Resolução" />
          </div>
          <div class="col-md-6 d-flex flex-wrap gap-2 align-items-center">
            <div class="form-check">
              <input :id="`susp-${d.id}`" v-model="suspensoes[d.id]" class="form-check-input" type="checkbox" />
              <label class="form-check-label small" :for="`susp-${d.id}`">Suspender o denunciado</label>
            </div>
            <button type="button" class="btn btn-sm btn-light" @click="analisar(d, 'em_analise')">Em análise</button>
            <button class="btn btn-sm btn-primary">Encerrar</button>
          </div>
        </form>
      </div>
    </template>

    <!-- ===================== ALERTAS ===================== -->
    <template v-else-if="aba === 'alertas'">
      <div v-if="!alertas.length" class="card vazio"><i class="bi bi-shield-check"></i><p class="mb-0">Nenhum alerta.</p></div>
      <div v-for="a in alertas" :key="a.id" :class="['card p-3 mb-2', { 'border border-danger': a.status !== 'resolvido' }]">
        <div class="d-flex flex-wrap justify-content-between gap-2">
          <div>
            <i :class="['bi me-1', a.tipo === 'botao_panico' ? 'bi-exclamation-octagon-fill text-danger' : 'bi-exclamation-triangle-fill text-warning']"></i>
            <strong>{{ a.tipo === 'botao_panico' ? 'Botão de emergência' : a.tipo.replace('_', ' ') }}</strong>
            <span class="small text-secondary"> · carona #{{ a.carona_id }} · {{ dataHora(a.criado_em) }}</span>
          </div>
          <span :class="['badge', a.status === 'resolvido' ? 'text-bg-success' : 'text-bg-danger']">{{ a.status }}</span>
        </div>
        <div class="small mt-1">
          <span v-if="a.usuario">{{ a.usuario.nome }}: </span>{{ a.detalhe }}
          <a v-if="a.lat" :href="`https://www.openstreetmap.org/?mlat=${a.lat}&mlon=${a.lng}#map=16/${a.lat}/${a.lng}`" target="_blank" rel="noopener" class="ms-1">ver no mapa</a>
        </div>
        <div v-if="a.status !== 'resolvido'" class="mt-2">
          <button class="btn btn-sm btn-success" @click="resolver(a)"><i class="bi bi-check2 me-1"></i>Marcar como resolvido</button>
        </div>
      </div>
    </template>

    <!-- ===================== REGRAS ===================== -->
    <template v-else-if="aba === 'regras'">
      <form class="card p-4" @submit.prevent="salvarConfiguracoes">
        <p class="small text-secondary">Valores usados pelas regras de negócio (rateio máximo, prazos e segurança). Mudam na hora, sem reiniciar.</p>
        <div v-for="c in configuracoes" :key="c.chave" class="row g-2 align-items-center mb-2">
          <label class="col-md-8 small" :for="`cfg-${c.chave}`">{{ c.descricao }} <span class="text-secondary font-monospace">({{ c.chave }})</span></label>
          <div class="col-md-4"><input :id="`cfg-${c.chave}`" v-model="c.valor" class="form-control form-control-sm" inputmode="decimal" /></div>
        </div>
        <div class="text-end"><button class="btn btn-primary">Salvar regras</button></div>
      </form>
    </template>

    <!-- ===================== BANCO DE DADOS ===================== -->
    <template v-else-if="aba === 'banco' && banco">
      <div class="card p-3 mb-3">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div>
            <strong>Banco:</strong> {{ banco.banco === 'postgresql' ? 'PostgreSQL' : 'SQLite' }} ·
            <strong>{{ banco.tabelas.length }}</strong> tabelas ·
            <strong>{{ totalLinhas }}</strong> registros ·
            migração <span class="font-monospace">{{ banco.versao_migracao || '—' }}</span>
          </div>
          <div class="btn-group btn-group-sm">
            <button :class="['btn', diagramaCompleto ? 'btn-outline-primary' : 'btn-primary']" @click="desenhar(false)">Só chaves</button>
            <button :class="['btn', diagramaCompleto ? 'btn-primary' : 'btn-outline-primary']" @click="desenhar(true)">Todas as colunas</button>
            <button :class="['btn', ampliado ? 'btn-dark' : 'btn-outline-dark']" @click="ampliado = !ampliado; desenhar(diagramaCompleto)">
              <i :class="['bi', ampliado ? 'bi-zoom-out' : 'bi-zoom-in']"></i> {{ ampliado ? 'Caber na tela' : 'Ampliar' }}
            </button>
          </div>
        </div>
        <p class="small text-secondary mb-0 mt-1">Diagrama gerado agora, a partir dos modelos do SQLAlchemy (mesma fonte das migrações).</p>
      </div>
      <div class="card p-3 mb-3 diagrama-er">
        <div v-if="desenhando" class="text-center py-4"><span class="spinner-border text-primary"></span></div>
        <div ref="diagrama"></div>
      </div>
      <div class="row g-3">
        <div v-for="t in banco.tabelas" :key="t.nome" class="col-md-6 col-xl-4">
          <div class="card h-100">
            <div class="card-header d-flex justify-content-between bg-white">
              <span class="fw-bold font-monospace">{{ t.nome }}</span>
              <span class="badge text-bg-light border">{{ t.linhas }} {{ t.linhas === 1 ? 'linha' : 'linhas' }}</span>
            </div>
            <ul class="list-group list-group-flush small">
              <li v-for="c in t.colunas" :key="c.nome" class="list-group-item d-flex justify-content-between py-1">
                <span class="font-monospace">
                  <i v-if="c.pk" class="bi bi-key-fill text-warning me-1" title="Chave primária"></i>
                  <i v-else-if="c.fk" class="bi bi-link-45deg text-primary me-1" :title="`Chave estrangeira para ${c.fk}`"></i>
                  {{ c.nome }}<span v-if="c.obrigatorio && !c.pk" class="text-danger" title="Obrigatório">*</span>
                </span>
                <span class="text-secondary">{{ c.fk ? `→ ${c.fk}` : c.tipo.toLowerCase() }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import AvatarUsuario from '../components/AvatarUsuario.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import api, { mensagemDeErro } from '../services/api'
import { auth, type TipoAviso } from '../stores/auth'
import type { Alerta, Configuracao, Denuncia, EstruturaBanco, ResumoAdmin, UsuarioAdmin } from '../types/api'
import { dataHora, nota, porcentagem, textoMotivo } from '../utils/formato'

type IdAba = 'resumo' | 'usuarios' | 'denuncias' | 'alertas' | 'regras' | 'banco'

const ABAS: { id: IdAba; texto: string; icone: string }[] = [
  { id: 'resumo', texto: 'Visão geral', icone: 'bi-speedometer2' },
  { id: 'usuarios', texto: 'Usuários', icone: 'bi-people' },
  { id: 'denuncias', texto: 'Denúncias', icone: 'bi-flag' },
  { id: 'alertas', texto: 'Alertas', icone: 'bi-shield-exclamation' },
  { id: 'regras', texto: 'Regras', icone: 'bi-sliders' },
  { id: 'banco', texto: 'Banco de dados', icone: 'bi-database' }
]

/** Cartao de indicador da visao geral. */
interface Kpi {
  rotulo: string
  valor: string | number
  detalhe: string
  classe?: '' | 'verde' | 'alerta'
}

const aba = ref<IdAba>('resumo')
const carregando = ref(true)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

const r = ref<ResumoAdmin | null>(null)
const usuarios = ref<UsuarioAdmin[]>([])
const busca = ref('')
const soPendentes = ref(false)
const denuncias = ref<Denuncia[]>([])
const resolucoes = reactive<Record<number, string>>({})
const suspensoes = reactive<Record<number, boolean>>({})
const alertas = ref<Alerta[]>([])
const configuracoes = ref<Configuracao[]>([])
const banco = ref<EstruturaBanco | null>(null)
const diagrama = ref<HTMLElement | null>(null)
const diagramaCompleto = ref(false)
const desenhando = ref(false)
const ampliado = ref(false)

const decimal = (n: number | null | undefined) => Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })

function avisar(texto: string, tipo: TipoAviso = 'success'): void {
  aviso.texto = texto
  aviso.tipo = tipo
}

const kpis = computed<Kpi[]>(() => {
  if (!r.value) return []
  const { usuarios: u, viagens: v, confianca: c } = r.value
  return [
    { rotulo: 'Alunos cadastrados', valor: u.total, detalhe: `${u.ativos_30_dias} ativos nos últimos 30 dias` },
    { rotulo: 'Viagens concluídas', valor: v.concluidas, detalhe: `${v.passageiros_transportados} passageiros levados`, classe: 'verde' },
    { rotulo: 'Ocupação dos carros', valor: porcentagem(v.taxa_ocupacao), detalhe: 'assentos usados nas viagens' },
    { rotulo: 'CO₂ evitado', valor: `${decimal(v.co2_evitado_kg)} kg`, detalhe: `${decimal(v.km_compartilhados)} km compartilhados`, classe: 'verde' },
    { rotulo: 'Nota média', valor: nota(c.nota_media), detalhe: `${c.avaliacoes} avaliações` },
    { rotulo: 'Faltas', valor: porcentagem(v.taxa_faltas), detalhe: 'das vagas confirmadas' },
    { rotulo: 'Denúncias abertas', valor: c.denuncias_abertas, detalhe: 'aguardando análise', classe: c.denuncias_abertas ? 'alerta' : '' },
    { rotulo: 'Alertas de segurança', valor: c.alertas_aguardando, detalhe: 'sem resolução', classe: c.alertas_aguardando ? 'alerta' : '' }
  ]
})
const maxDemanda = computed(() => Math.max(1, ...(r.value?.demanda_sem_oferta || []).map((d) => d.buscas)))
const maxOferta = computed(() => Math.max(1, ...(r.value?.bairros_com_mais_oferta || []).map((d) => d.caronas)))
const totalLinhas = computed(() => (banco.value?.tabelas || []).reduce((s, t) => s + t.linhas, 0))

async function carregarResumo(): Promise<void> {
  const { data } = await api.get<{ resumo: ResumoAdmin }>('/admin/resumo')
  r.value = data.resumo
}

async function carregarUsuarios(): Promise<void> {
  const { data } = await api.get<{ usuarios: UsuarioAdmin[] }>('/admin/usuarios', {
    params: { busca: busca.value, pendentes: soPendentes.value ? 1 : 0 }
  })
  usuarios.value = data.usuarios
}

// Cada aba sabe carregar os proprios dados. `Record<IdAba, ...>` garante que nenhuma aba fique sem carregador.
const CARREGADORES: Record<IdAba, () => Promise<unknown>> = {
  resumo: carregarResumo,
  usuarios: carregarUsuarios,
  denuncias: async () => (denuncias.value = (await api.get<{ denuncias: Denuncia[] }>('/admin/denuncias')).data.denuncias),
  alertas: async () => (alertas.value = (await api.get<{ alertas: Alerta[] }>('/admin/alertas')).data.alertas),
  regras: async () =>
    (configuracoes.value = (await api.get<{ configuracoes: Configuracao[] }>('/admin/configuracoes')).data.configuracoes),
  banco: async () => {
    banco.value = (await api.get<EstruturaBanco>('/admin/banco')).data
  }
}

async function trocarAba(id: IdAba): Promise<void> {
  aba.value = id
  carregando.value = true
  aviso.texto = ''
  try {
    await Promise.all([CARREGADORES[id](), id === 'resumo' ? null : carregarResumo()])
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    carregando.value = false
  }
  if (id === 'banco') {
    await nextTick()
    await desenhar(diagramaCompleto.value)
  }
}

async function verificar(u: UsuarioAdmin, aprovado: boolean): Promise<void> {
  try {
    await api.post(`/admin/usuarios/${u.id}/verificar`, { aprovado })
    avisar(aprovado ? `${u.nome} agora tem o selo de verificado.` : 'Pedido de verificação recusado.')
    await Promise.all([carregarUsuarios(), carregarResumo()])
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

// Moderacao: foto inadequada
async function removerFoto(u: UsuarioAdmin): Promise<void> {
  try {
    await api.delete(`/admin/usuarios/${u.id}/foto`)
    avisar(`A foto de ${u.nome} foi removida e ele(a) foi avisado(a).`)
    await carregarUsuarios()
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

// Aluno ficou sem o celular e sem os codigos de reserva
async function resetar2fa(u: UsuarioAdmin): Promise<void> {
  try {
    await api.post(`/admin/usuarios/${u.id}/resetar-2fa`)
    avisar(`A verificação em duas etapas de ${u.nome} foi desligada. Agora ele(a) entra só com a senha.`, 'warning')
    await carregarUsuarios()
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function suspender(u: UsuarioAdmin, ativo: boolean): Promise<void> {
  try {
    await api.post(`/admin/usuarios/${u.id}/suspender`, { ativo })
    avisar(ativo ? `${u.nome} foi reativado.` : `${u.nome} foi suspenso e as caronas futuras dele foram canceladas.`, ativo ? 'success' : 'warning')
    await carregarUsuarios()
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function analisar(d: Denuncia, status: 'encerrada' | 'em_analise' = 'encerrada'): Promise<void> {
  try {
    await api.post(`/admin/denuncias/${d.id}`, { status, resolucao: resolucoes[d.id] || '', suspender: Boolean(suspensoes[d.id]) })
    avisar(status === 'encerrada' ? 'Denúncia encerrada.' : 'Denúncia marcada como em análise.')
    await Promise.all([CARREGADORES.denuncias(), carregarResumo()])
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function resolver(a: Alerta): Promise<void> {
  try {
    await api.post(`/admin/alertas/${a.id}/resolver`)
    await Promise.all([CARREGADORES.alertas(), carregarResumo()])
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function salvarConfiguracoes(): Promise<void> {
  try {
    const valores = Object.fromEntries(configuracoes.value.map((c) => [c.chave, c.valor]))
    const { data } = await api.put<{ configuracoes: Configuracao[] }>('/admin/configuracoes', valores)
    configuracoes.value = data.configuracoes
    avisar('Regras salvas. Já valem para as próximas caronas.')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

// ==========================================================
// DIAGRAMA ER (Mermaid) montado a partir de /api/admin/banco
// ==========================================================
function codigoMermaid(estrutura: EstruturaBanco, completo: boolean): string {
  const linhas = ['erDiagram']
  for (const t of estrutura.tabelas) {
    const colunas = t.colunas.filter((c) => completo || c.pk || c.fk)
    linhas.push(`  ${t.nome} {`)
    for (const c of colunas) {
      const chave = c.pk ? ' PK' : c.fk ? ' FK' : ''
      linhas.push(`    ${c.tipo.toLowerCase().replace(/[^a-z]/g, '') || 'texto'} ${c.nome}${chave}`)
    }
    linhas.push('  }')
  }
  for (const t of estrutura.tabelas) {
    for (const c of t.colunas) {
      if (!c.fk) continue
      const alvo = c.fk.split('.')[0]
      const cardinalidade = c.obrigatorio ? '||--o{' : '|o--o{'
      linhas.push(`  ${alvo} ${cardinalidade} ${t.nome} : "${c.nome}"`)
    }
  }
  return linhas.join('\n')
}

async function desenhar(completo: boolean): Promise<void> {
  diagramaCompleto.value = completo
  if (!banco.value || !diagrama.value) return
  desenhando.value = true
  try {
    const mermaid = (await import('mermaid')).default // ~1 MB, carregado so nesta aba
    // useMaxWidth: o diagrama encolhe para caber na tela (bom para projetar na apresentacao)
    mermaid.initialize({ startOnLoad: false, theme: 'neutral', er: { useMaxWidth: !ampliado.value } })
    const { svg } = await mermaid.render(`er-${Date.now()}`, codigoMermaid(banco.value, completo))
    diagrama.value.innerHTML = svg
  } catch (e) {
    avisar(`Não foi possível desenhar o diagrama: ${mensagemDeErro(e, String(e))}`, 'warning')
  } finally {
    desenhando.value = false
  }
}

onMounted(() => trocarAba('resumo'))
</script>
