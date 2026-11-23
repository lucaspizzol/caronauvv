<template>
  <div class="container py-4" style="max-width: 860px">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-2 mb-3">
      <h1 class="titulo-pagina h3 mb-0">Meu perfil</h1>
      <RouterLink v-if="auth.usuario && !ehAdmin" :to="`/usuarios/${auth.usuario.id}`" class="btn btn-sm btn-outline-primary">
        <i class="bi bi-eye me-1"></i>Ver como os outros me veem
      </RouterLink>
    </div>

    <!-- CONFIANCA: e-mail confirmado e selo de perfil verificado (so alunos) -->
    <div v-if="!ehAdmin" class="card p-3 mb-4">
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

    <DocumentosVerificacao v-if="!ehAdmin" id="documentos" class="mb-4" />

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
              <CampoBairro id="p-bairro" v-model="perfil.bairro" :invalido="Boolean(errosPerfil.bairro)" />
              <div v-if="errosPerfil.bairro" class="invalid-feedback d-block">{{ errosPerfil.bairro }}</div>
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
            <div v-if="!ehAdmin" class="col-12">
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
      <div v-if="!ehAdmin" id="seguranca" class="col-12">
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
      <div v-if="!ehAdmin" id="veiculos" class="col-12">
        <div class="card p-4">
          <h2 class="h5 fw-bold mb-1"><i class="bi bi-car-front me-1"></i>Meus carros</h2>
          <p class="small text-secondary">
            A placa só aparece para o passageiro depois que a vaga é confirmada. O tipo de combustível e o consumo
            entram no cálculo do rateio ao oferecer carona.
          </p>
          <AlertaMensagem :texto="msgVeiculo.texto" :tipo="msgVeiculo.tipo" @fechar="msgVeiculo.texto = ''" />

          <div v-for="v in veiculos" :key="v.id" :class="['d-flex flex-wrap align-items-center gap-2 gap-sm-3 border rounded-3 p-2 mb-2', { 'border-primary': editandoId === v.id }]">
            <i :class="['bi fs-4 text-primary', ENERGIAS[v.energia].icone]"></i>
            <div class="flex-grow-1 min-w-0">
              <span class="fw-semibold">{{ v.modelo }}</span> <span class="text-secondary">{{ v.cor }}</span>
              <span class="badge text-bg-light border ms-2">{{ v.placa }}</span>
              <div class="small text-secondary">
                {{ ENERGIAS[v.energia].texto }} ·
                <span v-if="v.consumo_km">{{ numeroBr(v.consumo_km, 1) }} {{ unidadeConsumo(v.energia) }}</span>
                <span v-else class="text-warning-emphasis">consumo não informado (usa a média de {{ numeroBr(ENERGIAS[v.energia].consumoMedio, 1) }} {{ unidadeConsumo(v.energia) }})</span>
              </div>
            </div>
            <button type="button" class="btn btn-sm btn-light" @click="editarVeiculo(v)"><i class="bi bi-pencil me-1"></i>Editar</button>
            <BotaoConfirmar texto="Remover" pergunta="Remover este carro?" icone="bi-trash" :acao="() => removerVeiculo(v)" />
          </div>
          <p v-if="!veiculos.length" class="small text-secondary">Nenhum carro cadastrado.</p>

          <form class="row g-2 align-items-start mt-1" novalidate @submit.prevent="salvarVeiculo">
            <div v-if="editandoId" class="col-12 small fw-semibold text-primary"><i class="bi bi-pencil me-1"></i>Editando o carro {{ veiculo.placa }}</div>
            <div class="col-sm-4">
              <input v-model.trim="veiculo.modelo" placeholder="Modelo (ex.: HB20)" aria-label="Modelo" :class="['form-control', { 'is-invalid': errosVeiculo.modelo }]" />
              <div class="invalid-feedback">{{ errosVeiculo.modelo }}</div>
            </div>
            <div class="col-sm-4">
              <input v-model.trim="veiculo.cor" placeholder="Cor" aria-label="Cor" :class="['form-control', { 'is-invalid': errosVeiculo.cor }]" />
              <div class="invalid-feedback">{{ errosVeiculo.cor }}</div>
            </div>
            <div class="col-sm-4">
              <input v-model.trim="veiculo.placa" placeholder="Placa" aria-label="Placa" maxlength="8" style="text-transform: uppercase" :class="['form-control', { 'is-invalid': errosVeiculo.placa }]" />
              <div class="invalid-feedback">{{ errosVeiculo.placa }}</div>
            </div>
            <div class="col-sm-5">
              <select v-model="veiculo.energia" class="form-select" aria-label="Tipo de combustível">
                <option v-for="(info, chave) in ENERGIAS" :key="chave" :value="chave">{{ info.texto }}</option>
              </select>
            </div>
            <div class="col-sm-4">
              <div class="input-group has-validation">
                <input
                  v-model.number="veiculo.consumo_km" type="number" min="0.1" max="60" step="0.1" aria-label="Consumo"
                  :placeholder="`Consumo (média ${numeroBr(ENERGIAS[veiculo.energia].consumoMedio, 1)})`"
                  :class="['form-control', { 'is-invalid': errosVeiculo.consumo_km }]"
                />
                <span class="input-group-text">{{ unidadeConsumo(veiculo.energia) }}</span>
                <div class="invalid-feedback">{{ errosVeiculo.consumo_km }}</div>
              </div>
            </div>
            <div class="col-sm-3 d-flex gap-2">
              <button class="btn btn-primary flex-grow-1">
                <i :class="['bi', editandoId ? 'bi-check-lg' : 'bi-plus-lg']"></i> {{ editandoId ? 'Salvar' : 'Adicionar' }}
              </button>
              <button v-if="editandoId" type="button" class="btn btn-light" aria-label="Cancelar edição" @click="limparVeiculo"><i class="bi bi-x-lg"></i></button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import CampoBairro from '../components/CampoBairro.vue'
