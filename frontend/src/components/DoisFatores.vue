<template>
  <!-- Verificacao em duas etapas: senha + codigo do aplicativo autenticador (TOTP) -->
  <div id="duas-etapas" class="card p-4 flex-grow-1">
    <h2 class="h5 fw-bold mb-1"><i class="bi bi-shield-lock me-1"></i>Verificação em duas etapas</h2>
    <div class="mb-2">
      <span v-if="situacao?.ativo" class="badge text-bg-success"><i class="bi bi-check-lg me-1"></i>Ativa</span>
      <span v-else-if="situacao" class="badge text-bg-light border">Desligada</span>
    </div>

    <AlertaMensagem :texto="msg.texto" :tipo="msg.tipo" @fechar="msg.texto = ''" />
    <div v-if="!situacao && !msg.texto" class="text-center py-3"><span class="spinner-border spinner-border-sm text-primary"></span></div>

    <!-- CODIGOS DE RESERVA (aparecem uma unica vez, logo depois de ativar ou gerar) -->
    <template v-else-if="codigos.length">
      <p class="small mb-2">
        <strong>Guarde estes códigos de reserva.</strong> Cada um entra no lugar do aplicativo uma única vez,
        se você ficar sem o celular. Eles não aparecem de novo.
      </p>
      <div class="codigos-reserva mb-3">
        <code v-for="c in codigos" :key="c">{{ c }}</code>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <button type="button" class="btn btn-sm btn-outline-primary" @click="copiar(codigos.join('\n'), 'codigos')">
          <i class="bi bi-clipboard me-1"></i>{{ copiado === 'codigos' ? 'Copiado!' : 'Copiar' }}
        </button>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="baixar"><i class="bi bi-download me-1"></i>Baixar .txt</button>
        <button type="button" class="btn btn-sm btn-primary ms-auto" @click="codigos = []">Já guardei</button>
      </div>
    </template>

    <!-- DESLIGADA -->
    <template v-else-if="situacao && !situacao.ativo && !config">
      <p class="small text-secondary">
        Além da senha, o login pede um código de 6 números que muda a cada 30 segundos no seu celular.
        Mesmo que alguém descubra sua senha, não entra na sua conta.
      </p>
      <div class="mt-auto">
        <button type="button" class="btn btn-primary" :disabled="carregando" @click="iniciar">
          <span v-if="carregando" class="spinner-border spinner-border-sm me-1"></span><i v-else class="bi bi-phone me-1"></i>Ativar com aplicativo autenticador
        </button>
      </div>
    </template>

    <!-- CONFIGURANDO: QR Code + primeiro codigo -->
    <form v-else-if="config" novalidate @submit.prevent="ativar">
      <ol class="small ps-3 mb-2 passos-2fa">
        <li>Instale no celular um aplicativo autenticador: <strong>Google Authenticator</strong>, <strong>Microsoft Authenticator</strong> ou <strong>Authy</strong>.</li>
        <li>No aplicativo, toque em <strong>+</strong> e leia este QR Code:</li>
      </ol>
      <div class="text-center mb-2">
        <img v-if="config.qr" :src="config.qr" alt="QR Code para o aplicativo autenticador" width="180" height="180" class="border rounded bg-white p-1" />
        <div class="small text-secondary mt-2">Não consegue ler? Digite a chave no aplicativo:</div>
        <button type="button" class="btn btn-link btn-sm font-monospace text-break p-0" title="Copiar a chave" @click="copiar(config.segredo, 'chave')">
          {{ chaveAgrupada }} <i :class="['bi', copiado === 'chave' ? 'bi-check2' : 'bi-clipboard']"></i>
        </button>
      </div>
      <label class="form-label small mb-1" for="codigo-2fa"><strong>3.</strong> Digite o código de 6 números que o aplicativo mostra:</label>
      <input
        id="codigo-2fa" v-model.trim="codigo" inputmode="numeric" maxlength="7" autocomplete="one-time-code" placeholder="000000"
        :class="['form-control text-center font-monospace', { 'is-invalid': erros.codigo }]" style="letter-spacing: 0.4rem"
      />
      <div class="invalid-feedback">{{ erros.codigo }}</div>
      <label class="form-label small mb-1 mt-2" for="senha-ativar"><strong>4.</strong> Confirme sua senha do CaronaUVV:</label>
      <input id="senha-ativar" v-model="senha" type="password" autocomplete="current-password" :class="['form-control', { 'is-invalid': erros.senha }]" />
      <div class="invalid-feedback">{{ erros.senha }}</div>
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button type="button" class="btn btn-light" :disabled="carregando" @click="cancelar">Cancelar</button>
        <button class="btn btn-primary" :disabled="carregando">
          <span v-if="carregando" class="spinner-border spinner-border-sm me-1"></span>Ativar
        </button>
      </div>
    </form>

    <!-- ATIVA -->
    <template v-else-if="situacao?.ativo">
      <p class="small text-secondary mb-2">
        O login pede a senha e o código do aplicativo autenticador<span v-if="situacao.ativado_em"> desde {{ dataCurtaNumerica(situacao.ativado_em) }}</span>.
      </p>
      <p :class="['small mb-3', situacao.codigos_restantes <= 2 ? 'text-danger fw-semibold' : '']">
        <i class="bi bi-life-preserver me-1"></i>Códigos de reserva sem usar: <strong>{{ situacao.codigos_restantes }}</strong> de 8
        <span v-if="situacao.codigos_restantes <= 2"> — gere novos.</span>
      </p>

      <!-- acoes sensiveis pedem a senha e um codigo -->
      <form v-if="acao" class="border rounded-3 p-3" novalidate @submit.prevent="confirmarAcao">
        <div class="fw-semibold small mb-2">{{ acao === 'desativar' ? 'Desligar a verificação em duas etapas' : 'Gerar novos códigos de reserva' }}</div>
        <div class="mb-2">
          <label class="form-label small mb-1" for="senha-2fa">Sua senha</label>
          <input id="senha-2fa" v-model="senha" type="password" autocomplete="current-password" :class="['form-control form-control-sm', { 'is-invalid': erros.senha }]" />
          <div class="invalid-feedback">{{ erros.senha }}</div>
        </div>
        <div class="mb-2">
          <label class="form-label small mb-1" for="codigo-acao">Código do aplicativo (ou um código de reserva)</label>
          <input id="codigo-acao" v-model.trim="codigo" autocomplete="one-time-code" :class="['form-control form-control-sm font-monospace', { 'is-invalid': erros.codigo }]" placeholder="000000" />
          <div class="invalid-feedback">{{ erros.codigo }}</div>
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-sm btn-light" :disabled="carregando" @click="fecharAcao">Cancelar</button>
          <button :class="['btn btn-sm', acao === 'desativar' ? 'btn-danger' : 'btn-primary']" :disabled="carregando">
            <span v-if="carregando" class="spinner-border spinner-border-sm me-1"></span>{{ acao === 'desativar' ? 'Desligar' : 'Gerar códigos' }}
          </button>
        </div>
      </form>
      <div v-else class="d-flex flex-wrap gap-2 mt-auto">
        <button type="button" class="btn btn-sm btn-outline-primary" @click="abrirAcao('codigos')"><i class="bi bi-arrow-repeat me-1"></i>Novos códigos de reserva</button>
        <button type="button" class="btn btn-sm btn-outline-danger" @click="abrirAcao('desativar')"><i class="bi bi-shield-x me-1"></i>Desligar</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import api, { camposDoErro, mensagemDeErro } from '../services/api'
