<template>
  <div class="container py-5" style="max-width: 480px">
    <div class="card p-4 text-center">
      <i class="bi bi-envelope-check display-5 text-primary"></i>
      <h1 class="h4 fw-bold mt-2">Confirme seu e-mail UVV</h1>

      <template v-if="auth.usuario?.email_verificado">
        <p class="text-success fw-semibold mb-3"><i class="bi bi-check-circle-fill me-1"></i>E-mail confirmado!</p>
        <RouterLink to="/caronas" class="btn btn-primary">Buscar caronas</RouterLink>
      </template>

      <template v-else>
        <p class="text-secondary">
          Enviamos um código de 6 números para <strong>{{ auth.usuario?.email }}</strong>.
          Só alunos com e-mail da UVV confirmado podem oferecer e pedir caronas.
        </p>

        <!-- Sem servidor de e-mail (desenvolvimento), a API devolve o codigo para a demonstracao -->
        <div v-if="demo.codigoDev" class="alert alert-info small py-2">
          <i class="bi bi-tools me-1"></i>Modo de demonstração: seu código é
          <strong class="font-monospace fs-6">{{ demo.codigoDev }}</strong>
        </div>

        <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

        <form novalidate @submit.prevent="confirmar">
          <input
            v-model.trim="codigo"
            inputmode="numeric"
            maxlength="6"
            autocomplete="one-time-code"
            aria-label="Código de verificação"
            :class="['form-control form-control-lg text-center font-monospace mb-1', { 'is-invalid': erro }]"
            placeholder="000000"
            style="letter-spacing: 0.5rem"
          />
          <div class="invalid-feedback d-block mb-2">{{ erro }}</div>
          <button class="btn btn-primary w-100" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-1"></span>Confirmar
          </button>
        </form>
        <button class="btn btn-link btn-sm mt-2" :disabled="reenviando" @click="reenviar">Não recebi: enviar outro código</button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import api, { camposDoErro, mensagemDeErro } from '../services/api'
import { atualizarUsuario, auth, demo, type TipoAviso } from '../stores/auth'
import type { UsuarioLogado } from '../types/api'
import { regras } from '../utils/validacao'

const router = useRouter()
const codigo = ref('')
const erro = ref('')
const enviando = ref(false)
const reenviando = ref(false)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

async function confirmar(): Promise<void> {
  erro.value = regras.codigo(codigo.value) || ''
  if (erro.value) return
  enviando.value = true
  try {
    const { data } = await api.post<{ usuario: UsuarioLogado }>('/auth/verificar-email', { codigo: codigo.value })
    atualizarUsuario(data.usuario)
    demo.codigoDev = null
    void router.push({ name: 'buscar' })
  } catch (e) {
    erro.value = camposDoErro(e).codigo || mensagemDeErro(e)
  } finally {
    enviando.value = false
  }
}

async function reenviar(): Promise<void> {
  reenviando.value = true
  try {
    const { data } = await api.post<{ message: string; codigo_dev?: string }>('/auth/reenviar-codigo')
    demo.codigoDev = data.codigo_dev || null
    aviso.texto = data.message
    aviso.tipo = 'success'
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  } finally {
    reenviando.value = false
  }
}
</script>
