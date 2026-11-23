import type { AcaoAdmin, TipoAcaoAdmin } from '../types/api'
import { dataCurta, paraData } from './formato'

// ==========================================================
// Regras puras do painel da administracao (testadas no Vitest):
// escala do grafico, frases e agrupamento do historico.
// ==========================================================

/** Eixo do grafico com numeros redondos: 0, 1, 2, 3, 4 ou 0, 5, 10, 15, 20... */
export function escalaEixo(maximo: number, divisoes = 4): { topo: number; marcas: number[] } {
  if (maximo <= 0) return { topo: divisoes, marcas: Array.from({ length: divisoes + 1 }, (_, i) => i) }
  const bruto = maximo / divisoes
  const potencia = 10 ** Math.floor(Math.log10(bruto))
  const passo = [1, 2, 5, 10].map((m) => m * potencia).find((p) => p >= bruto && Number.isInteger(p)) ?? Math.ceil(bruto)
  const topo = passo * divisoes
  return { topo, marcas: Array.from({ length: divisoes + 1 }, (_, i) => i * passo) }
}

interface DescricaoAcao {
  verbo: string // completa "Fulano ___ Ciclano"
  icone: string
  cor: 'verde' | 'vermelho' | 'amarelo' | 'azul'
  filtro: string // nome no filtro do historico
}

export const ACOES: Record<TipoAcaoAdmin, DescricaoAcao> = {
  aprovar_selo: { verbo: 'aprovou o selo de verificado de', icone: 'bi-patch-check-fill', cor: 'verde', filtro: 'Selo aprovado' },
  recusar_selo: { verbo: 'recusou o selo de verificado de', icone: 'bi-patch-exclamation', cor: 'amarelo', filtro: 'Selo recusado' },
  aprovar_documento: { verbo: 'aprovou um documento de', icone: 'bi-person-vcard-fill', cor: 'verde', filtro: 'Documento aprovado' },
  recusar_documento: { verbo: 'recusou um documento de', icone: 'bi-person-vcard', cor: 'amarelo', filtro: 'Documento recusado' },
  suspender: { verbo: 'suspendeu a conta de', icone: 'bi-person-dash-fill', cor: 'vermelho', filtro: 'Conta suspensa' },
  reativar: { verbo: 'reativou a conta de', icone: 'bi-person-check-fill', cor: 'verde', filtro: 'Conta reativada' },
  exclusao_automatica: { verbo: 'excluiu do aplicativo', icone: 'bi-person-x-fill', cor: 'vermelho', filtro: 'Exclusão automática' },
  remover_foto: { verbo: 'removeu a foto de perfil de', icone: 'bi-image', cor: 'amarelo', filtro: 'Foto removida' },
  resetar_2fa: { verbo: 'desligou a verificação em duas etapas de', icone: 'bi-shield-slash', cor: 'amarelo', filtro: 'Duas etapas desligada' },
  analisar_denuncia: { verbo: 'começou a analisar uma denúncia contra', icone: 'bi-flag', cor: 'amarelo', filtro: 'Denúncia em análise' },
  encerrar_denuncia: { verbo: 'encerrou uma denúncia contra', icone: 'bi-flag-fill', cor: 'azul', filtro: 'Denúncia encerrada' },
  resolver_alerta: { verbo: 'resolveu um alerta de', icone: 'bi-shield-check', cor: 'azul', filtro: 'Alerta resolvido' },
  alterar_regras: { verbo: 'alterou as regras do aplicativo', icone: 'bi-sliders', cor: 'azul', filtro: 'Regras alteradas' },
  exportar_dados: { verbo: 'exportou uma planilha', icone: 'bi-download', cor: 'azul', filtro: 'Dados exportados' }
}

/** Quem fez: o admin ou, na exclusao automatica, o proprio sistema. */
export function autorDa(acao: AcaoAdmin): string {
  return acao.admin?.nome ?? 'Sistema (regra automática)'
}

export interface GrupoDoDia {
  rotulo: string // "Hoje", "Ontem", "sex, 20/11"
  acoes: AcaoAdmin[]
}

/** Junta as acoes (ja da mais nova para a mais antiga) por dia, para a linha do tempo. */
export function agruparPorDia(acoes: AcaoAdmin[], agora: Date = new Date()): GrupoDoDia[] {
  const ontem = new Date(agora)
  ontem.setDate(agora.getDate() - 1)
  const grupos: GrupoDoDia[] = []
  for (const acao of acoes) {
    const d = paraData(acao.criado_em)
    if (!d) continue
    const rotulo =
      d.toDateString() === agora.toDateString() ? 'Hoje' : d.toDateString() === ontem.toDateString() ? 'Ontem' : dataCurta(acao.criado_em)
    const ultimo = grupos[grupos.length - 1]
    if (ultimo && ultimo.rotulo === rotulo) ultimo.acoes.push(acao)
    else grupos.push({ rotulo, acoes: [acao] })
  }
  return grupos
}

/** "2026-11-23" -> "23/11" (eixo do grafico). */
export function diaMes(isoData: string): string {
  const [, mes, dia] = isoData.split('-')
  return `${dia}/${mes}`
}
