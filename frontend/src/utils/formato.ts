import type {
  DataIso, Energia, NivelConversa, Preferencias, StatusCarona, StatusPedidoCarona, StatusSolicitacao
} from '../types/api'

// ==========================================================
// Formatacao de datas, valores e status para exibicao
// ==========================================================
const DIAS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

/** Texto da API que pode faltar (campo opcional). */
type Talvez<T> = T | null | undefined

const doisDigitos = (n: number): string => String(n).padStart(2, '0')

export function paraData(iso: Talvez<DataIso>): Date | null {
  // A API envia "AAAA-MM-DDTHH:MM" no horario local
  if (!iso) return null
  // So a data ("2029-05-10", ex.: validade da CNH): o JavaScript leria como meia-noite em UTC,
  // que no horario de Brasilia ainda e o dia anterior. Monta a data no fuso local.
  const soData = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (soData) return new Date(Number(soData[1]), Number(soData[2]) - 1, Number(soData[3]))
  return new Date(iso)
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

/** Sempre em reais, inclusive zero ("R$ 0,00"): para contas e detalhamentos */
export function reais(valor: Talvez<number | string>): string {
  return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
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
export type CorStatus = 'success' | 'warning' | 'info' | 'secondary' | 'danger' | 'primary'

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

export const STATUS_FILA: Record<StatusPedidoCarona, InfoStatus> = {
  aberto: { texto: 'Na fila', cor: 'primary' },
  atendido: { texto: 'Conseguiu carona', cor: 'success' },
  expirado: { texto: 'Expirado', cor: 'secondary' },
  cancelado: { texto: 'Cancelado', cor: 'secondary' }
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

// ==========================================================
// Energia do carro e distancia (calculo do combustivel)
// ==========================================================
export interface InfoEnergia {
  texto: string
  icone: string
  unidade: 'L' | 'kWh'
  consumoMedio: number // usado quando o carro nao tem consumo cadastrado (igual ao servidor)
}

export const ENERGIAS: Record<Energia, InfoEnergia> = {
  flex: { texto: 'Flex (gasolina)', icone: 'bi-fuel-pump', unidade: 'L', consumoMedio: 12 },
  gasolina: { texto: 'Gasolina', icone: 'bi-fuel-pump', unidade: 'L', consumoMedio: 12 },
  etanol: { texto: 'Etanol', icone: 'bi-fuel-pump', unidade: 'L', consumoMedio: 8.5 },
  diesel: { texto: 'Diesel', icone: 'bi-fuel-pump-diesel', unidade: 'L', consumoMedio: 13 },
  hibrido: { texto: 'Híbrido (gasolina)', icone: 'bi-lightning-charge', unidade: 'L', consumoMedio: 18 },
  eletrico: { texto: 'Elétrico', icone: 'bi-ev-station', unidade: 'kWh', consumoMedio: 6.5 }
}

/** "km/l" ou "km/kWh" */
export function unidadeConsumo(energia: Energia): string {
  return `km/${ENERGIAS[energia].unidade === 'kWh' ? 'kWh' : 'l'}`
}

/** Numero no formato brasileiro com ate N casas: 6.2 -> "6,2" */
export function numeroBr(valor: Talvez<number>, casas = 2): string {
  return Number(valor || 0).toLocaleString('pt-BR', { maximumFractionDigits: casas })
}

/** 6200 -> "6,2 km (6.200 m)"; abaixo de 1 km so em metros */
export function distanciaTexto(metros: Talvez<number>): string {
  const m = Math.round(Number(metros || 0))
  if (m < 1000) return `${m.toLocaleString('pt-BR')} m`
  return `${numeroBr(m / 1000, 3)} km (${m.toLocaleString('pt-BR')} m)`
}

/**
 * Contagem regressiva ate um horario: "24:05" (menos de 1 h), "1 h 05 min" ou "" se ja passou.
 * `agora` e parametro para facilitar o teste.
 */
export function tempoRestante(iso: Talvez<DataIso>, agora: Date = new Date()): string {
  const fim = paraData(iso)
  if (!fim) return ''
  const segundos = Math.floor((fim.getTime() - agora.getTime()) / 1000)
  if (segundos <= 0) return ''
  const h = Math.floor(segundos / 3600)
  const min = Math.floor((segundos % 3600) / 60)
  if (h > 0) return `${h} h ${doisDigitos(min)} min`
  return `${doisDigitos(min)}:${doisDigitos(segundos % 60)}`
}
