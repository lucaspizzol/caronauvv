import axios from 'axios'

import { auth, sair } from '../stores/auth'

// ==========================================================
// Cliente HTTP da API Flask
// - envia o token de login em todas as requisicoes
// - transforma qualquer erro em uma mensagem legivel (campo "error" da API)
// - repassa o erro de cada campo do formulario (campo "campos" da API, vindo
//   da validacao Pydantic no servidor) para a tela marcar o campo certo
// ==========================================================
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
  (erro) => {
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

export default api
