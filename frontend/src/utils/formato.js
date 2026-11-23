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
  // Sem numero: o WhatsApp abre e a pessoa escolhe o contato
  if (!numero) return `https://wa.me/${texto ? `?text=${encodeURIComponent(texto)}` : ''}`
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

// Endereco completo da foto de perfil. A API devolve "/api/fotos/<token>"; se o
// frontend estiver em outro dominio (VITE_API_URL), troca o comeco pelo da API.
export function urlFoto(caminho, base = import.meta.env?.VITE_API_URL || '/api') {
  if (!caminho) return ''
  return caminho.startsWith('/api/') ? `${base.replace(/\/$/, '')}${caminho.slice(4)}` : caminho
}

// Codigo de reserva do autenticador: "abcdefgh" -> "ABCD-EFGH" enquanto a pessoa digita
export function codigoReservaFormatado(texto) {
  const limpo = String(texto || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8)
  return limpo.length > 4 ? `${limpo.slice(0, 4)}-${limpo.slice(4)}` : limpo
}

// Data de hoje no fuso do navegador, no formato AAAA-MM-DD (para <input type="date">)
export function hojeLocal(deslocamentoDias = 0) {
  const d = new Date()
  d.setDate(d.getDate() + deslocamentoDias)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ==========================================================
// Reputacao, preferencias e textos de confianca
// ==========================================================
export function nota(valor) {
  return valor == null ? 'Novo' : Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

export const PREF_CONVERSA = {
  quieto: { texto: 'Prefere silêncio', icone: 'bi-chat' },
  depende: { texto: 'Conversa se você quiser', icone: 'bi-chat-dots' },
  conversador: { texto: 'Adora conversar', icone: 'bi-chat-heart' }
}

export function listaPreferencias(p) {
  if (!p) return []
  const conversa = PREF_CONVERSA[p.conversa] || PREF_CONVERSA.depende
  return [
    conversa,
    p.musica ? { texto: 'Curte música', icone: 'bi-music-note-beamed' } : { texto: 'Sem música', icone: 'bi-volume-mute' },
    p.animais ? { texto: 'Aceita animais', icone: 'bi-heart' } : { texto: 'Sem animais', icone: 'bi-slash-circle' },
    p.fumar ? { texto: 'Pode fumar', icone: 'bi-cloud' } : { texto: 'Não fuma no carro', icone: 'bi-ban' }
  ]
}

export const MOTIVOS_DENUNCIA = {
  nao_compareceu: 'Não compareceu',
  direcao_perigosa: 'Direção perigosa',
  comportamento_inadequado: 'Comportamento inadequado',
  assedio: 'Assédio',
  cobranca_indevida: 'Cobrança indevida',
  perfil_falso: 'Perfil falso',
  outro: 'Outro motivo'
}

// "2026-11-22T19:40" -> "22/11/2026"
export function dataCurtaNumerica(iso) {
  const d = paraData(iso)
  if (!d) return ''
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
}

export function dataHora(iso) {
  const d = paraData(iso)
  return d ? `${dataCurta(iso)} ${hora(iso)}` : ''
}

export function membroDesde(isoData) {
  if (!isoData) return ''
  const [ano, mes] = isoData.split('-')
  const meses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
  return `${meses[Number(mes) - 1]}/${ano}`
}

export function porcentagem(fracao) {
  return `${Math.round(Number(fracao || 0) * 100)}%`
}
