import { computed, reactive } from 'vue'

import type { UsuarioLogado } from '../types/api'

// ==========================================================
// Estado de login compartilhado entre as telas.
// O token fica no sessionStorage: cada aba tem a sua sessao, entao da para
// deixar o motorista numa aba e o passageiro em outra no mesmo navegador.
// Recarregar a pagina mantem o login; fechar a aba encerra (o logout so
// descarta o token).
// ==========================================================
const CHAVE = 'caronauvv.sessao'

interface SessaoSalva {
  token?: string | null
  usuario?: UsuarioLogado | null
}

type Armazenamento = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>

const armazenamento: Armazenamento = (() => {
  try {
    return window.sessionStorage
  } catch {
    return { getItem: () => null, setItem: () => {}, removeItem: () => {} }
  }
})()

function lerSessao(): SessaoSalva {
  try {
    return (JSON.parse(armazenamento.getItem(CHAVE) ?? 'null') as SessaoSalva | null) || {}
  } catch {
    return {}
  }
}

const salvo = lerSessao()

export const auth = reactive<{ token: string | null; usuario: UsuarioLogado | null }>({
  token: salvo.token || null,
  usuario: salvo.usuario || null
})

export const logado = computed(() => Boolean(auth.token))

// Modo desenvolvimento/apresentacao: sem servidor de e-mail, a API devolve o
// codigo de verificacao ("codigo_dev") e a tela de confirmacao o mostra.
export const demo = reactive<{ codigoDev: string | null }>({ codigoDev: null })

function persistir(): void {
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

export type TipoAviso = 'info' | 'success' | 'warning' | 'danger'

// Aviso que precisa sobreviver a troca de tela (ex.: "voce entrou com um codigo de reserva")
export const avisoGlobal = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'info' })

export function entrar(token: string, usuario: UsuarioLogado): void {
  auth.token = token
  auth.usuario = usuario
  persistir()
}

export function atualizarUsuario(usuario: UsuarioLogado): void {
  auth.usuario = usuario
  persistir()
}

export function sair(): void {
  auth.token = null
  auth.usuario = null
  persistir()
}
