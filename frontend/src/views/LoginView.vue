<template>
  <div class="tela-login d-flex align-items-center py-5">
    <div class="container" style="max-width: 420px">
      <div class="text-center mb-4">
        <div class="marca display-6"><i class="bi bi-car-front-fill me-2"></i>Carona<span>UVV</span></div>
        <p class="text-white-50 mb-0">Caronas entre alunos da UVV, com vaga garantida.</p>
      </div>

      <div class="card p-4">
        <h1 class="h4 fw-bold mb-3">Entrar</h1>

        <AlertaMensagem v-if="route.query.expirou" texto="Sua sessão expirou. Entre de novo." tipo="info" @fechar="router.replace({ query: {} })" />
        <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />

        <form novalidate @submit.prevent="enviar">
          <div class="mb-3">
            <label class="form-label" for="login">E-mail ou matrícula</label>
            <input id="login" v-model.trim="form.login" type="text" autocomplete="username" :class="['form-control', { 'is-invalid': erros.login }]" placeholder="seu.email@uvv.br" />
            <div class="invalid-feedback">{{ erros.login }}</div>
          </div>
          <div class="mb-3">
            <label class="form-label" for="senha">Senha</label>
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
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import api from '../services/api'
import { entrar } from '../stores/auth'
import { regras, validar } from '../utils/validacao'

const route = useRoute()
const router = useRouter()

const form = reactive({ login: '', senha: '' })
const erros = ref({})
const erroApi = ref('')
const enviando = ref(false)

async function enviar() {
  erroApi.value = ''
  erros.value = validar(form, { login: [regras.obrigatorio], senha: [regras.obrigatorio] })
  if (Object.keys(erros.value).length) return

  enviando.value = true
  try {
    const { data } = await api.post('/auth/login', form)
    entrar(data.token, data.usuario)
    router.push(route.query.volta || '/caronas')
  } catch (e) {
    erroApi.value = e.mensagem
  } finally {
    enviando.value = false
  }
}
</script>
