import { afterEach, describe, expect, it } from 'vitest'

import type { ResumoAdmin } from '../types/api'
import { contador, ehAba, painel, SECOES } from './admin'

const RESUMO = {
  usuarios: { total: 8, ativos_30_dias: 2, verificados: 5, suspensos: 0, verificacoes_pendentes: 1, documentos_pendentes: 2 },
  caronas: { total: 11, por_status: {} },
  viagens: {
    concluidas: 4,
    em_andamento_agora: 1,
    passageiros_transportados: 6,
    taxa_ocupacao: 0.5,
    km_compartilhados: 48,
    co2_evitado_kg: 5.8,
    taxa_faltas: 0.18
  },
  confianca: { nota_media: 4.7, avaliacoes: 10, denuncias_abertas: 1, alertas_aguardando: 3, avaliacoes_baixas_abertas: 1, excluidos_automaticamente: 0 },
  demanda_sem_oferta: [],
  bairros_com_mais_oferta: []
} as unknown as ResumoAdmin

afterEach(() => {
  painel.resumo = null
})

describe('secoes do painel da administracao', () => {
  it('aceita so as secoes que existem no menu', () => {
    expect(ehAba('avaliacoes')).toBe(true)
    expect(ehAba('aovivo')).toBe(true)
    expect(ehAba('qualquer')).toBe(false)
    expect(ehAba(undefined)).toBe(false)
  })

  it('cada secao tem nome, icone e descricao, sem id repetido', () => {
    expect(new Set(SECOES.map((s) => s.id)).size).toBe(SECOES.length)
    SECOES.forEach((s) => {
      expect(s.texto).not.toBe('')
      expect(s.icone).toMatch(/^bi-/)
      expect(s.descricao.length).toBeGreaterThan(10)
    })
  })

  it('sem resumo carregado nenhum contador aparece', () => {
    expect(SECOES.every((s) => contador(s.id).n === 0)).toBe(true)
  })

  it('contadores do menu vem das pendencias do resumo', () => {
    painel.resumo = RESUMO
    expect(contador('aovivo')).toEqual({ n: 1, cor: 'success' })
    expect(contador('avaliacoes')).toEqual({ n: 1, cor: 'danger' })
    expect(contador('usuarios')).toEqual({ n: 1, cor: 'warning' })
    expect(contador('documentos')).toEqual({ n: 2, cor: 'warning' })
    expect(contador('denuncias')).toEqual({ n: 1, cor: 'danger' })
    expect(contador('alertas')).toEqual({ n: 3, cor: 'danger' })
    expect(contador('resumo').n).toBe(0)
    expect(contador('banco').n).toBe(0)
  })
})
