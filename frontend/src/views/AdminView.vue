<template>
  <div>
    <!-- Cabecalho da secao (o menu lateral fica no AdminShell) -->
    <header class="secao-topo mb-3">
      <div class="min-w-0">
        <h1 class="h3 fw-bold mb-1"><i :class="['bi me-2', secao.icone]"></i>{{ secao.texto }}</h1>
        <p class="text-secondary mb-0">{{ secao.descricao }}</p>
      </div>
      <div v-if="r" class="d-flex flex-wrap gap-2">
        <RouterLink to="/admin/aovivo" class="chip-topo">
          <span class="ponto" :class="{ ativo: r.viagens.em_andamento_agora }"></span>{{ r.viagens.em_andamento_agora }} em viagem agora
        </RouterLink>
        <RouterLink to="/admin/avaliacoes" class="chip-topo">
          <i class="bi bi-star-fill text-warning"></i>média {{ nota(r.confianca.nota_media) }}
        </RouterLink>
        <RouterLink to="/admin/alertas" :class="['chip-topo', { perigo: r.confianca.alertas_aguardando }]">
          <i class="bi bi-bell-fill"></i>{{ r.confianca.alertas_aguardando }} {{ r.confianca.alertas_aguardando === 1 ? 'alerta' : 'alertas' }}
        </RouterLink>
      </div>
    </header>

    <!-- Alerta em qualquer secao: chegou avaliacao abaixo do limite -->
    <div v-if="novaNotaBaixa && aba !== 'avaliacoes'" class="alert alert-danger d-flex flex-wrap align-items-center gap-2 shadow-sm" role="alert" aria-live="assertive">
      <i class="bi bi-exclamation-octagon-fill fs-5"></i>
      <span class="flex-grow-1"><strong>Nova avaliação baixa.</strong> {{ novaNotaBaixa }}</span>
      <button type="button" class="btn btn-sm btn-danger" @click="novaNotaBaixa = ''; trocarAba('avaliacoes')">Ver avaliações</button>
      <button type="button" class="btn-close" aria-label="Fechar aviso" @click="novaNotaBaixa = ''"></button>
    </div>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />
    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <!-- ===================== VISAO GERAL ===================== -->
    <template v-else-if="aba === 'resumo' && r">
      <!-- 4 numeros principais -->
      <div class="row g-3 mb-3">
        <div v-for="d in destaques" :key="d.rotulo" class="col-6 col-lg-3">
          <div class="destaque h-100">
            <span :class="['icone-destaque', d.cor]"><i :class="['bi', d.icone]"></i></span>
            <div class="min-w-0">
              <div class="rotulo">{{ d.rotulo }}</div>
              <div class="numero">{{ d.valor }}</div>
              <div class="detalhe">{{ d.detalhe }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <!-- Viagens: metricas agrupadas num bloco so -->
        <div class="col-lg-7">
          <section class="bloco h-100" aria-labelledby="t-viagens">
            <h2 id="t-viagens" class="bloco-titulo"><i class="bi bi-car-front-fill"></i>Viagens</h2>
            <div class="metricas">
              <div v-for="m in metricasViagem" :key="m.rotulo" class="metrica">
                <i :class="['bi', m.icone]"></i>
                <div>
                  <div class="valor-m">{{ m.valor }}</div>
                  <div class="rotulo-m">{{ m.rotulo }}</div>
                </div>
              </div>
            </div>
            <div class="d-flex flex-wrap align-items-center gap-2 mt-3 small">
              <span class="text-secondary">Caronas por status:</span>
              <span v-for="(n, status) in r.caronas.por_status" :key="status" class="d-inline-flex align-items-center gap-1">
                <StatusBadge :status="status" /><strong>{{ n }}</strong>
              </span>
            </div>
          </section>
        </div>

        <!-- O que precisa de acao (so aparece o que tem pendencia) -->
        <div class="col-lg-5">
          <section class="bloco h-100" aria-labelledby="t-atencao">
            <h2 id="t-atencao" class="bloco-titulo"><i class="bi bi-bell-fill"></i>Precisa de atenção</h2>
            <button v-for="p in pendencias" :key="p.texto" type="button" class="pendencia" @click="trocarAba(p.aba)">
              <span :class="['icone-pendencia', p.cor]"><i :class="['bi', p.icone]"></i></span>
              <span class="flex-grow-1 text-start">{{ p.texto }}</span>
              <span :class="['badge rounded-pill', p.cor === 'verde' ? 'text-bg-success' : p.cor === 'amarelo' ? 'text-bg-warning' : 'text-bg-danger']">{{ p.n }}</span>
              <i class="bi bi-chevron-right text-secondary"></i>
            </button>
            <div v-if="!pendencias.length" class="tudo-em-dia">
              <i class="bi bi-check-circle-fill"></i>Tudo em dia: nenhuma pendência agora.
            </div>
          </section>
        </div>

        <!-- Grafico: caronas por dia nos ultimos 30 dias -->
        <div class="col-12">
          <section class="bloco" aria-labelledby="t-grafico">
            <h2 id="t-grafico" class="bloco-titulo"><i class="bi bi-bar-chart-fill"></i>Caronas por dia</h2>
            <GraficoCaronas :dias="r.caronas_por_dia" />
          </section>
        </div>

        <!-- Bairros: onde falta carona x onde mais tem -->
        <div class="col-12">
          <section class="bloco" aria-labelledby="t-bairros">
            <h2 id="t-bairros" class="bloco-titulo"><i class="bi bi-geo-alt-fill"></i>Bairros nos últimos 30 dias</h2>
            <div class="row g-4">
              <div class="col-md-6">
                <div class="subtitulo">Procuraram e não acharam carona <span class="text-secondary fw-normal">(bom lugar para incentivar motoristas)</span></div>
                <div v-for="d in r.demanda_sem_oferta" :key="d.bairro" class="barra-linha">
                  <span class="nome">{{ d.bairro }}</span>
                  <div class="barra"><div class="preenchido perigo" :style="{ width: `${(d.buscas / maxDemanda) * 100}%` }"></div></div>
                  <strong>{{ d.buscas }}</strong>
                </div>
                <p v-if="!r.demanda_sem_oferta.length" class="small text-success mb-0"><i class="bi bi-check-circle me-1"></i>Ninguém ficou sem carona.</p>
              </div>
              <div class="col-md-6">
                <div class="subtitulo">Mais caronas oferecidas</div>
                <div v-for="d in r.bairros_com_mais_oferta" :key="d.bairro" class="barra-linha">
                  <span class="nome">{{ d.bairro }}</span>
                  <div class="barra"><div class="preenchido" :style="{ width: `${(d.caronas / maxOferta) * 100}%` }"></div></div>
                  <strong>{{ d.caronas }}</strong>
                </div>
                <p v-if="!r.bairros_com_mais_oferta.length" class="small text-secondary mb-0">Nenhuma carona oferecida ainda.</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>

    <!-- ===================== AO VIVO (todas as viagens com GPS) ===================== -->
    <AdminAoVivo v-else-if="aba === 'aovivo'" />

    <!-- ===================== CONTROLE DE AVALIACOES ===================== -->
    <AdminAvaliacoes v-else-if="aba === 'avaliacoes'" @abrir="trocarAba" />

    <!-- ===================== HISTORICO E EXPORTAR ===================== -->
    <AdminHistorico v-else-if="aba === 'historico'" />
    <AdminExportar v-else-if="aba === 'exportar'" />

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
            <thead><tr><th>Aluno</th><th>Matrícula</th><th>Média</th><th>Situação</th><th class="text-end">Ações</th></tr></thead>
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
                <td class="text-nowrap">
                  <template v-if="u.media_recebida !== null">
                    <span :class="u.media_recebida < 3 ? 'text-danger fw-bold' : u.media_recebida < 4 ? 'text-warning-emphasis fw-semibold' : ''">
                      <i class="bi bi-star-fill text-warning"></i> {{ nota(u.media_recebida) }}
                    </span>
                    <span class="text-secondary">({{ u.avaliacoes_recebidas }})</span>
                  </template>
                  <span v-else class="text-secondary">—</span>
                </td>
                <td>
                  <span v-if="!u.is_active" class="badge text-bg-danger">Suspenso</span>
                  <span v-else-if="u.verificado" class="badge text-bg-primary"><i class="bi bi-patch-check-fill me-1"></i>Verificado</span>
                  <span v-else-if="u.verificacao_solicitada_em" class="badge text-bg-warning">Pediu verificação</span>
                  <span v-else class="badge text-bg-light border">Comum</span>
                  <span v-if="!u.email_verificado" class="badge text-bg-light border ms-1">e-mail pendente</span>
                  <span v-if="u.is_admin" class="badge text-bg-dark ms-1">admin</span>
                  <span v-if="u.dois_fatores" class="badge text-bg-light border ms-1" title="Usa aplicativo autenticador"><i class="bi bi-shield-lock-fill me-1"></i>2 etapas</span>
                  <div v-if="!u.is_active && u.suspenso_motivo" class="text-danger mt-1" style="max-width: 18rem">{{ u.suspenso_motivo }}</div>
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
              <tr v-if="!usuarios.length"><td colspan="5" class="text-center text-secondary py-4">Nenhum usuário encontrado.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- ===================== DOCUMENTOS (identidade e CNH) ===================== -->
    <template v-else-if="aba === 'documentos'">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
        <div class="btn-group btn-group-sm" role="group" aria-label="Filtrar documentos">
          <button v-for="f in FILTROS_DOC" :key="f.id" :class="['btn', filtroDoc === f.id ? 'btn-primary' : 'btn-outline-primary']" @click="trocarFiltroDoc(f.id)">
            {{ f.texto }}
          </button>
        </div>
        <span class="small text-secondary"><i class="bi bi-shield-lock me-1"></i>A imagem é apagada assim que você aprova ou recusa (LGPD).</span>
      </div>
      <div v-if="!documentos.length" class="card vazio"><i class="bi bi-person-vcard"></i><p class="mb-0">Nenhum documento {{ filtroDoc === 'pendente' ? 'esperando conferência' : 'nesta lista' }}.</p></div>
      <div v-for="d in documentos" :key="d.id" class="card p-3 mb-3">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <AvatarUsuario :usuario="d.usuario" :tamanho="2.6" />
          <div class="flex-grow-1 min-w-0">
            <div class="fw-semibold">{{ d.usuario.nome }} <span class="text-secondary fw-normal small">· matrícula {{ d.usuario.matricula }}</span></div>
            <div class="small text-secondary">
              <i :class="['bi me-1', d.tipo === 'cnh' ? 'bi-car-front' : 'bi-person-vcard']"></i>{{ d.tipo === 'cnh' ? 'CNH' : 'Identidade' }}
              <span v-if="d.validade"> · validade {{ dataCurtaNumerica(d.validade) }}</span>
              · enviado {{ dataHora(d.enviado_em) }}
            </div>
          </div>
          <span :class="['badge rounded-pill', COR_DOC[d.status]]">{{ TEXTO_DOC[d.status] }}</span>
        </div>

        <template v-if="d.status === 'pendente'">
          <div class="mt-3">
            <img v-if="imagens[d.id]" :src="imagens[d.id]" class="doc-imagem" :alt="`Documento de ${d.usuario.nome}`" />
            <button v-else type="button" class="btn btn-sm btn-outline-primary" :disabled="abrindoImagem === d.id" @click="verImagem(d)">
              <span v-if="abrindoImagem === d.id" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="bi bi-eye me-1"></i>Ver documento
            </button>
          </div>
          <div class="row g-2 mt-1 align-items-start">
            <div class="col-md">
              <input v-model.trim="motivos[d.id]" class="form-control form-control-sm" placeholder="Motivo, se for recusar (o aluno vê este texto)" aria-label="Motivo da recusa" />
            </div>
            <div class="col-md-auto d-flex gap-2">
              <button class="btn btn-sm btn-success" :disabled="analisando === d.id" @click="analisarDoc(d, true)"><i class="bi bi-check-lg me-1"></i>Aprovar</button>
              <button class="btn btn-sm btn-outline-danger" :disabled="analisando === d.id || !motivos[d.id]" @click="analisarDoc(d, false)"><i class="bi bi-x-lg me-1"></i>Recusar</button>
            </div>
          </div>
        </template>
        <div v-else-if="d.status === 'recusado'" class="small text-danger mt-2"><i class="bi bi-info-circle me-1"></i>{{ d.motivo_recusa }}</div>
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
            <i :class="['bi me-1', ICONE_ALERTA[a.tipo] ?? 'bi-exclamation-triangle-fill text-warning']"></i>
            <strong>{{ NOME_ALERTA[a.tipo] ?? a.tipo }}</strong>
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
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AdminAoVivo from '../components/admin/AdminAoVivo.vue'
import AdminAvaliacoes from '../components/admin/AdminAvaliacoes.vue'
import AdminExportar from '../components/admin/AdminExportar.vue'
import AdminHistorico from '../components/admin/AdminHistorico.vue'
import GraficoCaronas from '../components/admin/GraficoCaronas.vue'
import AlertaMensagem from '../components/AlertaMensagem.vue'
import AvatarUsuario from '../components/AvatarUsuario.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import api, { mensagemDeErro } from '../services/api'
import { carregarResumo, ehAba, painel, SECOES, type IdAba } from '../stores/admin'
import { auth, type TipoAviso } from '../stores/auth'
import type { Alerta, Configuracao, Denuncia, DocumentoAdmin, EstruturaBanco, StatusDocumento, UsuarioAdmin } from '../types/api'
import { dataCurtaNumerica, dataHora, nota, porcentagem, textoMotivo } from '../utils/formato'

/** Cartao de indicador da visao geral. */
interface Destaque {
  rotulo: string
  valor: string | number
  detalhe: string
  icone: string
  cor: 'azul' | 'verde' | 'amarelo' | 'roxo'
}

interface Pendencia {
  texto: string
  n: number
  aba: IdAba
  icone: string
  cor: 'vermelho' | 'amarelo' | 'verde'
}

const route = useRoute()
const router = useRouter()
// A secao aberta vem do endereco (/admin/avaliacoes): o menu lateral e o botao voltar funcionam
const aba = computed<IdAba>(() => (ehAba(route.params.aba) ? route.params.aba : 'resumo'))
const secao = computed(() => SECOES.find((s) => s.id === aba.value) ?? SECOES[0]!)
const carregando = ref(true)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

// Resumo compartilhado com o menu lateral (que o atualiza a cada 10 s)
const r = computed(() => painel.resumo)
const usuarios = ref<UsuarioAdmin[]>([])
const busca = ref('')
const soPendentes = ref(false)
const denuncias = ref<Denuncia[]>([])
const resolucoes = reactive<Record<number, string>>({})
const suspensoes = reactive<Record<number, boolean>>({})
const alertas = ref<Alerta[]>([])
const configuracoes = ref<Configuracao[]>([])
const banco = ref<EstruturaBanco | null>(null)

// Documentos: a imagem chega pela API com o token (nao ha link publico) e vira um endereco blob: local
type FiltroDoc = 'pendente' | 'aprovado' | 'recusado' | 'todos'
const FILTROS_DOC: { id: FiltroDoc; texto: string }[] = [
  { id: 'pendente', texto: 'Para conferir' },
  { id: 'aprovado', texto: 'Aprovados' },
  { id: 'recusado', texto: 'Recusados' },
  { id: 'todos', texto: 'Todos' }
]
const TEXTO_DOC: Record<StatusDocumento, string> = { nao_enviado: 'Não enviado', pendente: 'Para conferir', aprovado: 'Aprovado', recusado: 'Recusado' }
const COR_DOC: Record<StatusDocumento, string> = {
  nao_enviado: 'text-bg-light border', pendente: 'text-bg-warning', aprovado: 'text-bg-success', recusado: 'text-bg-danger'
}
const documentos = ref<DocumentoAdmin[]>([])
const filtroDoc = ref<FiltroDoc>('pendente')
const imagens = reactive<Record<number, string>>({})
const motivos = reactive<Record<number, string>>({})
const abrindoImagem = ref<number | null>(null)
const analisando = ref<number | null>(null)
const diagrama = ref<HTMLElement | null>(null)
const diagramaCompleto = ref(false)
const desenhando = ref(false)
const ampliado = ref(false)

const decimal = (n: number | null | undefined) => Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })

function avisar(texto: string, tipo: TipoAviso = 'success'): void {
  aviso.texto = texto
  aviso.tipo = tipo
}

const minutos = (n: number | null) => (n === null ? '—' : `${decimal(n)} min`)

// Os 4 numeros do topo
const destaques = computed<Destaque[]>(() => {
  if (!r.value) return []
  const { usuarios: u, viagens: v, confianca: c } = r.value
  return [
    { rotulo: 'Alunos', valor: u.total, detalhe: `${u.ativos_30_dias} ${u.ativos_30_dias === 1 ? 'ativo' : 'ativos'} em 30 dias`, icone: 'bi-people-fill', cor: 'azul' },
    { rotulo: 'Viagens concluídas', valor: v.concluidas, detalhe: `${v.passageiros_transportados} passageiros levados`, icone: 'bi-flag-fill', cor: 'roxo' },
    { rotulo: 'Nota média', valor: nota(c.nota_media), detalhe: `${c.avaliacoes} avaliações`, icone: 'bi-star-fill', cor: 'amarelo' },
    { rotulo: 'CO₂ evitado', valor: `${decimal(v.co2_evitado_kg)} kg`, detalhe: `${decimal(v.km_compartilhados)} km compartilhados`, icone: 'bi-tree-fill', cor: 'verde' }
  ]
})

