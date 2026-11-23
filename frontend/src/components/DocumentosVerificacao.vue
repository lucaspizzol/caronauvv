<template>
  <!-- Verificacao de documentos: identidade (todos) e CNH (quem oferece carona) -->
  <div class="card p-4">
    <h2 class="h5 fw-bold mb-1"><i class="bi bi-person-vcard me-1"></i>Documentos verificados</h2>
    <p class="small text-secondary">
      Envie uma foto nítida do documento. A administração confere e o selo aparece no seu perfil e nas suas caronas.
      Depois da conferência a imagem é apagada: guardamos só o resultado.
    </p>
    <AlertaMensagem :texto="msg.texto" :tipo="msg.tipo" @fechar="msg.texto = ''" />

    <div v-if="carregando" class="text-center py-3"><span class="spinner-border spinner-border-sm text-primary"></span></div>
    <div v-else class="row g-3">
      <div v-for="d in documentos" :key="d.tipo" class="col-md-6">
        <div class="documento h-100 p-3">
          <div class="d-flex align-items-start gap-2">
            <i :class="['bi fs-3', INFO[d.tipo].icone, d.status === 'aprovado' ? 'text-success' : 'text-primary']"></i>
            <div class="flex-grow-1 min-w-0">
              <div class="fw-semibold">{{ INFO[d.tipo].titulo }}</div>
              <div class="small text-secondary">{{ INFO[d.tipo].para }}</div>
            </div>
            <span :class="['badge rounded-pill', SITUACAO[situacao(d)].classe]">
              <i :class="['bi me-1', SITUACAO[situacao(d)].icone]"></i>{{ SITUACAO[situacao(d)].texto }}
            </span>
          </div>

          <div v-if="d.status === 'aprovado'" class="small text-success mt-2">
            Conferido pela administração<span v-if="d.validade"> · válida até {{ dataCurtaNumerica(d.validade) }}</span>.
          </div>
          <div v-else-if="d.status === 'pendente'" class="small text-secondary mt-2">
            Enviado em {{ dataHora(d.enviado_em) }}. A administração vai conferir em breve.
          </div>
          <div v-else-if="d.status === 'recusado'" class="small text-danger mt-2">
            <i class="bi bi-info-circle me-1"></i>{{ d.motivo_recusa }}
          </div>

          <!-- Enviar (ou reenviar): o arquivo ja vai reduzido; na CNH, a validade -->
          <div v-if="podeEnviar(d)" class="mt-3">
            <div v-if="d.tipo === 'cnh'" class="mb-2">
              <label class="form-label small mb-1" :for="`validade-${d.tipo}`">Validade da CNH</label>
              <input
                :id="`validade-${d.tipo}`" v-model="validades[d.tipo]" type="date" :min="hojeLocal()"
                :class="['form-control form-control-sm', { 'is-invalid': erros[d.tipo]?.validade }]" style="max-width: 12rem"
              />
              <div class="invalid-feedback">{{ erros[d.tipo]?.validade }}</div>
            </div>
            <label :class="['btn btn-sm btn-primary mb-0', { disabled: enviando === d.tipo }]" :for="`arquivo-${d.tipo}`">
              <span v-if="enviando === d.tipo" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="bi bi-camera me-1"></i>{{ d.status === 'nao_enviado' ? 'Enviar foto' : 'Enviar outra foto' }}
            </label>
            <input
              :id="`arquivo-${d.tipo}`" type="file" class="visually-hidden" :accept="TIPOS_ACEITOS.join(',')"
              :disabled="enviando === d.tipo" @change="(e) => escolher(d.tipo, e)"
            />
            <div class="form-text">JPG, PNG ou WebP. Mostre o documento inteiro, sem reflexo.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import api, { camposDoErro, mensagemDeErro } from '../services/api'
