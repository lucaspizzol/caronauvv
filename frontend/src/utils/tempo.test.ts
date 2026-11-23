import { describe, expect, it } from 'vitest'

import { tempoRestante } from './formato'

describe('contagem regressiva do pedido (30 min para o motorista responder)', () => {
  const agora = new Date(2026, 10, 23, 18, 0, 0)

  it('mostra minutos e segundos abaixo de 1 hora', () => {
    expect(tempoRestante('2026-11-23T18:30', agora)).toBe('30:00')
    expect(tempoRestante('2026-11-23T18:01', new Date(2026, 10, 23, 18, 0, 15))).toBe('00:45')
  })

  it('mostra horas e minutos acima de 1 hora', () => {
    expect(tempoRestante('2026-11-23T19:05', agora)).toBe('1 h 05 min')
  })

  it('fica vazio quando o prazo passou ou não existe', () => {
    expect(tempoRestante('2026-11-23T17:59', agora)).toBe('')
    expect(tempoRestante(null, agora)).toBe('')
  })
})
