import type { ErrosCampos } from '../types/api'
import { pareceEndereco } from './bairros'

// ==========================================================
// Validacao dos formularios no navegador.
// A API valida tudo de novo no servidor (services.py); aqui e so para
// avisar o usuario antes de enviar e mostrar o erro ao lado do campo.
// ==========================================================

/** Uma regra recebe o valor do campo (e o formulario inteiro) e devolve a mensagem de erro ou null. */
export type Regra = (valor: unknown, dados?: Record<string, unknown>) => string | null

const texto = (v: unknown): string => String(v ?? '')

export const regras = {
  obrigatorio: (v) => (texto(v).trim() ? null : 'Campo obrigatório.'),
  email: (v) => (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(texto(v).trim()) ? null : 'E-mail inválido.'),
  // So alunos da UVV: e-mail institucional (aceita subdominios, ex.: aluno.uvv.br)
  emailUvv: (v) => (/@([a-z0-9-]+\.)*uvv\.br$/i.test(texto(v).trim()) ? null : 'Use seu e-mail institucional (@uvv.br).'),
  codigo: (v) => (/^\d{6}$/.test(texto(v).trim()) ? null : 'O código tem 6 números.'),
  pin: (v) => (/^\d{4}$/.test(texto(v).trim()) ? null : 'O PIN tem 4 números.'),
  senha: (v) => (texto(v).length >= 6 ? null : 'A senha precisa ter pelo menos 6 caracteres.'),
  telefone: (v) => {
    const n = texto(v).replace(/\D/g, '')
    return n.length >= 10 && n.length <= 13 ? null : 'Informe o telefone com DDD.'
  },
  bairro: (v) => (pareceEndereco(texto(v)) ? 'Aqui vai só o bairro (ex.: Itapuã); a rua vai no campo de rua/endereço.' : null),
  matricula: (v) => (/^\d{5,12}$/.test(texto(v).trim()) ? null : 'A matrícula tem de 5 a 12 números.'),
  placa: (v) =>
    /^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(texto(v).replace(/[\s-]/g, '').toUpperCase())
      ? null
      : 'Placa inválida (ex.: ABC1234 ou ABC1D23).'
} satisfies Record<string, Regra>

/**
 * Aplica as regras de cada campo e devolve { campo: 'mensagem' } so com os erros.
 * Exemplo: validar(form, { email: [regras.obrigatorio, regras.email] })
 * O esquema so aceita nomes de campos que existem no formulario.
 */
export function validar<T extends object>(dados: T, esquema: Partial<Record<keyof T & string, Regra[]>>): ErrosCampos {
  const erros: ErrosCampos = {}
  const valores = dados as Record<string, unknown>
  for (const [campo, lista] of Object.entries(esquema) as [string, Regra[] | undefined][]) {
    for (const regra of lista ?? []) {
      const msg = regra(valores[campo], valores)
      if (msg) {
        erros[campo] = msg
        break
      }
    }
  }
  return erros
}

/**
 * Junta os erros de campo que vieram do servidor (validacao Pydantic, campo
 * "campos" da resposta) com os do navegador. Assim, mesmo uma regra que so o
 * servidor conhece aparece embaixo do campo certo.
 */
export function errosDoServidor(erro: unknown, camposDoFormulario: readonly string[]): ErrosCampos {
  const vindos: ErrosCampos =
    erro && typeof erro === 'object' && 'campos' in erro && erro.campos && typeof erro.campos === 'object'
      ? (erro.campos as ErrosCampos)
      : {}
  return Object.fromEntries(Object.entries(vindos).filter(([campo]) => camposDoFormulario.includes(campo)))
}
