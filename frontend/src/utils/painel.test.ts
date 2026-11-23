import { describe, expect, it } from 'vitest'

import type { AcaoAdmin, TipoAcaoAdmin } from '../types/api'
import { ACOES, agruparPorDia, autorDa, diaMes, escalaEixo } from './painel'

function acao(id: number, criado_em: string, extra: Partial<AcaoAdmin> = {}): AcaoAdmin {
  return { id, acao: 'aprovar_selo', admin: { id: 1, nome: 'Admin' }, alvo: null, detalhe: null, criado_em, ...extra }
}

describe('eixo do grafico de caronas', () => {
  it('usa numeros redondos e o topo cobre o maior valor', () => {
    expect(escalaEixo(3)).toEqual({ topo: 4, marcas: [0, 1, 2, 3, 4] })
    expect(escalaEixo(7)).toEqual({ topo: 8, marcas: [0, 2, 4, 6, 8] })
    expect(escalaEixo(18)).toEqual({ topo: 20, marcas: [0, 5, 10, 15, 20] })
    expect(escalaEixo(130).topo).toBeGreaterThanOrEqual(130)
  })

  it('nunca usa passo quebrado (meia carona nao existe)', () => {
    for (const maximo of [1, 2, 5, 9, 11, 33, 47]) {
      expect(escalaEixo(maximo).marcas.every(Number.isInteger)).toBe(true)
    }
  })

  it('sem caronas ainda desenha um eixo', () => {
    expect(escalaEixo(0)).toEqual({ topo: 4, marcas: [0, 1, 2, 3, 4] })
  })

  it('formata o dia do eixo', () => {
    expect(diaMes('2026-11-05')).toBe('05/11')
  })
})

describe('historico da administracao', () => {
  it('toda acao do backend tem frase, icone e nome no filtro', () => {
    const tipos: TipoAcaoAdmin[] = [
      'aprovar_selo', 'recusar_selo', 'suspender', 'reativar', 'remover_foto', 'resetar_2fa', 'aprovar_documento',
      'recusar_documento', 'analisar_denuncia', 'encerrar_denuncia', 'resolver_alerta', 'alterar_regras',
      'exportar_dados', 'exclusao_automatica'
    ]
    expect(Object.keys(ACOES).sort()).toEqual([...tipos].sort())
    tipos.forEach((t) => expect(ACOES[t].icone).toMatch(/^bi-/))
  })

  it('exclusao automatica aparece como acao do sistema', () => {
    expect(autorDa(acao(1, '2026-11-23T10:00', { admin: null, acao: 'exclusao_automatica' }))).toBe('Sistema (regra automática)')
    expect(autorDa(acao(2, '2026-11-23T10:00'))).toBe('Admin')
  })

  it('agrupa por dia: hoje, ontem e depois a data', () => {
    const agora = new Date(2026, 10, 23, 12, 0)
    const grupos = agruparPorDia(
      [acao(4, '2026-11-23T11:00'), acao(3, '2026-11-23T08:00'), acao(2, '2026-11-22T20:00'), acao(1, '2026-11-20T09:00')],
      agora
    )
    expect(grupos.map((g) => g.rotulo)).toEqual(['Hoje', 'Ontem', 'sex, 20/11'])
    expect(grupos[0]!.acoes.map((a) => a.id)).toEqual([4, 3])
  })
})