import { atualizarUsuario, type TipoAviso } from '../stores/auth'
import type { Documento, ErrosCampos, TipoDocumento, UsuarioLogado } from '../types/api'
import { dataCurtaNumerica, dataHora, hojeLocal } from '../utils/formato'
import { prepararDocumento, TIPOS_ACEITOS, validarArquivoDeFoto } from '../utils/imagem'
import AlertaMensagem from './AlertaMensagem.vue'

const INFO: Record<TipoDocumento, { titulo: string; para: string; icone: string }> = {
  identidade: { titulo: 'Identidade (RG ou CNH)', para: 'Para motorista e passageiro', icone: 'bi-person-vcard' },
  cnh: { titulo: 'CNH', para: 'Para quem oferece carona', icone: 'bi-car-front' }
}

type Situacao = 'nao_enviado' | 'pendente' | 'aprovado' | 'recusado' | 'vencido'
const SITUACAO: Record<Situacao, { texto: string; classe: string; icone: string }> = {
  nao_enviado: { texto: 'Não enviado', classe: 'text-bg-light border', icone: 'bi-dash-circle' },
  pendente: { texto: 'Em análise', classe: 'text-bg-warning', icone: 'bi-hourglass-split' },
  aprovado: { texto: 'Verificado', classe: 'text-bg-success', icone: 'bi-patch-check-fill' },
  recusado: { texto: 'Recusado', classe: 'text-bg-danger', icone: 'bi-x-circle' },
  vencido: { texto: 'Vencida', classe: 'text-bg-danger', icone: 'bi-calendar-x' }
}

const documentos = ref<Documento[]>([])
const carregando = ref(true)
const enviando = ref<TipoDocumento | null>(null)
const validades = reactive<Record<TipoDocumento, string>>({ identidade: '', cnh: '' })
const erros = reactive<Partial<Record<TipoDocumento, ErrosCampos>>>({})
const msg = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

const situacao = (d: Documento): Situacao => (d.status === 'aprovado' && d.vencido ? 'vencido' : d.status)
const podeEnviar = (d: Documento) => d.status === 'nao_enviado' || d.status === 'recusado' || Boolean(d.vencido)

onMounted(async () => {
  try {
    const { data } = await api.get<{ documentos: Documento[] }>('/auth/me/documentos')
    documentos.value = data.documentos
  } catch (e) {
    msg.texto = mensagemDeErro(e)
    msg.tipo = 'danger'
  } finally {
    carregando.value = false
  }
})

async function escolher(tipo: TipoDocumento, evento: Event): Promise<void> {
  const campo = evento.target as HTMLInputElement
  const arquivo = campo.files?.[0]
  campo.value = '' // deixa escolher o mesmo arquivo de novo
  if (!arquivo) return
  msg.texto = ''
  erros[tipo] = {}
  if (tipo === 'cnh' && !validades.cnh) {
    erros[tipo] = { validade: 'Informe a validade antes de enviar a foto.' }
    return
  }
  const problema = validarArquivoDeFoto(arquivo)
  if (problema) {
    msg.texto = problema
    msg.tipo = 'danger'
    return
  }
  enviando.value = tipo
  try {
    const formulario = new FormData()
    formulario.append('documento', await prepararDocumento(arquivo), 'documento.jpg')
    if (tipo === 'cnh') formulario.append('validade', validades.cnh)
    const { data } = await api.put<{ documentos: Documento[]; usuario: UsuarioLogado }>(`/auth/me/documentos/${tipo}`, formulario)
    documentos.value = data.documentos
    atualizarUsuario(data.usuario)
    msg.texto = 'Documento enviado! Você recebe uma notificação quando a administração conferir.'
    msg.tipo = 'success'
  } catch (e) {
    erros[tipo] = camposDoErro(e)
    msg.texto = mensagemDeErro(e, 'Não deu para enviar o documento.')
    msg.tipo = 'danger'
  } finally {
    enviando.value = null
  }
}
</script>

<style scoped>
.documento {
  border: 1px solid var(--bs-border-color);
  border-radius: 0.75rem;
  background: #fbfcfe;
}
</style>