import BotaoConfirmar from '../components/BotaoConfirmar.vue'
import DocumentosVerificacao from '../components/DocumentosVerificacao.vue'
import DoisFatores from '../components/DoisFatores.vue'
import FotoPerfilEditor from '../components/FotoPerfilEditor.vue'
import api, { mensagemDeErro } from '../services/api'
import { atualizarUsuario, auth, entrar, type TipoAviso } from '../stores/auth'
import type { ContatoConfianca, Energia, ErrosCampos, NivelConversa, UsuarioLogado, Veiculo } from '../types/api'
import { ENERGIAS, numeroBr, PREF_CONVERSA, telefoneFormatado, unidadeConsumo } from '../utils/formato'
import { errosDoServidor, regras, validar } from '../utils/validacao'

// O administrador nao oferece nem pede carona: o perfil dele mostra so dados, foto, senha e duas etapas
const ehAdmin = computed(() => Boolean(auth.usuario?.is_admin))

/** Mensagem curta mostrada embaixo de cada cartao da tela. */
type Aviso = { texto: string; tipo: TipoAviso }
const novoAviso = (): Aviso => reactive({ texto: '', tipo: 'success' })

interface FormPerfil {
  nome: string
  telefone: string
  bairro: string
  curso: string
  chave_pix: string
  bio: string
  pref_conversa: NivelConversa
  pref_musica: boolean
  pref_animais: boolean
  pref_fumar: boolean
}

const perfil = reactive<FormPerfil>({
  nome: '', telefone: '', bairro: '', curso: '', chave_pix: '', bio: '',
  pref_conversa: 'depende', pref_musica: true, pref_animais: false, pref_fumar: false
})
const msgSelo = novoAviso()

