<template>
  <div class="tela-login d-flex align-items-center py-5">
    <div class="container" style="max-width: 560px">
      <div class="text-center mb-4">
        <div class="marca display-6"><i class="bi bi-car-front-fill me-2"></i>Carona<span>UVV</span></div>
        <p class="text-white-50 mb-0">Só alunos da UVV: use seu e-mail institucional.</p>
      </div>

      <div class="card p-4">
        <h1 class="h4 fw-bold mb-3">Criar conta</h1>
        <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />

        <form novalidate @submit.prevent="enviar">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="nome">Nome completo</label>
              <input id="nome" v-model.trim="form.nome" autocomplete="name" :class="['form-control', { 'is-invalid': erros.nome }]" />
              <div class="invalid-feedback">{{ erros.nome }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="matricula">Matrícula</label>
              <input id="matricula" v-model.trim="form.matricula" inputmode="numeric" :class="['form-control', { 'is-invalid': erros.matricula }]" placeholder="202416377" />
              <div class="invalid-feedback">{{ erros.matricula }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="curso">Curso <span class="text-secondary fw-normal">(opcional)</span></label>
              <input id="curso" v-model.trim="form.curso" class="form-control" placeholder="Ciência da Computação" />
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="email">E-mail UVV</label>
              <input id="email" v-model.trim="form.email" type="email" autocomplete="email" :class="['form-control', { 'is-invalid': erros.email }]" placeholder="nome@uvv.br" />
              <div class="invalid-feedback">{{ erros.email }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="telefone">Telefone (WhatsApp)</label>
              <input id="telefone" v-model.trim="form.telefone" type="tel" autocomplete="tel" :class="['form-control', { 'is-invalid': erros.telefone }]" placeholder="(27) 99999-0000" />
              <div class="invalid-feedback">{{ erros.telefone }}</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="bairro">Bairro onde mora</label>
              <CampoBairro id="bairro" v-model="form.bairro" :invalido="Boolean(erros.bairro)" />
              <div v-if="erros.bairro" class="invalid-feedback d-block">{{ erros.bairro }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="senha">Senha</label>
              <input id="senha" v-model="form.senha" type="password" autocomplete="new-password" :class="['form-control', { 'is-invalid': erros.senha }]" />
              <div class="invalid-feedback">{{ erros.senha }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="confirmar">Confirmar senha</label>
              <input id="confirmar" v-model="form.confirmar" type="password" autocomplete="new-password" :class="['form-control', { 'is-invalid': erros.confirmar }]" />
              <div class="invalid-feedback">{{ erros.confirmar }}</div>
            </div>
          </div>

          <p class="small text-secondary mt-3 mb-3">
            <i class="bi bi-shield-lock me-1"></i>Seu telefone só aparece para o motorista ou passageiro depois que a vaga é confirmada.
            Vamos enviar um código para confirmar seu e-mail UVV.
          </p>

          <button class="btn btn-primary w-100 py-2" type="submit" :disabled="enviando">
            <span v-if="enviando" class="spinner-border spinner-border-sm me-2"></span>Criar conta
          </button>
        </form>

        <p class="text-center small mt-3 mb-0">Já tem conta? <RouterLink to="/login" class="fw-semibold">Entrar</RouterLink></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import CampoBairro from '../components/CampoBairro.vue'
import api, { mensagemDeErro } from '../services/api'
import { demo, entrar } from '../stores/auth'
import type { ErrosCampos, RespostaSessao } from '../types/api'
import { errosDoServidor, regras, validar } from '../utils/validacao'

const router = useRouter()

const form = reactive({ nome: '', matricula: '', curso: '', email: '', telefone: '', bairro: '', senha: '', confirmar: '' })
const erros = ref<ErrosCampos>({})
const erroApi = ref('')
const enviando = ref(false)

async function enviar(): Promise<void> {
  erroApi.value = ''
  erros.value = validar(form, {
    nome: [regras.obrigatorio],
    matricula: [regras.obrigatorio, regras.matricula],
    email: [regras.obrigatorio, regras.email, regras.emailUvv],
    telefone: [regras.obrigatorio, regras.telefone],
    bairro: [regras.obrigatorio, regras.bairro],
    senha: [regras.obrigatorio, regras.senha],
    confirmar: [(v, d) => (v === d?.senha ? null : 'As senhas não conferem.')]
  })
  if (Object.keys(erros.value).length) return

  enviando.value = true
  try {
    // "confirmar" so existe na tela: nao vai para a API
    const { confirmar: _confirmar, ...dados } = form
    const { data } = await api.post<RespostaSessao>('/auth/cadastro', dados)
    entrar(data.token, data.usuario)
    demo.codigoDev = data.codigo_dev || null
    void router.push('/verificar-email')
  } catch (e) {
    erroApi.value = mensagemDeErro(e)
    // erros que so o servidor conhece (ex.: dominio do e-mail) aparecem no campo certo
    erros.value = { ...erros.value, ...errosDoServidor(e, Object.keys(form)) }
  } finally {
    enviando.value = false
  }
}
</script>
