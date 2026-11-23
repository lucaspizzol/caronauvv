<template>
  <div class="container py-4" style="max-width: 860px">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-2 mb-3">
      <h1 class="titulo-pagina h3 mb-0">Meu perfil</h1>
      <RouterLink v-if="auth.usuario" :to="`/usuarios/${auth.usuario.id}`" class="btn btn-sm btn-outline-primary">
        <i class="bi bi-eye me-1"></i>Ver como os outros me veem
      </RouterLink>
    </div>

    <!-- CONFIANCA: e-mail confirmado e selo de perfil verificado -->
    <div class="card p-3 mb-4">
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <span :class="['selo', { 'bg-warning-subtle text-warning-emphasis': !auth.usuario?.email_verificado }]">
          <i :class="['bi', auth.usuario?.email_verificado ? 'bi-envelope-check-fill' : 'bi-envelope-exclamation']"></i>
          {{ auth.usuario?.email_verificado ? 'E-mail UVV confirmado' : 'E-mail UVV não confirmado' }}
        </span>
        <RouterLink v-if="!auth.usuario?.email_verificado" to="/verificar-email" class="small">Confirmar agora</RouterLink>

        <span v-if="auth.usuario?.verificado" class="selo"><i class="bi bi-patch-check-fill"></i>Perfil verificado pela UVV</span>
        <span v-else-if="auth.usuario?.verificacao_solicitada_em" class="small text-secondary">
          <i class="bi bi-hourglass-split me-1"></i>Verificação do perfil em análise pela administração
        </span>
        <button v-else class="btn btn-sm btn-outline-primary" :disabled="!auth.usuario?.email_verificado" @click="pedirVerificacao">
          <i class="bi bi-patch-check me-1"></i>Pedir selo de perfil verificado
        </button>
      </div>
      <AlertaMensagem class="mt-2 mb-0" :texto="msgSelo.texto" :tipo="msgSelo.tipo" @fechar="msgSelo.texto = ''" />
    </div>

    <div class="row g-4">
      <!-- DADOS PESSOAIS -->
      <div class="col-lg-7">
        <form class="card p-4 h-100" novalidate @submit.prevent="salvarPerfil">
          <FotoPerfilEditor />

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
              <input id="p-pix" v-model.trim="perfil.chave_pix" :class="['form-control', { 'is-invalid': errosPerfil.chave_pix }]" />
              <div class="invalid-feedback">{{ errosPerfil.chave_pix }}</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="p-bio">Sobre mim <span class="text-secondary fw-normal">(aparece no seu perfil)</span></label>
              <textarea id="p-bio" v-model.trim="perfil.bio" rows="2" maxlength="300" :class="['form-control', { 'is-invalid': errosPerfil.bio }]" placeholder="Ex.: estudo à noite e saio pontualmente"></textarea>
              <div class="invalid-feedback">{{ errosPerfil.bio }}</div>
            </div>

            <!-- Preferencias de viagem (como o "Bla, BlaBla, BlaBlaBla" do BlaBlaCar) -->
            <div class="col-12">
              <div class="form-label">Preferências na viagem</div>
              <div class="btn-group btn-group-sm w-100 mb-2" role="group" aria-label="Conversa">
                <template v-for="(info, nivel) in PREF_CONVERSA" :key="nivel">
                  <input :id="`conv-${nivel}`" v-model="perfil.pref_conversa" class="btn-check" type="radio" :value="nivel" />
                  <label class="btn btn-outline-primary" :for="`conv-${nivel}`"><i :class="['bi me-1', info.icone]"></i>{{ info.texto }}</label>
                </template>
              </div>
              <div class="d-flex flex-wrap gap-3">
                <div class="form-check form-switch">
                  <input id="pm" v-model="perfil.pref_musica" class="form-check-input" type="checkbox" role="switch" />
                  <label class="form-check-label small" for="pm">Música no caminho</label>
                </div>
                <div class="form-check form-switch">
                  <input id="pa" v-model="perfil.pref_animais" class="form-check-input" type="checkbox" role="switch" />
                  <label class="form-check-label small" for="pa">Aceito animais</label>
                </div>
                <div class="form-check form-switch">
                  <input id="pf" v-model="perfil.pref_fumar" class="form-check-input" type="checkbox" role="switch" />
                  <label class="form-check-label small" for="pf">Pode fumar no carro</label>
                </div>
              </div>
            </div>
          </div>
          <div class="text-end mt-3">
            <button class="btn btn-primary" :disabled="salvandoPerfil">
              <span v-if="salvandoPerfil" class="spinner-border spinner-border-sm me-1"></span>Salvar dados
            </button>
          </div>
        </form>
      </div>

      <!-- SENHA E VERIFICACAO EM DUAS ETAPAS -->
      <div class="col-lg-5 d-flex flex-column gap-4">
        <form class="card p-4" novalidate @submit.prevent="trocarSenha">
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
        <DoisFatores />
      </div>

      <!-- SEGURANCA: contatos de confianca -->
      <div id="seguranca" class="col-12">
        <div class="card p-4">
          <h2 class="h5 fw-bold mb-1"><i class="bi bi-person-heart me-1"></i>Contatos de confiança</h2>
          <p class="small text-secondary">
            Pessoas que recebem o link para acompanhar sua viagem e o aviso se você apertar o botão de emergência (até 5).
          </p>
          <AlertaMensagem :texto="msgContato.texto" :tipo="msgContato.tipo" @fechar="msgContato.texto = ''" />
          <div v-for="c in contatos" :key="c.id" class="d-flex align-items-center gap-3 border rounded-3 p-2 mb-2">
            <i class="bi bi-person-heart fs-4 text-danger"></i>
            <div class="flex-grow-1"><span class="fw-semibold">{{ c.nome }}</span> <span class="text-secondary">{{ telefoneFormatado(c.telefone) }}</span></div>
            <BotaoConfirmar texto="Remover" pergunta="Remover contato?" icone="bi-trash" :acao="() => removerContato(c)" />
          </div>
          <p v-if="!contatos.length" class="small text-secondary">Nenhum contato cadastrado.</p>
          <form v-if="contatos.length < 5" class="row g-2 align-items-start mt-1" novalidate @submit.prevent="adicionarContato">
            <div class="col-sm-5">
              <input v-model.trim="contato.nome" placeholder="Nome (ex.: Mãe)" aria-label="Nome do contato" :class="['form-control', { 'is-invalid': errosContato.nome }]" />
              <div class="invalid-feedback">{{ errosContato.nome }}</div>
            </div>
            <div class="col-sm-5">
              <input v-model.trim="contato.telefone" type="tel" placeholder="(27) 99999-0000" aria-label="Telefone do contato" :class="['form-control', { 'is-invalid': errosContato.telefone }]" />
              <div class="invalid-feedback">{{ errosContato.telefone }}</div>
            </div>
            <div class="col-sm-2 d-grid">
              <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> Adicionar</button>
            </div>
          </form>
        </div>
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
import DoisFatores from '../components/DoisFatores.vue'
import FotoPerfilEditor from '../components/FotoPerfilEditor.vue'
import api from '../services/api'
import { atualizarUsuario, auth, entrar } from '../stores/auth'
import { BAIRROS } from '../utils/bairros'
import { PREF_CONVERSA, telefoneFormatado } from '../utils/formato'
import { errosDoServidor, regras, validar } from '../utils/validacao'