const contatos = ref<ContatoConfianca[]>([])
const contato = reactive({ nome: '', telefone: '' })
const errosContato = ref<ErrosCampos>({})
const msgContato = novoAviso()
const errosPerfil = ref<ErrosCampos>({})
const msgPerfil = novoAviso()
const salvandoPerfil = ref(false)

const senha = reactive({ senha_atual: '', nova_senha: '' })
const errosSenha = ref<ErrosCampos>({})
const msgSenha = novoAviso()
const salvandoSenha = ref(false)

const veiculos = ref<Veiculo[]>([])
interface FormVeiculo {
  modelo: string
  cor: string
  placa: string
  energia: Energia
  consumo_km: number | '' // vazio = nao informado (o calculo usa a media)
}
const VEICULO_VAZIO: FormVeiculo = { modelo: '', cor: '', placa: '', energia: 'flex', consumo_km: '' }
const veiculo = reactive<FormVeiculo>({ ...VEICULO_VAZIO })
const editandoId = ref<number | null>(null)
const errosVeiculo = ref<ErrosCampos>({})
const msgVeiculo = novoAviso()

function avisar(msg: Aviso, texto: string, tipo: TipoAviso = 'success'): void {
  msg.texto = texto
  msg.tipo = tipo
}

function preencher(u: UsuarioLogado): void {
  const p = u.preferencias
  Object.assign(perfil, {
    nome: u.nome, telefone: u.telefone, bairro: u.bairro, curso: u.curso || '', chave_pix: u.chave_pix || '',
    bio: u.bio || '', pref_conversa: p?.conversa || 'depende', pref_musica: p?.musica ?? true,
    pref_animais: Boolean(p?.animais), pref_fumar: Boolean(p?.fumar)
  } satisfies FormPerfil)
}

onMounted(async () => {
  try {
    const [me, vs, cs] = await Promise.all([
      api.get<{ usuario: UsuarioLogado }>('/auth/me'),
      api.get<{ veiculos: Veiculo[] }>('/veiculos'),
      api.get<{ contatos: ContatoConfianca[] }>('/contatos')
    ])
    atualizarUsuario(me.data.usuario)
    preencher(me.data.usuario)
    veiculos.value = vs.data.veiculos
    contatos.value = cs.data.contatos
  } catch (e) {
    avisar(msgPerfil, mensagemDeErro(e), 'danger')
  }
})

async function salvarPerfil(): Promise<void> {
  msgPerfil.texto = ''
  errosPerfil.value = validar(perfil, {
    nome: [regras.obrigatorio],
    telefone: [regras.obrigatorio, regras.telefone],
    bairro: [regras.obrigatorio, regras.bairro]
  })
  if (Object.keys(errosPerfil.value).length) return
  salvandoPerfil.value = true
  try {
    const { data } = await api.put<{ usuario: UsuarioLogado }>('/auth/me', perfil)
    atualizarUsuario(data.usuario)
    avisar(msgPerfil, 'Dados atualizados.')
  } catch (e) {
    avisar(msgPerfil, mensagemDeErro(e), 'danger')
    errosPerfil.value = { ...errosPerfil.value, ...errosDoServidor(e, Object.keys(perfil)) }
  } finally {
    salvandoPerfil.value = false
  }
}

async function pedirVerificacao(): Promise<void> {
  try {
    const { data } = await api.post<{ usuario: UsuarioLogado }>('/auth/solicitar-verificacao')
    atualizarUsuario(data.usuario)
    avisar(msgSelo, 'Pedido enviado! A administração confere sua matrícula e aprova o selo.')
  } catch (e) {
    avisar(msgSelo, mensagemDeErro(e), 'danger')
  }
}

async function adicionarContato(): Promise<void> {
  msgContato.texto = ''
  errosContato.value = validar(contato, { nome: [regras.obrigatorio], telefone: [regras.obrigatorio, regras.telefone] })
  if (Object.keys(errosContato.value).length) return
  try {
    const { data } = await api.post<{ contato: ContatoConfianca }>('/contatos', contato)
    contatos.value.push(data.contato)
    Object.assign(contato, { nome: '', telefone: '' })
    avisar(msgContato, 'Contato adicionado.')
  } catch (e) {
    avisar(msgContato, mensagemDeErro(e), 'danger')
    errosContato.value = errosDoServidor(e, ['nome', 'telefone'])
  }
}

