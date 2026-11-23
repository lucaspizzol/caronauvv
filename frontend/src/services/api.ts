import axios, { type AxiosError } from 'axios'

import { auth, sair } from '../stores/auth'
import type { ErrosCampos } from '../types/api'

// ==========================================================
// Cliente HTTP da API Flask
// - envia o token de login em todas as requisicoes
// - transforma qualquer erro em uma mensagem legivel (campo "error" da API)
// - repassa o erro de cada campo do formulario (campo "campos" da API, vindo
//   da validacao Pydantic no servidor) para a tela marcar o campo certo
// ==========================================================

/** Corpo de erro que a API devolve (caronauvv/errors.py). */
interface CorpoErro {
  error?: string
  campos?: ErrosCampos
}

/** Erro do axios ja com a mensagem em portugues e os erros por campo. */
export interface ErroApi extends AxiosError<CorpoErro> {
  mensagem: string
  campos: ErrosCampos
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000
})

api.interceptors.request.use((config) => {
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

api.interceptors.response.use(
  (resposta) => resposta,
  (erroOriginal: AxiosError<CorpoErro>) => {
    const erro = erroOriginal as ErroApi
    const status = erro.response?.status
    // Token vencido ou invalido: volta para o login
    if (status === 401 && auth.token) {
      sair()
      if (!location.pathname.startsWith('/login')) {
        location.assign(`/login?expirou=1&volta=${encodeURIComponent(location.pathname)}`)
      }
    }
    erro.campos = erro.response?.data?.campos || {}
    erro.mensagem =
      erro.response?.data?.error ||
      (erro.code === 'ECONNABORTED'
        ? 'O servidor demorou para responder. Tente de novo.'
        : !erro.response
          ? 'Não foi possível conectar à API. Confira se o Flask está rodando.'
          : 'Algo deu errado. Tente novamente.')
    return Promise.reject(erro)
  }
)

/**
 * Mensagem legivel de qualquer erro pego num `catch`. No TypeScript o erro do
 * `catch` e `unknown`: esta funcao confere o formato antes de ler a mensagem.
 */
export function mensagemDeErro(erro: unknown, padrao = 'Algo deu errado. Tente novamente.'): string {
  if (erro && typeof erro === 'object' && 'mensagem' in erro && typeof erro.mensagem === 'string') {
    return erro.mensagem
  }
  if (erro instanceof Error && erro.message) return erro.message
  return padrao
}

/** Erros por campo que vieram do servidor (vazio se o erro nao veio da API). */
export function camposDoErro(erro: unknown): ErrosCampos {
  if (erro && typeof erro === 'object' && 'campos' in erro && erro.campos && typeof erro.campos === 'object') {
    return erro.campos as ErrosCampos
  }
  return {}
}

/** Status HTTP do erro da API (ou undefined se nem chegou a resposta). */
export function statusDoErro(erro: unknown): number | undefined {
  return axios.isAxiosError(erro) ? erro.response?.status : undefined
}

export default api
