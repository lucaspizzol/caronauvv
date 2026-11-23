// ==========================================================
// Validacao dos formularios no navegador.
// A API valida tudo de novo no servidor (services.py); aqui e so para
// avisar o usuario antes de enviar e mostrar o erro ao lado do campo.
// ==========================================================
export const regras = {
  obrigatorio: (v) => (String(v ?? '').trim() ? null : 'Campo obrigatório.'),
  email: (v) => (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v || '').trim()) ? null : 'E-mail inválido.'),
  // So alunos da UVV: e-mail institucional (aceita subdominios, ex.: aluno.uvv.br)
  emailUvv: (v) => (/@([a-z0-9-]+\.)*uvv\.br$/i.test(String(v || '').trim()) ? null : 'Use seu e-mail institucional (@uvv.br).'),
  codigo: (v) => (/^\d{6}$/.test(String(v || '').trim()) ? null : 'O código tem 6 números.'),
  pin: (v) => (/^\d{4}$/.test(String(v || '').trim()) ? null : 'O PIN tem 4 números.'),
  senha: (v) => (String(v || '').length >= 6 ? null : 'A senha precisa ter pelo menos 6 caracteres.'),
  telefone: (v) => {
    const n = String(v || '').replace(/\D/g, '')
    return n.length >= 10 && n.length <= 13 ? null : 'Informe o telefone com DDD.'
  },
  matricula: (v) => (/^\d{5,12}$/.test(String(v || '').trim()) ? null : 'A matrícula tem de 5 a 12 números.'),
  placa: (v) =>
    /^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(String(v || '').replace(/[\s-]/g, '').toUpperCase())
      ? null
      : 'Placa inválida (ex.: ABC1234 ou ABC1D23).'
}

/**
 * Aplica as regras de cada campo e devolve { campo: 'mensagem' } so com os erros.
 * Exemplo: validar(form, { email: [regras.obrigatorio, regras.email] })
 */
export function validar(dados, esquema) {
  const erros = {}
  for (const [campo, lista] of Object.entries(esquema)) {
    for (const regra of lista) {
      const msg = regra(dados[campo], dados)
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
export function errosDoServidor(erro, camposDoFormulario) {
  const vindos = erro?.campos || {}
  return Object.fromEntries(Object.entries(vindos).filter(([campo]) => camposDoFormulario.includes(campo)))
}