// Metricas das viagens, todas num bloco so
const metricasViagem = computed(() => {
  if (!r.value) return []
  const { viagens: v, medias: m } = r.value
  return [
    { rotulo: 'ocupação dos carros', valor: porcentagem(v.taxa_ocupacao), icone: 'bi-person-plus-fill' },
    { rotulo: 'tempo médio de viagem', valor: minutos(m.tempo_medio_viagem_min), icone: 'bi-stopwatch-fill' },
    { rotulo: 'atraso médio na saída', valor: minutos(m.atraso_medio_saida_min), icone: 'bi-hourglass-split' },
    { rotulo: 'velocidade média', valor: m.velocidade_media_kmh === null ? '—' : `${decimal(m.velocidade_media_kmh)} km/h`, icone: 'bi-speedometer2' },
    { rotulo: 'tempo médio a bordo', valor: minutos(m.tempo_medio_a_bordo_min), icone: 'bi-person-check-fill' },
    { rotulo: 'faltas nas vagas confirmadas', valor: porcentagem(v.taxa_faltas), icone: 'bi-person-x-fill' }
  ]
})

// So o que precisa de acao agora (zeros nao aparecem)
const pendencias = computed<Pendencia[]>(() => {
  if (!r.value) return []
  const { usuarios: u, viagens: v, confianca: c } = r.value
  const outrosAlertas = Math.max(0, c.alertas_aguardando - c.avaliacoes_baixas_abertas)
  const lista: Pendencia[] = [
    { texto: 'Avaliações abaixo do limite', n: c.avaliacoes_baixas_abertas, aba: 'avaliacoes', icone: 'bi-star-half', cor: 'vermelho' },
    { texto: 'Alertas de segurança sem resolução', n: outrosAlertas, aba: 'alertas', icone: 'bi-shield-exclamation', cor: 'vermelho' },
    { texto: 'Denúncias aguardando análise', n: c.denuncias_abertas, aba: 'denuncias', icone: 'bi-flag-fill', cor: 'vermelho' },
    { texto: 'Documentos para conferir', n: u.documentos_pendentes, aba: 'documentos', icone: 'bi-person-vcard', cor: 'amarelo' },
    { texto: 'Pedidos de selo de verificado', n: u.verificacoes_pendentes, aba: 'usuarios', icone: 'bi-patch-check', cor: 'amarelo' },
    { texto: 'Viagens acontecendo agora', n: v.em_andamento_agora, aba: 'aovivo', icone: 'bi-geo-alt-fill', cor: 'verde' }
  ]
  return lista.filter((p) => p.n > 0)
})
const maxDemanda = computed(() => Math.max(1, ...(r.value?.demanda_sem_oferta || []).map((d) => d.buscas)))
const maxOferta = computed(() => Math.max(1, ...(r.value?.bairros_com_mais_oferta || []).map((d) => d.caronas)))
const totalLinhas = computed(() => (banco.value?.tabelas || []).reduce((s, t) => s + t.linhas, 0))

