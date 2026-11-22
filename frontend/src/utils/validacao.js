// ==========================================================
// Validacao dos formularios no navegador.
// A API valida tudo de novo no servidor (services.py); aqui e so para
// avisar o usuario antes de enviar e mostrar o erro ao lado do campo.
// ==========================================================
export const regras = {
  obrigatorio: (v) => (String(v ?? '').trim() ? null : 'Campo obrigatório.'),
  email: (v) => (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v || '').trim()) ? null : 'E-mail inválido.'),
  senha: (v) => (String(v || '').length >= 6 ? null : 'A senha precisa ter pelo menos 6 caracteres.'),
  telefone: (v) => {
    const n = String(v || '').replace(/\D/g, '')
    return n.length >= 10 && n.length <= 13 ? null : 'Informe o telefone com DDD.'
  },
  matricula: (v) => (/^\d{5,12}$/.test(String(v || '').trim()) ? null : 'A matrícula tem só números.'),
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
