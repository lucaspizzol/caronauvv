<template>
  <div class="container py-4" style="max-width: 860px">
    <a href="#" class="small text-decoration-none" @click.prevent="router.back()"><i class="bi bi-arrow-left me-1"></i>Voltar</a>

    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>
    <AlertaMensagem v-else-if="erro" :texto="erro" @fechar="erro = ''" />

    <template v-else-if="u">
      <!-- CABECALHO -->
      <div class="card p-4 mt-2">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <AvatarUsuario :usuario="u" :tamanho="5" />
          <div class="flex-grow-1">
            <h1 class="h4 fw-bold mb-0">
              {{ u.nome }}
              <i v-if="u.verificado" class="bi bi-patch-check-fill text-primary" title="Perfil verificado pela UVV"></i>
            </h1>
            <div class="text-secondary small">
              {{ u.curso || 'Aluno(a) da UVV' }} · {{ u.bairro }} · no CaronaUVV desde {{ membroDesde(u.membro_desde) }}
            </div>
            <div class="mt-1"><span class="badge rounded-pill text-bg-light border fs-6">{{ rep.nivel }}</span></div>
          </div>
          <div class="text-center">
            <div class="display-6 fw-bold text-warning"><i class="bi bi-star-fill"></i> {{ nota(rep.nota_media) }}</div>
            <div class="small text-secondary">{{ rep.total_avaliacoes }} {{ rep.total_avaliacoes === 1 ? 'avaliação' : 'avaliações' }}</div>
          </div>
        </div>

        <p v-if="u.bio" class="mt-3 mb-0 fst-italic">"{{ u.bio }}"</p>

        <!-- Selos de confianca -->
        <div v-if="rep.selos.length" class="d-flex flex-wrap gap-2 mt-3">
          <span v-for="s in rep.selos" :key="s.codigo" class="selo"><i :class="['bi', ICONE_SELO[s.codigo] || 'bi-award']"></i>{{ s.texto }}</span>
        </div>
      </div>

      <div class="row g-3 mt-1">
        <!-- NUMEROS -->
        <div class="col-md-5">
          <div class="card p-3 h-100">
            <h2 class="h6 fw-bold">Histórico</h2>
            <ul class="list-unstyled small mb-0 d-flex flex-column gap-2">
              <li><i class="bi bi-car-front me-2 text-primary"></i>{{ rep.viagens_motorista }} viagens como motorista</li>
              <li><i class="bi bi-person me-2 text-primary"></i>{{ rep.viagens_passageiro }} viagens como passageiro(a)</li>
              <li>
                <i :class="['bi me-2', rep.faltas ? 'bi-exclamation-triangle text-warning' : 'bi-check2-circle text-success']"></i>
                {{ rep.faltas ? `${rep.faltas} ${rep.faltas === 1 ? 'falta' : 'faltas'} em vagas confirmadas` : 'Nenhuma falta' }}
              </li>
              <li>
                <i class="bi bi-x-octagon me-2 text-secondary"></i>
                {{ rep.taxa_cancelamento > 0.3 ? 'Cancela com frequência' : 'Raramente cancela' }} ({{ porcentagem(rep.taxa_cancelamento) }} das caronas)
              </li>
            </ul>
          </div>
        </div>

        <!-- PREFERENCIAS -->
        <div class="col-md-7">
          <div class="card p-3 h-100">
            <h2 class="h6 fw-bold">Preferências na viagem</h2>
            <div class="row g-2 small">
              <div v-for="p in listaPreferencias(u.preferencias)" :key="p.texto" class="col-6">
                <i :class="['bi me-2 text-primary', p.icone]"></i>{{ p.texto }}
              </div>
            </div>
            <div v-if="u.veiculos.length" class="small mt-3">
              <i class="bi bi-car-front-fill me-2 text-primary"></i>
              <span v-for="(v, i) in u.veiculos" :key="v.id">{{ i ? ', ' : '' }}{{ v.modelo }} {{ v.cor }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- O QUE MAIS ELOGIAM -->
      <div v-if="rep.tags.length" class="card p-3 mt-3">
        <h2 class="h6 fw-bold">O que mais elogiam</h2>
        <div class="d-flex flex-wrap gap-2">
          <span v-for="t in rep.tags" :key="t.tag" class="badge rounded-pill text-bg-light border fs-6 fw-normal">{{ t.tag }} <strong>×{{ t.total }}</strong></span>
        </div>
      </div>

      <!-- AVALIACOES -->
      <div class="card p-3 mt-3">
        <h2 class="h6 fw-bold">Avaliações recebidas</h2>
        <p v-if="!u.avaliacoes.length" class="small text-secondary mb-0">Ainda sem avaliações publicadas.</p>
        <div v-for="a in u.avaliacoes" :key="a.id" class="border-top py-2">
          <div class="d-flex justify-content-between align-items-center small">
            <span class="d-inline-flex flex-wrap align-items-center gap-1">
              <AvatarUsuario :usuario="a.avaliador" :tamanho="1.6" class="me-1" />
              <i v-for="n in 5" :key="n" :class="['bi', n <= a.nota ? 'bi-star-fill text-warning' : 'bi-star text-secondary']"></i>
              <span class="ms-2 fw-semibold">{{ a.avaliador.nome }}</span>
              <span class="text-secondary"> · como {{ a.papel_avaliado }}</span>
            </span>
            <span class="text-secondary">{{ dataCurta(a.criada_em) }}</span>
          </div>
          <div v-if="a.comentario" class="small mt-1">"{{ a.comentario }}"</div>
          <div v-if="a.tags.length" class="d-flex flex-wrap gap-1 mt-1">
            <span v-for="t in a.tags" :key="t" class="badge text-bg-light border fw-normal">{{ t }}</span>
          </div>
        </div>
      </div>

      <!-- DENUNCIA -->
      <div v-if="u.id !== auth.usuario?.id" id="denunciar" class="card p-3 mt-3 border-danger-subtle">
        <button v-if="!denunciando" class="btn btn-sm btn-outline-danger align-self-start" @click="abrirDenuncia">
          <i class="bi bi-flag me-1"></i>Denunciar {{ u.nome.split(' ')[0] }}
        </button>
        <form v-else novalidate @submit.prevent="denunciar">
          <h2 class="h6 fw-bold text-danger"><i class="bi bi-flag-fill me-1"></i>Denunciar {{ u.nome }}</h2>
          <p class="small text-secondary">Só dá para denunciar quem dividiu uma carona com você. A administração analisa cada caso.</p>
          <AlertaMensagem :texto="msgDenuncia.texto" :tipo="msgDenuncia.tipo" @fechar="msgDenuncia.texto = ''" />
          <div class="row g-2">
            <div class="col-md-5">
              <label class="form-label" for="motivo">Motivo</label>
              <select id="motivo" v-model="denuncia.motivo" :class="['form-select', { 'is-invalid': errosDenuncia.motivo }]">
                <option value="">Escolha...</option>
                <option v-for="(texto, chave) in MOTIVOS_DENUNCIA" :key="chave" :value="chave">{{ texto }}</option>
              </select>
              <div class="invalid-feedback">{{ errosDenuncia.motivo }}</div>
            </div>
            <div class="col-md-7">
              <label class="form-label" for="descricao">O que aconteceu?</label>
              <textarea id="descricao" v-model.trim="denuncia.descricao" rows="2" maxlength="1000" class="form-control"></textarea>
            </div>
          </div>
          <div class="d-flex justify-content-end gap-2 mt-2">
            <button type="button" class="btn btn-sm btn-light" @click="denunciando = false">Cancelar</button>
            <button class="btn btn-sm btn-danger" :disabled="enviando">Enviar denúncia</button>
          </div>
        </form>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import AvatarUsuario from '../components/AvatarUsuario.vue'
import api, { camposDoErro, mensagemDeErro } from '../services/api'
import { auth, type TipoAviso } from '../stores/auth'
import type { ErrosCampos, PerfilPublico, Reputacao, Selo } from '../types/api'
import {
  dataCurta, listaPreferencias, membroDesde, MOTIVOS_DENUNCIA, nota, porcentagem, type MotivoDenuncia
} from '../utils/formato'
import { regras, validar } from '../utils/validacao'

const props = defineProps<{ id: string }>()
const router = useRouter()
const route = useRoute()

const ICONE_SELO: Record<Selo['codigo'], string> = {
  email_uvv: 'bi-envelope-check-fill',
  perfil_verificado: 'bi-patch-check-fill',
  pontual: 'bi-alarm-fill',
  bem_avaliado: 'bi-star-fill',
  sem_faltas: 'bi-calendar-check-fill'
}

const u = ref<PerfilPublico | null>(null)
const carregando = ref(true)
const erro = ref('')
// Reputacao "zerada" enquanto o perfil carrega: o template pode ler os campos sem conferir se existem
const REPUTACAO_VAZIA: Reputacao = {
  nota_media: null, total_avaliacoes: 0, tags: [], viagens_motorista: 0, viagens_passageiro: 0,
  faltas: 0, taxa_cancelamento: 0, nivel: 'Calouro', selos: []
}
const rep = computed<Reputacao>(() => u.value?.reputacao ?? REPUTACAO_VAZIA)

const denunciando = ref(false)
const enviando = ref(false)
const denuncia = reactive<{ motivo: '' | MotivoDenuncia; descricao: string }>({ motivo: '', descricao: '' })
const errosDenuncia = ref<ErrosCampos>({})
const msgDenuncia = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

async function carregar(): Promise<void> {
  carregando.value = true
  erro.value = ''
  try {
    const { data } = await api.get<{ usuario: PerfilPublico }>(`/usuarios/${props.id}`)
    u.value = data.usuario
  } catch (e) {
    erro.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
  if (route.hash === '#denunciar') abrirDenuncia()
}

function abrirDenuncia(): void {
  denunciando.value = true
}

async function denunciar(): Promise<void> {
  if (!u.value) return
  errosDenuncia.value = validar(denuncia, { motivo: [regras.obrigatorio] })
  if (Object.keys(errosDenuncia.value).length) return
  enviando.value = true
  try {
    await api.post('/denuncias', { denunciado_id: u.value.id, ...denuncia })
    msgDenuncia.texto = 'Denúncia enviada. A administração vai analisar.'
    msgDenuncia.tipo = 'success'
    Object.assign(denuncia, { motivo: '', descricao: '' })
  } catch (e) {
    msgDenuncia.texto = mensagemDeErro(e)
    msgDenuncia.tipo = 'danger'
    errosDenuncia.value = camposDoErro(e)
  } finally {
    enviando.value = false
  }
}

onMounted(carregar)
watch(() => props.id, carregar)
</script>