async function carregarUsuarios(): Promise<void> {
  const { data } = await api.get<{ usuarios: UsuarioAdmin[] }>('/admin/usuarios', {
    params: { busca: busca.value, pendentes: soPendentes.value ? 1 : 0 }
  })
  usuarios.value = data.usuarios
}

// Cada aba sabe carregar os proprios dados. `Record<IdAba, ...>` garante que nenhuma aba fique sem carregador.
const CARREGADORES: Record<IdAba, () => Promise<unknown>> = {
  resumo: carregarResumo,
  // as abas em tempo real carregam (e atualizam) os proprios dados
  aovivo: async () => undefined,
  avaliacoes: async () => undefined,
  historico: async () => undefined,
  exportar: async () => undefined,
  usuarios: carregarUsuarios,
  documentos: async () =>
    (documentos.value = (await api.get<{ documentos: DocumentoAdmin[] }>('/admin/documentos', { params: { status: filtroDoc.value } })).data.documentos),
  denuncias: async () => (denuncias.value = (await api.get<{ denuncias: Denuncia[] }>('/admin/denuncias')).data.denuncias),
  alertas: async () => (alertas.value = (await api.get<{ alertas: Alerta[] }>('/admin/alertas')).data.alertas),
  regras: async () =>
    (configuracoes.value = (await api.get<{ configuracoes: Configuracao[] }>('/admin/configuracoes')).data.configuracoes),
  banco: async () => {
    banco.value = (await api.get<EstruturaBanco>('/admin/banco')).data
  }
}

