<template>
  <!-- "Esqueci minha senha": codigo de 6 numeros por e-mail e, em seguida, a senha nova -->
  <div class="tela-login d-flex align-items-center py-5">
    <div class="container" style="max-width: 440px">
      <div class="text-center mb-4">
        <div class="marca display-6"><i class="bi bi-car-front-fill me-2"></i>Carona<span>UVV</span></div>
      </div>

      <div class="card p-4">
        <h1 class="h4 fw-bold mb-1">Criar uma senha nova</h1>

        <!-- PASSO 1: qual conta -->
        <form v-if="passo === 1" novalidate @submit.prevent="pedirCodigo">
          <p class="text-secondary small">Informe o e-mail UVV ou a matrícula da conta. Enviamos um código de 6 números para o e-mail cadastrado.</p>
          <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />
          <div class="mb-3">
            <label class="form-label" for="r-login">E-mail ou matrícula</label>
            <input id="r-login" v-model.trim="form.login" type="text" autocomplete="username" :class="['form-control', { 'is-invalid': erros.login }]" placeholder="seu.email@uvv.br" />
            <div class="invalid-feedback">{{ erros.login }}</div>
          </div>
          <button class="btn btn-primary w-100 py-2" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-2"></span>Enviar código
          </button>
        </form>

        <!-- PASSO 2: codigo + senha nova -->
        <form v-else novalidate @submit.prevent="redefinir">
          <p class="text-secondary small">{{ mensagem }}</p>

          <!-- Sem servidor de e-mail (desenvolvimento), a API devolve o codigo para a demonstracao -->
          <div v-if="codigoDev" class="alert alert-info small py-2">
            <i class="bi bi-tools me-1"></i>Modo de demonstração: seu código é
            <strong class="font-monospace fs-6">{{ codigoDev }}</strong>
          </div>
          <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />

          <div class="mb-3">
            <label class="form-label" for="r-codigo">Código recebido por e-mail</label>
            <input
              id="r-codigo" v-model.trim="form.codigo" inputmode="numeric" maxlength="6" autocomplete="one-time-code" placeholder="000000"
              :class="['form-control text-center font-monospace', { 'is-invalid': erros.codigo }]" style="letter-spacing: 0.4rem"
            />
            <div class="invalid-feedback">{{ erros.codigo }}</div>
          </div>
          <div class="mb-3">
            <label class="form-label" for="r-senha">Senha nova</label>
            <input id="r-senha" v-model="form.nova_senha" type="password" autocomplete="new-password" :class="['form-control', { 'is-invalid': erros.nova_senha }]" />
            <div class="invalid-feedback">{{ erros.nova_senha }}</div>
          </div>
          <div class="mb-3">
            <label class="form-label" for="r-senha2">Repita a senha nova</label>
            <input id="r-senha2" v-model="form.confirmar" type="password" autocomplete="new-password" :class="['form-control', { 'is-invalid': erros.confirmar }]" />
            <div class="invalid-feedback">{{ erros.confirmar }}</div>
          </div>
          <button class="btn btn-primary w-100 py-2" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-2"></span>Salvar senha nova
          </button>
          <button type="button" class="btn btn-link btn-sm w-100 mt-2" :disabled="enviando" @click="passo = 1">Não recebi: pedir outro código</button>
        </form>

        <p class="text-center small mt-3 mb-0"><RouterLink to="/login"><i class="bi bi-arrow-left me-1"></i>Voltar para o login</RouterLink></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import api from '../services/api'
import { errosDoServidor, regras, validar } from '../utils/validacao'

const route = useRoute()
const router = useRouter()

const passo = ref(1)
const form = reactive({ login: String(route.query.login || ''), codigo: '', nova_senha: '', confirmar: '' })
const erros = ref({})
const erroApi = ref('')
const mensagem = ref('')
const codigoDev = ref('')
const enviando = ref(false)

async function pedirCodigo() {
  erroApi.value = ''
  erros.value = validar(form, { login: [regras.obrigatorio] })
  if (Object.keys(erros.value).length) return
  enviando.value = true
  try {
    const { data } = await api.post('/auth/esqueci-senha', { login: form.login })
    mensagem.value = data.message
    codigoDev.value = data.codigo_dev || ''
    Object.assign(form, { codigo: '', nova_senha: '', confirmar: '' })
    passo.value = 2
  } catch (e) {
    erroApi.value = e.mensagem
  } finally {
    enviando.value = false
  }
}

async function redefinir() {
  erroApi.value = ''
  erros.value = validar(form, {
    codigo: [regras.obrigatorio, regras.codigo],
    nova_senha: [regras.obrigatorio, regras.senha],
    confirmar: [regras.obrigatorio, (v, dados) => (v === dados.nova_senha ? null : 'As senhas não são iguais.')]
  })
  if (Object.keys(erros.value).length) return
  enviando.value = true
  try {
    await api.post('/auth/redefinir-senha', { login: form.login, codigo: form.codigo, nova_senha: form.nova_senha })
    router.push({ name: 'login', query: { senha: 'ok' } })
  } catch (e) {
    erros.value = errosDoServidor(e, ['codigo', 'nova_senha'])
    if (!Object.keys(erros.value).length) erroApi.value = e.mensagem
  } finally {
    enviando.value = false
  }
}
</script>
