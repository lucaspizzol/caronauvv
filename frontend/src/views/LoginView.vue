<template>
  <div class="tela-login d-flex align-items-center py-4 py-lg-5">
    <div class="container" style="max-width: 1040px">
      <div class="row g-4 align-items-center">
      <!-- VITRINE: o que o app faz (no celular, so o essencial) -->
      <div class="col-lg-6 text-white vitrine">
        <div class="marca display-6 mb-2 text-center text-lg-start"><i class="bi bi-car-front-fill me-2"></i>Carona<span>UVV</span></div>
        <p class="lead mb-3 text-center text-lg-start chamada">Vá para a UVV com quem faz o mesmo caminho e divida só o combustível.</p>
        <ul class="list-unstyled d-none d-lg-flex flex-column gap-3 mb-4">
          <li v-for="v in VANTAGENS" :key="v.titulo" class="d-flex gap-3 align-items-start">
            <span class="icone-vitrine" aria-hidden="true"><i :class="['bi', v.icone]"></i></span>
            <span><strong class="d-block">{{ v.titulo }}</strong><span class="texto-suave small">{{ v.texto }}</span></span>
          </li>
        </ul>
        <div class="d-flex d-lg-none flex-wrap justify-content-center gap-2 mb-1">
          <span v-for="v in VANTAGENS" :key="v.titulo" class="selo-vitrine"><i :class="['bi me-1', v.icone]" aria-hidden="true"></i>{{ v.curto }}</span>
        </div>
      </div>

      <div class="col-lg-6">
      <div class="mx-auto" style="max-width: 420px">

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
          <span class="d-block mt-2"><RouterLink to="/perguntas-frequentes"><i class="bi bi-question-circle me-1"></i>Perguntas frequentes</RouterLink></span>
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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Vitrine da tela de entrada: o que o professor (e o aluno) ve primeiro
const VANTAGENS = [
  { icone: 'bi-patch-check-fill', titulo: 'Só alunos da UVV', curto: 'Só alunos UVV', texto: 'Cadastro com e-mail @uvv.br e documentos verificados.' },
  { icone: 'bi-shield-lock-fill', titulo: 'Viagem segura', curto: 'PIN e link da família', texto: 'PIN de embarque, link para a família acompanhar e botão de emergência.' },
  { icone: 'bi-fuel-pump-fill', titulo: 'Valor justo e aberto', curto: 'Divide o combustível', texto: 'A conta do combustível (com trânsito) aparece passo a passo, com teto por pessoa.' },
  { icone: 'bi-people-fill', titulo: 'Fila com prioridade', curto: 'Fila com prioridade', texto: 'Sem carona? Entre na fila e seja avisado primeiro quando aparecer uma.' }
]
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

<style scoped>
.chamada { color: rgba(255, 255, 255, 0.9); }
.texto-suave { color: rgba(255, 255, 255, 0.78); }
.icone-vitrine {
  flex: 0 0 2.6rem; height: 2.6rem; border-radius: 0.8rem; display: grid; place-items: center;
  background: rgba(255, 199, 44, 0.15); color: var(--uvv-amarelo); font-size: 1.2rem;
}
.selo-vitrine {
  font-size: 0.8rem; padding: 0.3rem 0.7rem; border-radius: 999px;
  background: rgba(255, 255, 255, 0.1); color: #fff; border: 1px solid rgba(255, 255, 255, 0.2);
}
</style>