/** Abre uma secao do painel (muda o endereco; o watch abaixo carrega os dados). */
function trocarAba(id: IdAba): void {
  void router.push(id === 'resumo' ? '/admin' : `/admin/${id}`)
}

async function abrirSecao(id: IdAba): Promise<void> {
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

// ---------------- documentos ----------------
async function trocarFiltroDoc(filtro: FiltroDoc): Promise<void> {
  filtroDoc.value = filtro
  try {
    await CARREGADORES.documentos()
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}

async function verImagem(d: DocumentoAdmin): Promise<void> {
  abrindoImagem.value = d.id
  try {
    const { data } = await api.get<Blob>(`/admin/documentos/${d.id}/imagem`, { responseType: 'blob' })
    imagens[d.id] = URL.createObjectURL(data)
  } catch (e) {
    avisar(mensagemDeErro(e, 'Não deu para abrir a imagem.'), 'danger')
  } finally {
    abrindoImagem.value = null
  }
}

function esquecerImagem(id: number): void {
  if (imagens[id]) URL.revokeObjectURL(imagens[id])
  delete imagens[id]
}

async function analisarDoc(d: DocumentoAdmin, aprovado: boolean): Promise<void> {
  analisando.value = d.id
  try {
    await api.post(`/admin/documentos/${d.id}/analisar`, { aprovado, motivo: motivos[d.id] || '' })
    esquecerImagem(d.id)
    const nome = d.tipo === 'cnh' ? 'CNH' : 'identidade'
    avisar(aprovado ? `A ${nome} de ${d.usuario.nome} foi aprovada.` : `A ${nome} de ${d.usuario.nome} foi recusada.`, aprovado ? 'success' : 'warning')
    await Promise.all([CARREGADORES.documentos(), carregarResumo()])
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    analisando.value = null
  }
}

onBeforeUnmount(() => Object.keys(imagens).forEach((id) => esquecerImagem(Number(id))))

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

// Alertas com nome legivel na aba Alertas
const NOME_ALERTA: Record<string, string> = {
  botao_panico: 'Botão de emergência',
  parada_longa: 'Parada longa',
  sinal_perdido: 'Sinal perdido',
  desvio_rota: 'Desvio de rota',
  pin_sem_gps: 'PIN sem GPS',
  avaliacao_baixa: 'Avaliação baixa',
  exclusao_automatica: 'Exclusão automática'
}
const ICONE_ALERTA: Record<string, string> = {
  botao_panico: 'bi-exclamation-octagon-fill text-danger',
  avaliacao_baixa: 'bi-star-half text-danger',
  exclusao_automatica: 'bi-person-x-fill text-danger'
}

// Resumo atualizado a cada 10 s: se chegar avaliacao baixa nova, avisa em qualquer aba do painel
const novaNotaBaixa = ref('')
watch(
  () => r.value?.confianca.avaliacoes_baixas_abertas,
  (agora, antes) => {
    if (antes !== undefined && agora !== undefined && agora > antes) {
      const novas = agora - antes
      novaNotaBaixa.value = `${novas} ${novas === 1 ? 'avaliação abaixo do limite chegou' : 'avaliações abaixo do limite chegaram'} agora.`
    }
  }
)
watch(aba, (id) => void abrirSecao(id), { immediate: true })
</script>

<style scoped>
/* ----- Visao geral: menos caixas brancas soltas, blocos agrupados ----- */
.destaque {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  background: #fff;
  box-shadow: 0 0.15rem 0.6rem rgba(11, 42, 91, 0.08);
}

.destaque .rotulo {
  font-size: 0.8rem;
  color: var(--bs-secondary-color);
}

.destaque .numero {
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1.1;
  color: var(--uvv-azul);
}

.destaque .detalhe {
  font-size: 0.78rem;
  color: var(--bs-secondary-color);
}

/* Celular: icone em cima e numero logo abaixo (lado a lado ficava apertado) */
@media (max-width: 575.98px) {
  .destaque {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.85rem;
  }

  .destaque .numero {
    font-size: 1.5rem;
  }

  .destaque .icone-destaque {
    width: 2.25rem;
    height: 2.25rem;
    font-size: 1.05rem;
  }
}

.icone-destaque,
.icone-pendencia {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.8rem;
}

.icone-destaque {
  width: 3rem;
  height: 3rem;
  font-size: 1.35rem;
}

.icone-destaque.azul { background: #e3ecfb; color: var(--uvv-azul-2); }
.icone-destaque.roxo { background: #ece6fb; color: #5b3cc4; }
.icone-destaque.amarelo { background: #fff3cd; color: #9a6b00; }
.icone-destaque.verde { background: #dcf3e6; color: #157347; }

.bloco {
  padding: 1.1rem 1.25rem;
  border-radius: 1rem;
  background: #eef3fa;
}

.bloco-titulo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--uvv-azul);
  margin-bottom: 0.9rem;
}

.metricas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10.5rem, 1fr));
  gap: 0.6rem;
}

.metrica {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.75);
}

