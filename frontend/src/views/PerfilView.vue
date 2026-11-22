<template>
  <div class="container py-4" style="max-width: 860px">
    <h1 class="titulo-pagina h3 mb-3">Meu perfil</h1>

    <div class="row g-4">
      <!-- DADOS PESSOAIS -->
      <div class="col-lg-7">
        <form class="card p-4 h-100" novalidate @submit.prevent="salvarPerfil">
          <div class="d-flex align-items-center gap-3 mb-3">
            <span class="avatar" style="width: 3.2rem; height: 3.2rem; font-size: 1.1rem">{{ iniciais(perfil.nome) }}</span>
            <div>
              <div class="fw-bold">{{ auth.usuario?.nome }}</div>
              <div class="small text-secondary">Matrícula {{ auth.usuario?.matricula }} · {{ auth.usuario?.email }}</div>
            </div>
          </div>

          <AlertaMensagem :texto="msgPerfil.texto" :tipo="msgPerfil.tipo" @fechar="msgPerfil.texto = ''" />

          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="p-nome">Nome</label>
              <input id="p-nome" v-model.trim="perfil.nome" :class="['form-control', { 'is-invalid': errosPerfil.nome }]" />
              <div class="invalid-feedback">{{ errosPerfil.nome }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="p-tel">Telefone</label>
              <input id="p-tel" v-model.trim="perfil.telefone" type="tel" :class="['form-control', { 'is-invalid': errosPerfil.telefone }]" />
              <div class="invalid-feedback">{{ errosPerfil.telefone }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="p-bairro">Bairro</label>
              <input id="p-bairro" v-model.trim="perfil.bairro" list="lista-bairros" :class="['form-control', { 'is-invalid': errosPerfil.bairro }]" />
              <datalist id="lista-bairros"><option v-for="b in BAIRROS" :key="b" :value="b" /></datalist>
              <div class="invalid-feedback">{{ errosPerfil.bairro }}</div>
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="p-curso">Curso</label>
              <input id="p-curso" v-model.trim="perfil.curso" class="form-control" />
            </div>
            <div class="col-sm-6">
              <label class="form-label" for="p-pix">Chave Pix <span class="text-secondary fw-normal">(para o rateio)</span></label>
              <input id="p-pix" v-model.trim="perfil.chave_pix" class="form-control" />
            </div>
          </div>
          <div class="text-end mt-3">
            <button class="btn btn-primary" :disabled="salvandoPerfil">
              <span v-if="salvandoPerfil" class="spinner-border spinner-border-sm me-1"></span>Salvar dados
            </button>
          </div>
        </form>
      </div>

      <!-- SENHA -->
      <div class="col-lg-5">
        <form class="card p-4 h-100" novalidate @submit.prevent="trocarSenha">
          <h2 class="h5 fw-bold mb-3"><i class="bi bi-key me-1"></i>Trocar senha</h2>
          <AlertaMensagem :texto="msgSenha.texto" :tipo="msgSenha.tipo" @fechar="msgSenha.texto = ''" />
          <div class="mb-3">
            <label class="form-label" for="s-atual">Senha atual</label>
            <input id="s-atual" v-model="senha.senha_atual" type="password" autocomplete="current-password" :class="['form-control', { 'is-invalid': errosSenha.senha_atual }]" />
            <div class="invalid-feedback">{{ errosSenha.senha_atual }}</div>
          </div>
          <div class="mb-3">
            <label class="form-label" for="s-nova">Nova senha</label>
            <input id="s-nova" v-model="senha.nova_senha" type="password" autocomplete="new-password" :class="['form-control', { 'is-invalid': errosSenha.nova_senha }]" />
            <div class="invalid-feedback">{{ errosSenha.nova_senha }}</div>
          </div>
          <div class="text-end mt-auto">
            <button class="btn btn-outline-primary" :disabled="salvandoSenha">Trocar senha</button>
          </div>
        </form>
      </div>

      <!-- VEICULOS -->
      <div id="veiculos" class="col-12">
        <div class="card p-4">
          <h2 class="h5 fw-bold mb-1"><i class="bi bi-car-front me-1"></i>Meus carros</h2>
          <p class="small text-secondary">A placa só aparece para o passageiro depois que a vaga é confirmada.</p>
          <AlertaMensagem :texto="msgVeiculo.texto" :tipo="msgVeiculo.tipo" @fechar="msgVeiculo.texto = ''" />

          <div v-for="v in veiculos" :key="v.id" class="d-flex align-items-center gap-3 border rounded-3 p-2 mb-2">
            <i class="bi bi-car-front-fill fs-4 text-primary"></i>
            <div class="flex-grow-1">
              <span class="fw-semibold">{{ v.modelo }}</span> <span class="text-secondary">{{ v.cor }}</span>
              <span class="badge text-bg-light border ms-2">{{ v.placa }}</span>
            </div>
            <BotaoConfirmar texto="Remover" pergunta="Remover este carro?" icone="bi-trash" :acao="() => removerVeiculo(v)" />
          </div>
          <p v-if="!veiculos.length" class="small text-secondary">Nenhum carro cadastrado.</p>

          <form class="row g-2 align-items-start mt-1" novalidate @submit.prevent="adicionarVeiculo">
            <div class="col-sm-4">
              <input v-model.trim="veiculo.modelo" placeholder="Modelo (ex.: HB20)" aria-label="Modelo" :class="['form-control', { 'is-invalid': errosVeiculo.modelo }]" />
              <div class="invalid-feedback">{{ errosVeiculo.modelo }}</div>
            </div>
            <div class="col-sm-3">
              <input v-model.trim="veiculo.cor" placeholder="Cor" aria-label="Cor" :class="['form-control', { 'is-invalid': errosVeiculo.cor }]" />
              <div class="invalid-feedback">{{ errosVeiculo.cor }}</div>
            </div>
            <div class="col-sm-3">
              <input v-model.trim="veiculo.placa" placeholder="Placa" aria-label="Placa" maxlength="8" style="text-transform: uppercase" :class="['form-control', { 'is-invalid': errosVeiculo.placa }]" />
              <div class="invalid-feedback">{{ errosVeiculo.placa }}</div>
            </div>
            <div class="col-sm-2 d-grid">
              <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> Adicionar</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import api from '../services/api'
import { atualizarUsuario, auth } from '../stores/auth'
import { BAIRROS } from '../utils/bairros'
import { iniciais } from '../utils/formato'
import { regras, validar } from '../utils/validacao'

const perfil = reactive({ nome: '', telefone: '', bairro: '', curso: '', chave_pix: '' })
const errosPerfil = ref({})
const msgPerfil = reactive({ texto: '', tipo: 'success' })
const salvandoPerfil = ref(false)

const senha = reactive({ senha_atual: '', nova_senha: '' })
const errosSenha = ref({})
const msgSenha = reactive({ texto: '', tipo: 'success' })
const salvandoSenha = ref(false)

const veiculos = ref([])
const veiculo = reactive({ modelo: '', cor: '', placa: '' })
const errosVeiculo = ref({})
const msgVeiculo = reactive({ texto: '', tipo: 'success' })

function preencher(u) {
  Object.assign(perfil, { nome: u.nome, telefone: u.telefone, bairro: u.bairro, curso: u.curso || '', chave_pix: u.chave_pix || '' })
}

onMounted(async () => {
  try {
    const [me, vs] = await Promise.all([api.get('/auth/me'), api.get('/veiculos')])
    atualizarUsuario(me.data.usuario)
    preencher(me.data.usuario)
    veiculos.value = vs.data.veiculos
  } catch (e) {
    msgPerfil.texto = e.mensagem
    msgPerfil.tipo = 'danger'
  }
})

async function salvarPerfil() {
  msgPerfil.texto = ''
  errosPerfil.value = validar(perfil, {
    nome: [regras.obrigatorio],
    telefone: [regras.obrigatorio, regras.telefone],
    bairro: [regras.obrigatorio]
  })
  if (Object.keys(errosPerfil.value).length) return
  salvandoPerfil.value = true
  try {
    const { data } = await api.put('/auth/me', perfil)
    atualizarUsuario(data.usuario)
    msgPerfil.texto = 'Dados atualizados.'
    msgPerfil.tipo = 'success'
  } catch (e) {
    msgPerfil.texto = e.mensagem
    msgPerfil.tipo = 'danger'
  } finally {
    salvandoPerfil.value = false
  }
}

async function trocarSenha() {
  msgSenha.texto = ''
  errosSenha.value = validar(senha, { senha_atual: [regras.obrigatorio], nova_senha: [regras.obrigatorio, regras.senha] })
  if (Object.keys(errosSenha.value).length) return
  salvandoSenha.value = true
  try {
    await api.put('/auth/me', senha)
    Object.assign(senha, { senha_atual: '', nova_senha: '' })
    msgSenha.texto = 'Senha alterada.'
    msgSenha.tipo = 'success'
  } catch (e) {
    msgSenha.texto = e.mensagem
    msgSenha.tipo = 'danger'
  } finally {
    salvandoSenha.value = false
  }
}

async function adicionarVeiculo() {
  msgVeiculo.texto = ''
  errosVeiculo.value = validar(veiculo, { modelo: [regras.obrigatorio], cor: [regras.obrigatorio], placa: [regras.obrigatorio, regras.placa] })
  if (Object.keys(errosVeiculo.value).length) return
  try {
    const { data } = await api.post('/veiculos', veiculo)
    veiculos.value.push(data.veiculo)
    Object.assign(veiculo, { modelo: '', cor: '', placa: '' })
    msgVeiculo.texto = 'Carro cadastrado.'
    msgVeiculo.tipo = 'success'
  } catch (e) {
    msgVeiculo.texto = e.mensagem
    msgVeiculo.tipo = 'danger'
  }
}

async function removerVeiculo(v) {
  try {
    await api.delete(`/veiculos/${v.id}`)
    veiculos.value = veiculos.value.filter((x) => x.id !== v.id)
    msgVeiculo.texto = 'Carro removido.'
    msgVeiculo.tipo = 'success'
  } catch (e) {
    msgVeiculo.texto = e.mensagem
    msgVeiculo.tipo = 'danger'
  }
}
</script>