import { atualizarUsuario, auth, type TipoAviso } from '../stores/auth'
import type { DataIso, ErrosCampos, UsuarioLogado } from '../types/api'
import { dataCurtaNumerica } from '../utils/formato'
import AlertaMensagem from './AlertaMensagem.vue'

/** GET /api/auth/2fa */
interface SituacaoDoisFatores {
  ativo: boolean
  ativado_em: DataIso | null
  codigos_restantes: number
}

/** POST /api/auth/2fa/iniciar (+ o QR Code desenhado aqui) */
interface ConfigAutenticador {
  segredo: string
  uri: string
  qr: string
}

interface RespostaAtivacao {
  usuario: UsuarioLogado
  dois_fatores: SituacaoDoisFatores
  codigos_reserva: string[]
}

const situacao = ref<SituacaoDoisFatores | null>(null)
const config = ref<ConfigAutenticador | null>(null) // enquanto o aluno le o QR Code
const codigos = ref<string[]>([]) // codigos de reserva recem-gerados
const acao = ref<'' | 'desativar' | 'codigos'>('')
const codigo = ref('')
const senha = ref('')
const erros = ref<ErrosCampos>({})
const carregando = ref(false)
const copiado = ref('')
const msg = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

// JBSWY3DP... -> "JBSW Y3DP ..." (mais facil de digitar no aplicativo)
const chaveAgrupada = computed(() => (config.value?.segredo || '').replace(/(.{4})/g, '$1 ').trim())