.metrica > .bi {
  font-size: 1.15rem;
  color: var(--uvv-azul-2);
}

.metrica .valor-m {
  font-weight: 800;
  font-size: 1.1rem;
  color: var(--uvv-azul);
  line-height: 1.1;
}

.metrica .rotulo-m {
  font-size: 0.74rem;
  color: var(--bs-secondary-color);
}

.pendencia {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.75rem;
  margin-bottom: 0.45rem;
  border: 0;
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.75);
  font-size: 0.9rem;
}

.pendencia:hover,
.pendencia:focus-visible {
  background: #fff;
  box-shadow: 0 0.15rem 0.5rem rgba(11, 42, 91, 0.1);
}

.icone-pendencia {
  width: 2rem;
  height: 2rem;
}

.icone-pendencia.vermelho { background: #fde2e4; color: #b02a37; }
.icone-pendencia.amarelo { background: #fff3cd; color: #9a6b00; }
.icone-pendencia.verde { background: #dcf3e6; color: #157347; }

.tudo-em-dia {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.9rem;
  border-radius: 0.75rem;
  background: #dcf3e6;
  color: #0f5132;
  font-weight: 600;
}

.subtitulo {
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.barra-linha {
  display: grid;
  grid-template-columns: minmax(6rem, 9.5rem) 1fr 1.6rem;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
}

.barra-linha .nome {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.barra-linha strong {
  text-align: right;
}

.barra {
  height: 0.5rem;
  border-radius: 999px;
  background: rgba(11, 42, 91, 0.1);
  overflow: hidden;
}

.barra .preenchido {
  height: 100%;
  border-radius: 999px;
  background: var(--uvv-azul-2);
}

.barra .preenchido.perigo {
  background: #dc3545;
}

/* Cabecalho da secao: titulo a esquerda, numeros do momento a direita */
.secao-topo {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: 0.75rem 1rem;
}

.secao-topo h1 {
  color: var(--uvv-azul);
}

.min-w-0 {
  min-width: 0;
}

.chip-topo {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid #dfe5ef;
  background: #fff;
  color: var(--uvv-azul);
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
}

.chip-topo:hover,
.chip-topo:focus-visible {
  border-color: var(--uvv-azul-2);
  background: #eef3fa;
}

.chip-topo.perigo {
  background: #dc3545;
  border-color: #dc3545;
  color: #fff;
}

.chip-topo .ponto {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: #b8c2d3;
}

.chip-topo .ponto.ativo {
  background: #1db96a;
  box-shadow: 0 0 0 3px rgba(29, 185, 106, 0.25);
}

/* Documento enviado para conferencia (ocupa a largura do cartao, sem passar da tela) */
.doc-imagem {
  display: block;
  max-width: 100%;
  max-height: 420px;
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
}
</style>
