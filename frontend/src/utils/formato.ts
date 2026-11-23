import type { DataIso, NivelConversa, Preferencias, StatusCarona, StatusSolicitacao } from '../types/api'

// ==========================================================
// Formatacao de datas, valores e status para exibicao
// ==========================================================
const DIAS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

/** Texto da API que pode faltar (campo opcional). */
type Talvez<T> = T | null | undefined

const doisDigitos = (n: number): string => String(n).padStart(2, '0')

export function paraData(iso: Talvez<DataIso>): Date | null {
  // A API envia "AAAA-MM-DDTHH:MM" no horario local
  return iso ? new Date(iso) : null
}

export function dataCurta(iso: Talvez<DataIso>): string {
  const d = paraData(iso)
  if (!d) return ''
  const hoje = new Date()
  const amanha = new Date()
  amanha.setDate(hoje.getDate() + 1)
  const mesmoDia = (a: Date, b: Date) => a.toDateString() === b.toDateString()
  if (mesmoDia(d, hoje)) return 'Hoje'
  if (mesmoDia(d, amanha)) return 'Amanhã'
  return `${DIAS[d.getDay()]}, ${doisDigitos(d.getDate())}/${doisDigitos(d.getMonth() + 1)}`
}

export function hora(iso: Talvez<DataIso>): string {
  const d = paraData(iso)
  return d ? `${doisDigitos(d.getHours())}:${doisDigitos(d.getMinutes())}` : ''
}

export function dinheiro(valor: Talvez<number | string>): string {
  const numero = Number(valor || 0)
  return numero === 0 ? 'Grátis' : numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export function jaSaiu(iso: Talvez<DataIso>): boolean {
  const d = paraData(iso)
  return d ? d <= new Date() : false
}

export function linkWhatsApp(telefone: Talvez<string>, texto = ''): string {
  const numero = String(telefone || '').replace(/\D/g, '')
  const mensagem = texto ? `?text=${encodeURIComponent(texto)}` : ''
  // Sem numero: o WhatsApp abre e a pessoa escolhe o contato
  if (!numero) return `https://wa.me/${mensagem}`
  const comPais = numero.startsWith('55') ? numero : `55${numero}`
  return `https://wa.me/${comPais}${mensagem}`
}

export function telefoneFormatado(telefone: Talvez<string>): string {
  const n = String(telefone || '').replace(/\D/g, '')
  if (n.length === 11) return `(${n.slice(0, 2)}) ${n.slice(2, 7)}-${n.slice(7)}`
  if (n.length === 10) return `(${n.slice(0, 2)}) ${n.slice(2, 6)}-${n.slice(6)}`
  return telefone || ''
}

/** Cor do Bootstrap usada no selo de status (badge text-bg-<cor>). */
export type CorStatus = 'success' | 'warning' | 'info' | 'secondary' | 'danger'

export interface InfoStatus {
  texto: string
  cor: CorStatus
}

// `Record<StatusCarona, ...>`: o TypeScript avisa se faltar algum status
export const STATUS_CARONA: Record<StatusCarona, InfoStatus> = {
  ativa: { texto: 'Ativa', cor: 'success' },
  lotada: { texto: 'Lotada', cor: 'warning' },
  em_andamento: { texto: 'Em andamento', cor: 'info' },
  concluida: { texto: 'Concluída', cor: 'secondary' },
  cancelada: { texto: 'Cancelada', cor: 'danger' }
}

export const STATUS_PEDIDO: Record<StatusSolicitacao, InfoStatus> = {
  pendente: { texto: 'Aguardando motorista', cor: 'warning' },
  aceita: { texto: 'Vaga confirmada', cor: 'success' },
  recusada: { texto: 'Recusado', cor: 'danger' },
  cancelada: { texto: 'Cancelado', cor: 'secondary' },
  expirada: { texto: 'Expirado', cor: 'secondary' }
}

export function iniciais(nome: Talvez<string>): string {
  return String(nome || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join('')
}

// Endereco completo da foto de perfil. A API devolve "/api/fotos/<token>"; se o
// frontend estiver em outro dominio (VITE_API_URL), troca o comeco pelo da API.
export function urlFoto(caminho: Talvez<string>, base: string = import.meta.env?.VITE_API_URL || '/api'): string {
  if (!caminho) return ''
  return caminho.startsWith('/api/') ? `${base.replace(/\/$/, '')}${caminho.slice(4)}` : caminho
}

// Codigo de reserva do autenticador: "abcdefgh" -> "ABCD-EFGH" enquanto a pessoa digita
export function codigoReservaFormatado(texto: Talvez<string>): string {
  const limpo = String(texto || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8)
  return limpo.length > 4 ? `${limpo.slice(0, 4)}-${limpo.slice(4)}` : limpo
}

// Data de hoje no fuso do navegador, no formato AAAA-MM-DD (para <input type="date">)
export function hojeLocal(deslocamentoDias = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + deslocamentoDias)
  return `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}-${doisDigitos(d.getDate())}`
}

// ==========================================================
// Reputacao, preferencias e textos de confianca
// ==========================================================
export function nota(valor: Talvez<number>): string {
  return valor == null ? 'Novo' : Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

/** Texto com icone do Bootstrap Icons (ex.: preferencias do motorista). */
export interface ItemComIcone {
  texto: string
  icone: string
}

export const PREF_CONVERSA: Record<NivelConversa, ItemComIcone> = {
  quieto: { texto: 'Prefere silêncio', icone: 'bi-chat' },
  depende: { texto: 'Conversa se você quiser', icone: 'bi-chat-dots' },
  conversador: { texto: 'Adora conversar', icone: 'bi-chat-heart' }
}

export function listaPreferencias(p: Talvez<Preferencias>): ItemComIcone[] {
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
} as const

export type MotivoDenuncia = keyof typeof MOTIVOS_DENUNCIA

/** "direcao_perigosa" -> "Direção perigosa" (motivo desconhecido aparece como veio da API) */
export function textoMotivo(motivo: string): string {
  return motivo in MOTIVOS_DENUNCIA ? MOTIVOS_DENUNCIA[motivo as MotivoDenuncia] : motivo
}

// "2026-11-22T19:40" -> "22/11/2026"
export function dataCurtaNumerica(iso: Talvez<DataIso>): string {
  const d = paraData(iso)
  if (!d) return ''
  return `${doisDigitos(d.getDate())}/${doisDigitos(d.getMonth() + 1)}/${d.getFullYear()}`
}

export function dataHora(iso: Talvez<DataIso>): string {
  const d = paraData(iso)
  return d ? `${dataCurta(iso)} ${hora(iso)}` : ''
}

export function membroDesde(isoData: Talvez<string>): string {
  if (!isoData) return ''
  const [ano, mes] = isoData.split('-')
  const meses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
  return `${meses[Number(mes) - 1]}/${ano}`
}

export function porcentagem(fracao: Talvez<number>): string {
  return `${Math.round(Number(fracao || 0) * 100)}%`
}