const perfil = reactive({
  nome: '', telefone: '', bairro: '', curso: '', chave_pix: '', bio: '',
  pref_conversa: 'depende', pref_musica: true, pref_animais: false, pref_fumar: false
})
const msgSelo = reactive({ texto: '', tipo: 'success' })

const contatos = ref([])
const contato = reactive({ nome: '', telefone: '' })
const errosContato = ref({})
const msgContato = reactive({ texto: '', tipo: 'success' })
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
  const p = u.preferencias || {}
  Object.assign(perfil, {
    nome: u.nome, telefone: u.telefone, bairro: u.bairro, curso: u.curso || '', chave_pix: u.chave_pix || '',
    bio: u.bio || '', pref_conversa: p.conversa || 'depende', pref_musica: p.musica ?? true,
    pref_animais: Boolean(p.animais), pref_fumar: Boolean(p.fumar)
  })
}

onMounted(async () => {
  try {
    const [me, vs, cs] = await Promise.all([api.get('/auth/me'), api.get('/veiculos'), api.get('/contatos')])
    atualizarUsuario(me.data.usuario)
    preencher(me.data.usuario)
    veiculos.value = vs.data.veiculos
    contatos.value = cs.data.contatos
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
    errosPerfil.value = { ...errosPerfil.value, ...errosDoServidor(e, Object.keys(perfil)) }
  } finally {
    salvandoPerfil.value = false
  }
}

async function pedirVerificacao() {
  try {
    const { data } = await api.post('/auth/solicitar-verificacao')
    atualizarUsuario(data.usuario)
    msgSelo.texto = 'Pedido enviado! A administração confere sua matrícula e aprova o selo.'
    msgSelo.tipo = 'success'
  } catch (e) {
    msgSelo.texto = e.mensagem
    msgSelo.tipo = 'danger'
  }
}

async function adicionarContato() {
  msgContato.texto = ''
  errosContato.value = validar(contato, { nome: [regras.obrigatorio], telefone: [regras.obrigatorio, regras.telefone] })
  if (Object.keys(errosContato.value).length) return
  try {
    const { data } = await api.post('/contatos', contato)
    contatos.value.push(data.contato)
    Object.assign(contato, { nome: '', telefone: '' })
    msgContato.texto = 'Contato adicionado.'
    msgContato.tipo = 'success'
  } catch (e) {
    msgContato.texto = e.mensagem
    msgContato.tipo = 'danger'
    errosContato.value = errosDoServidor(e, ['nome', 'telefone'])
  }
}

async function removerContato(c) {
  try {
    await api.delete(`/contatos/${c.id}`)
    contatos.value = contatos.value.filter((x) => x.id !== c.id)
  } catch (e) {
    msgContato.texto = e.mensagem
    msgContato.tipo = 'danger'
  }
}

async function trocarSenha() {
  msgSenha.texto = ''
  errosSenha.value = validar(senha, { senha_atual: [regras.obrigatorio], nova_senha: [regras.obrigatorio, regras.senha] })
  if (Object.keys(errosSenha.value).length) return
  salvandoSenha.value = true
  try {
    const { data } = await api.put('/auth/me', senha)
    // A troca de senha encerra os logins antigos; este aparelho recebe um token novo
    if (data.token) entrar(data.token, data.usuario)
    Object.assign(senha, { senha_atual: '', nova_senha: '' })
    msgSenha.texto = 'Senha alterada. Os outros aparelhos em que você estava logado foram desconectados.'
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
    errosVeiculo.value = errosDoServidor(e, ['modelo', 'cor', 'placa'])
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
