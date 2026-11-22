// ==========================================================
// Formatacao de datas, valores e status para exibicao
// ==========================================================
const DIAS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

export function paraData(iso) {
  // A API envia "AAAA-MM-DDTHH:MM" no horario local
  return iso ? new Date(iso) : null
}

export function dataCurta(iso) {
  const d = paraData(iso)
  if (!d) return ''
  const hoje = new Date()
  const amanha = new Date()
  amanha.setDate(hoje.getDate() + 1)
  const mesmoDia = (a, b) => a.toDateString() === b.toDateString()
  if (mesmoDia(d, hoje)) return 'Hoje'
  if (mesmoDia(d, amanha)) return 'Amanhã'
  return `${DIAS[d.getDay()]}, ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
}

export function hora(iso) {
  const d = paraData(iso)
  return d ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : ''
}

export function dinheiro(valor) {
  const numero = Number(valor || 0)
  return numero === 0 ? 'Grátis' : numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export function jaSaiu(iso) {
  const d = paraData(iso)
  return d ? d <= new Date() : false
}

export function linkWhatsApp(telefone, texto = '') {
  const numero = String(telefone || '').replace(/\D/g, '')
  const comPais = numero.startsWith('55') ? numero : `55${numero}`
  return `https://wa.me/${comPais}${texto ? `?text=${encodeURIComponent(texto)}` : ''}`
}

export function telefoneFormatado(telefone) {
  const n = String(telefone || '').replace(/\D/g, '')
  if (n.length === 11) return `(${n.slice(0, 2)}) ${n.slice(2, 7)}-${n.slice(7)}`
  if (n.length === 10) return `(${n.slice(0, 2)}) ${n.slice(2, 6)}-${n.slice(6)}`
  return telefone || ''
}

export const STATUS_CARONA = {
  ativa: { texto: 'Ativa', cor: 'success' },
  lotada: { texto: 'Lotada', cor: 'warning' },
  em_andamento: { texto: 'Em andamento', cor: 'info' },
  concluida: { texto: 'Concluída', cor: 'secondary' },
  cancelada: { texto: 'Cancelada', cor: 'danger' }
}

export const STATUS_PEDIDO = {
  pendente: { texto: 'Aguardando motorista', cor: 'warning' },
  aceita: { texto: 'Vaga confirmada', cor: 'success' },
  recusada: { texto: 'Recusado', cor: 'danger' },
  cancelada: { texto: 'Cancelado', cor: 'secondary' },
  expirada: { texto: 'Expirado', cor: 'secondary' }
}

export function iniciais(nome) {
  return String(nome || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

// Data de hoje no fuso do navegador, no formato AAAA-MM-DD (para <input type="date">)
export function hojeLocal(deslocamentoDias = 0) {
  const d = new Date()
  d.setDate(d.getDate() + deslocamentoDias)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
