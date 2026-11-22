import { computed, reactive } from 'vue'

// ==========================================================
// Estado de login compartilhado entre as telas.
// O token fica no sessionStorage: cada aba tem a sua sessao, entao da para
// deixar o motorista numa aba e o passageiro em outra no mesmo navegador.
// Recarregar a pagina mantem o login; fechar a aba encerra (o logout so
// descarta o token).
// ==========================================================
const CHAVE = 'caronauvv.sessao'
const armazenamento = (() => {
  try {
    return window.sessionStorage
  } catch {
    return { getItem: () => null, setItem: () => {}, removeItem: () => {} }
  }
})()

function lerSessao() {
  try {
    return JSON.parse(armazenamento.getItem(CHAVE)) || {}
  } catch {
    return {}
  }
}

const salvo = lerSessao()

export const auth = reactive({
  token: salvo.token || null,
  usuario: salvo.usuario || null
})

export const logado = computed(() => Boolean(auth.token))

// Modo desenvolvimento/apresentacao: sem servidor de e-mail, a API devolve o
// codigo de verificacao ("codigo_dev") e a tela de confirmacao o mostra.
export const demo = reactive({ codigoDev: null })

function persistir() {
  try {
    if (auth.token) {
      armazenamento.setItem(CHAVE, JSON.stringify({ token: auth.token, usuario: auth.usuario }))
    } else {
      armazenamento.removeItem(CHAVE)
    }
  } catch {
    /* navegador sem sessionStorage: a sessao dura so enquanto a pagina estiver aberta */
  }
}

export function entrar(token, usuario) {
  auth.token = token
  auth.usuario = usuario
  persistir()
}

export function atualizarUsuario(usuario) {
  auth.usuario = usuario
  persistir()
}

export function sair() {
  auth.token = null
  auth.usuario = null
  persistir()
}