async function removerContato(c: ContatoConfianca): Promise<void> {
  try {
    await api.delete(`/contatos/${c.id}`)
    contatos.value = contatos.value.filter((x) => x.id !== c.id)
  } catch (e) {
    avisar(msgContato, mensagemDeErro(e), 'danger')
  }
}

async function trocarSenha(): Promise<void> {
  msgSenha.texto = ''
  errosSenha.value = validar(senha, { senha_atual: [regras.obrigatorio], nova_senha: [regras.obrigatorio, regras.senha] })
  if (Object.keys(errosSenha.value).length) return
  salvandoSenha.value = true
  try {
    const { data } = await api.put<{ usuario: UsuarioLogado; token?: string }>('/auth/me', senha)
    // A troca de senha encerra os logins antigos; este aparelho recebe um token novo
    if (data.token) entrar(data.token, data.usuario)
    Object.assign(senha, { senha_atual: '', nova_senha: '' })
    avisar(msgSenha, 'Senha alterada. Os outros aparelhos em que você estava logado foram desconectados.')
  } catch (e) {
    avisar(msgSenha, mensagemDeErro(e), 'danger')
  } finally {
    salvandoSenha.value = false
  }
}

function limparVeiculo(): void {
  Object.assign(veiculo, VEICULO_VAZIO)
  editandoId.value = null
  errosVeiculo.value = {}
}

function editarVeiculo(v: Veiculo): void {
  Object.assign(veiculo, { modelo: v.modelo, cor: v.cor, placa: v.placa || '', energia: v.energia, consumo_km: v.consumo_km ?? '' })
  editandoId.value = v.id
  errosVeiculo.value = {}
  msgVeiculo.texto = ''
}

async function salvarVeiculo(): Promise<void> {
  msgVeiculo.texto = ''
  errosVeiculo.value = validar(veiculo, {
    modelo: [regras.obrigatorio],
    cor: [regras.obrigatorio],
    placa: [regras.obrigatorio, regras.placa],
    consumo_km: [(v) => (v === '' || v === null || (Number(v) > 0 && Number(v) <= 60) ? null : 'Entre 0,1 e 60.')]
  })
  if (Object.keys(errosVeiculo.value).length) return
  const corpo = { ...veiculo, consumo_km: veiculo.consumo_km === '' ? null : Number(veiculo.consumo_km) }
  try {
    if (editandoId.value) {
      const { data } = await api.put<{ veiculo: Veiculo }>(`/veiculos/${editandoId.value}`, corpo)
      veiculos.value = veiculos.value.map((v) => (v.id === data.veiculo.id ? data.veiculo : v))
      avisar(msgVeiculo, 'Carro atualizado.')
    } else {
      const { data } = await api.post<{ veiculo: Veiculo }>('/veiculos', corpo)
      veiculos.value.push(data.veiculo)
      avisar(msgVeiculo, 'Carro cadastrado.')
    }
    limparVeiculo()
  } catch (e) {
    avisar(msgVeiculo, mensagemDeErro(e), 'danger')
    errosVeiculo.value = errosDoServidor(e, ['modelo', 'cor', 'placa', 'energia', 'consumo_km'])
  }
}

async function removerVeiculo(v: Veiculo): Promise<void> {
  try {
    await api.delete(`/veiculos/${v.id}`)
    veiculos.value = veiculos.value.filter((x) => x.id !== v.id)
    avisar(msgVeiculo, 'Carro removido.')
  } catch (e) {
    avisar(msgVeiculo, mensagemDeErro(e), 'danger')
  }
}
</script>
