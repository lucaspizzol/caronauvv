<template>
  <div class="tela-login d-flex align-items-center py-5">
    <div class="container" style="max-width: 420px">
      <div class="text-center mb-4">
        <div class="marca display-6"><i class="bi bi-car-front-fill me-2"></i>Carona<span>UVV</span></div>
        <p class="text-white-50 mb-0">Caronas entre alunos da UVV, com vaga garantida.</p>
      </div>

      <!-- ETAPA 1: e-mail (ou matricula) e senha -->
      <div v-if="!desafio" class="card p-4">
        <h1 class="h4 fw-bold mb-3">Entrar</h1>

        <AlertaMensagem v-if="route.query.expirou" texto="Sua sessão expirou. Entre de novo." tipo="info" @fechar="router.replace({ query: {} })" />
        <AlertaMensagem v-if="route.query.senha" texto="Senha alterada. Entre com a senha nova." tipo="success" @fechar="router.replace({ query: {} })" />
        <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />

        <form novalidate @submit.prevent="enviar">
          <div class="mb-3">
            <label class="form-label" for="login">E-mail ou matrícula</label>
            <input id="login" v-model.trim="form.login" type="text" autocomplete="username" :class="['form-control', { 'is-invalid': erros.login }]" placeholder="seu.email@uvv.br" />
            <div class="invalid-feedback">{{ erros.login }}</div>
          </div>
          <div class="mb-3">
            <div class="d-flex justify-content-between align-items-baseline">
              <label class="form-label" for="senha">Senha</label>
              <RouterLink :to="{ name: 'recuperar-senha', query: form.login ? { login: form.login } : {} }" class="small">Esqueci minha senha</RouterLink>
            </div>
            <input id="senha" v-model="form.senha" type="password" autocomplete="current-password" :class="['form-control', { 'is-invalid': erros.senha }]" />
            <div class="invalid-feedback">{{ erros.senha }}</div>
          </div>
          <button class="btn btn-primary w-100 py-2" type="submit" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-2"></span>Entrar
          </button>
        </form>

        <p class="text-center small mt-3 mb-0">
          Ainda não tem conta? <RouterLink to="/cadastro" class="fw-semibold">Cadastre-se</RouterLink>
        </p>
      </div>

      <!-- ETAPA 2: codigo do aplicativo autenticador (so para quem ligou a verificacao em duas etapas) -->
      <div v-else class="card p-4">
        <div class="text-center">
          <i class="bi bi-shield-lock display-5 text-primary"></i>
          <h1 class="h4 fw-bold mt-2 mb-1">Verificação em duas etapas</h1>
          <p class="text-secondary small mb-3">
            {{ usarReserva
              ? 'Digite um dos códigos de reserva que você guardou. Cada um vale uma vez.'
              : 'Abra o aplicativo autenticador no celular e digite o código de 6 números do CaronaUVV.' }}
          </p>
        </div>

        <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />

        <form novalidate @submit.prevent="confirmar">
          <input
            v-if="!usarReserva" id="codigo" ref="campoCodigo" v-model.trim="codigo" inputmode="numeric" maxlength="7" autocomplete="one-time-code"
            aria-label="Código do aplicativo autenticador" placeholder="000000"
            :class="['form-control form-control-lg text-center font-monospace', { 'is-invalid': erros.codigo }]" style="letter-spacing: 0.5rem"
          />
          <input
            v-else id="codigo" ref="campoCodigo" :value="codigo" maxlength="9" autocomplete="off" autocapitalize="characters"
            aria-label="Código de reserva" placeholder="ABCD-EFGH"
            :class="['form-control form-control-lg text-center font-monospace', { 'is-invalid': erros.codigo }]" style="letter-spacing: 0.2rem"
            @input="digitarReserva"
          />
          <div class="invalid-feedback d-block mb-2">{{ erros.codigo }}</div>
          <button class="btn btn-primary w-100 py-2" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-2"></span>Confirmar e entrar
          </button>
        </form>

        <div class="d-flex justify-content-between small mt-3">
          <button type="button" class="btn btn-link btn-sm p-0" @click="voltar"><i class="bi bi-arrow-left me-1"></i>Voltar</button>
          <button type="button" class="btn btn-link btn-sm p-0" @click="trocarModo">
            {{ usarReserva ? 'Usar o aplicativo' : 'Estou sem o celular: usar código de reserva' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import api, { camposDoErro, mensagemDeErro, statusDoErro } from '../services/api'
import { avisoGlobal, entrar } from '../stores/auth'
import type { ErrosCampos, RespostaSessao } from '../types/api'
import { codigoReservaFormatado } from '../utils/formato'
import { regras, validar } from '../utils/validacao'

/** O /login devolve a sessao ou, se a conta usa autenticador, um desafio para a segunda etapa. */
type RespostaLogin = (RespostaSessao & { precisa_2fa?: false }) | { precisa_2fa: true; desafio: string }

/** A segunda etapa pode trazer um aviso (ex.: "Voce entrou com um codigo de reserva. Restam 3."). */
type SessaoComAviso = RespostaSessao & { aviso?: string }

const route = useRoute()
const router = useRouter()

const form = reactive({ login: '', senha: '' })
const erros = ref<ErrosCampos>({})
const erroApi = ref('')
const enviando = ref(false)

// Segunda etapa: a API devolve um "desafio" no lugar do token quando a conta usa autenticador
const desafio = ref('')
const codigo = ref('')
const usarReserva = ref(false)
const campoCodigo = ref<HTMLInputElement | null>(null)

function concluir(dados: SessaoComAviso): void {
  entrar(dados.token, dados.usuario)
  if (dados.aviso) Object.assign(avisoGlobal, { texto: dados.aviso, tipo: 'warning' })
  const volta = route.query.volta
  void router.push(typeof volta === 'string' && volta ? volta : '/caronas')
}

async function enviar(): Promise<void> {
  erroApi.value = ''
  erros.value = validar(form, { login: [regras.obrigatorio], senha: [regras.obrigatorio] })
  if (Object.keys(erros.value).length) return

  enviando.value = true
  try {
    const { data } = await api.post<RespostaLogin>('/auth/login', form)
    if (data.precisa_2fa) {
      desafio.value = data.desafio
      codigo.value = ''
      usarReserva.value = false
      await nextTick()
      campoCodigo.value?.focus()
    } else {
      concluir(data)
    }
  } catch (e) {
    erroApi.value = mensagemDeErro(e)
  } finally {
    enviando.value = false
  }
}

async function confirmar(): Promise<void> {
  erroApi.value = ''
  const valido = usarReserva.value ? /^[A-Z0-9]{4}-?[A-Z0-9]{4}$/i.test(codigo.value) : /^\d{3}\s?\d{3}$/.test(codigo.value)
  erros.value = valido ? {} : { codigo: usarReserva.value ? 'O código de reserva tem 8 caracteres.' : 'O código tem 6 números.' }
  if (!valido) return

  enviando.value = true
  try {
    const { data } = await api.post<SessaoComAviso>('/auth/login/2fa', { desafio: desafio.value, codigo: codigo.value })
    concluir(data)
  } catch (e) {
    const erroCodigo = camposDoErro(e).codigo
    // desafio vencido (5 min) ou invalido: volta para a senha
    if (statusDoErro(e) === 401 && !erroCodigo) {
      voltar()
      erroApi.value = mensagemDeErro(e)
    } else if (erroCodigo) {
      erros.value = { codigo: erroCodigo }
      codigo.value = ''
      campoCodigo.value?.focus()
    } else {
      erroApi.value = mensagemDeErro(e)
    }
  } finally {
    enviando.value = false
  }
}

// Codigo de reserva: maiusculas e hifen no meio enquanto a pessoa digita ("abcdefgh" -> "ABCD-EFGH")
function digitarReserva(evento: Event): void {
  const campo = evento.target as HTMLInputElement
  codigo.value = campo.value = codigoReservaFormatado(campo.value)
}

async function trocarModo(): Promise<void> {
  usarReserva.value = !usarReserva.value
  codigo.value = ''
  erros.value = {}
  erroApi.value = ''
  await nextTick()
  campoCodigo.value?.focus()
}

function voltar(): void {
  desafio.value = ''
  codigo.value = ''
  form.senha = ''
  erros.value = {}
  erroApi.value = ''
}
</script>