function avisar(texto: string, tipo: TipoAviso = 'success'): void {
  msg.texto = texto
  msg.tipo = tipo
}

function falhou(e: unknown): void {
  erros.value = camposDoErro(e)
  if (!Object.keys(erros.value).length) avisar(mensagemDeErro(e), 'danger')
}

onMounted(async () => {
  try {
    const { data } = await api.get<{ dois_fatores: SituacaoDoisFatores }>('/auth/2fa')
    situacao.value = data.dois_fatores
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
})

async function iniciar(): Promise<void> {
  msg.texto = ''
  carregando.value = true
  try {
    const { data } = await api.post<Omit<ConfigAutenticador, 'qr'>>('/auth/2fa/iniciar')
    // QR Code desenhado no navegador: o segredo nao passa por nenhum site de fora
    const QRCode = (await import('qrcode')).default
    const qr = await QRCode.toDataURL(data.uri, { margin: 1, width: 360 })
    config.value = { ...data, qr }
    codigo.value = ''
    senha.value = ''
    erros.value = {}
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  } finally {
    carregando.value = false
  }
}

function cancelar(): void {
  config.value = null
  codigo.value = ''
  senha.value = ''
  erros.value = {}
}

async function ativar(): Promise<void> {
  erros.value = {}
  if (!/^\d{3}\s?\d{3}$/.test(codigo.value)) erros.value.codigo = 'O código tem 6 números.'
  if (!senha.value) erros.value.senha = 'Campo obrigatório.'
  if (Object.keys(erros.value).length) return
  carregando.value = true
  try {
    const { data } = await api.post<RespostaAtivacao>('/auth/2fa/ativar', { senha: senha.value, codigo: codigo.value })
    atualizarUsuario(data.usuario)
    situacao.value = data.dois_fatores
    codigos.value = data.codigos_reserva
    cancelar()
    avisar('Verificação em duas etapas ativada.')
  } catch (e) {
    falhou(e)
  } finally {
    carregando.value = false
  }
}

function abrirAcao(qual: 'desativar' | 'codigos'): void {
  acao.value = qual
  senha.value = ''
  codigo.value = ''
  erros.value = {}
  msg.texto = ''
}

function fecharAcao(): void {
  acao.value = ''
  senha.value = ''
  codigo.value = ''
  erros.value = {}
}

async function confirmarAcao(): Promise<void> {
  erros.value = {}
  if (!senha.value) erros.value.senha = 'Campo obrigatório.'
  if (!codigo.value) erros.value.codigo = 'Campo obrigatório.'
  if (Object.keys(erros.value).length) return
  carregando.value = true
  try {
    const corpo = { senha: senha.value, codigo: codigo.value }
    if (acao.value === 'desativar') {
      const { data } = await api.post<Omit<RespostaAtivacao, 'codigos_reserva'>>('/auth/2fa/desativar', corpo)
      atualizarUsuario(data.usuario)
      situacao.value = data.dois_fatores
      avisar('Verificação em duas etapas desligada.', 'info')
    } else {
      const { data } = await api.post<Omit<RespostaAtivacao, 'usuario'>>('/auth/2fa/codigos-reserva', corpo)
      situacao.value = data.dois_fatores
      codigos.value = data.codigos_reserva
    }
    fecharAcao()
  } catch (e) {
    falhou(e)
  } finally {
    carregando.value = false
  }
}

async function copiar(texto: string, qual: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(texto)
    copiado.value = qual
    setTimeout(() => (copiado.value = ''), 2000)
  } catch {
    avisar('Não deu para copiar automaticamente. Selecione o texto e copie.', 'danger')
  }
}

function baixar(): void {
  const texto = [
    'CaronaUVV - códigos de reserva da verificação em duas etapas',
    `Conta: ${auth.usuario?.email || ''}`,
    'Cada código vale uma única vez. Guarde em lugar seguro.',
    '',
    ...codigos.value
  ].join('\r\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([texto], { type: 'text/plain;charset=utf-8' }))
  link.download = 'caronauvv-codigos-de-reserva.txt'
  link.click()
  URL.revokeObjectURL(link.href)
}
</script>
