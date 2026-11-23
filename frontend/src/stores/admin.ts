import { reactive } from 'vue'

import api from '../services/api'
import type { ResumoAdmin } from '../types/api'

// ==========================================================
// Numeros do painel da administracao, compartilhados entre o menu
// lateral (contadores de pendencias) e a tela do painel.
// Um unico lugar busca o resumo, entao o menu e a tela nunca divergem.
// ==========================================================
export const painel = reactive<{ resumo: ResumoAdmin | null }>({ resumo: null })

export async function carregarResumo(): Promise<void> {
  const { data } = await api.get<{ resumo: ResumoAdmin }>('/admin/resumo')
  painel.resumo = data.resumo
}

/** Secoes do painel: o menu lateral e a tela usam a mesma lista. */
export type IdAba = 'resumo' | 'aovivo' | 'avaliacoes' | 'usuarios' | 'documentos' | 'denuncias' | 'alertas' | 'regras' | 'banco'

export interface SecaoAdmin {
  id: IdAba
  texto: string
  icone: string
  descricao: string
  grupo: 'Acompanhar' | 'Moderar' | 'Sistema'
}

export const SECOES: SecaoAdmin[] = [
  { id: 'resumo', texto: 'Visão geral', icone: 'bi-grid-1x2', descricao: 'Os números do aplicativo e o que precisa da sua atenção.', grupo: 'Acompanhar' },
  { id: 'aovivo', texto: 'Ao vivo', icone: 'bi-broadcast', descricao: 'Viagens acontecendo agora (com o GPS no mapa), saindo nas próximas 3 horas e concluídas nas últimas 3 horas.', grupo: 'Acompanhar' },
  { id: 'avaliacoes', texto: 'Avaliações', icone: 'bi-star-half', descricao: 'Todas as notas na hora, inclusive as que o aluno ainda não vê (avaliação às cegas), alunos em risco e contas excluídas.', grupo: 'Acompanhar' },
  { id: 'usuarios', texto: 'Usuários', icone: 'bi-people', descricao: 'Contas, selo de verificado e suspensões.', grupo: 'Moderar' },
  { id: 'documentos', texto: 'Documentos', icone: 'bi-person-vcard', descricao: 'Identidade e CNH enviadas para conferência.', grupo: 'Moderar' },
  { id: 'denuncias', texto: 'Denúncias', icone: 'bi-flag', descricao: 'Denúncias feitas pelos alunos.', grupo: 'Moderar' },
  { id: 'alertas', texto: 'Alertas', icone: 'bi-shield-exclamation', descricao: 'Botão de pânico, notas baixas e exclusões automáticas.', grupo: 'Moderar' },
  { id: 'regras', texto: 'Regras', icone: 'bi-sliders', descricao: 'Limites do aplicativo, como a nota mínima e o tempo de resposta.', grupo: 'Sistema' },
  { id: 'banco', texto: 'Banco de dados', icone: 'bi-database', descricao: 'Tabelas, quantidade de linhas e o diagrama do banco.', grupo: 'Sistema' }
]

export function ehAba(valor: unknown): valor is IdAba {
  return SECOES.some((s) => s.id === valor)
}

/** Contador mostrado ao lado de cada secao (0 = sem contador). */
export function contador(id: IdAba): { n: number; cor: 'danger' | 'warning' | 'success' } {
  const r = painel.resumo
  if (!r) return { n: 0, cor: 'danger' }
  switch (id) {
    case 'aovivo':
      return { n: r.viagens.em_andamento_agora, cor: 'success' }
    case 'avaliacoes':
      return { n: r.confianca.avaliacoes_baixas_abertas, cor: 'danger' }
    case 'usuarios':
      return { n: r.usuarios.verificacoes_pendentes, cor: 'warning' }
    case 'documentos':
      return { n: r.usuarios.documentos_pendentes, cor: 'warning' }
    case 'denuncias':
      return { n: r.confianca.denuncias_abertas, cor: 'danger' }
    case 'alertas':
      return { n: r.confianca.alertas_aguardando, cor: 'danger' }
    default:
      return { n: 0, cor: 'danger' }
  }
}
