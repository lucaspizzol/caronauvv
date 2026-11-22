import { describe, expect, it } from 'vitest'

import {
  dinheiro, hora, iniciais, linkWhatsApp, listaPreferencias, membroDesde, nota, porcentagem, telefoneFormatado
} from './formato'

describe('formatação para a tela', () => {
  it('mostra valor em reais e "Grátis" para zero', () => {
    expect(dinheiro(0)).toBe('Grátis')
    expect(dinheiro(1.5).replace(/\s/g, ' ')).toBe('R$ 1,50')
  })

  it('formata hora e telefone', () => {
    expect(hora('2026-11-23T18:30')).toBe('18:30')
    expect(telefoneFormatado('27999990000')).toBe('(27) 99999-0000')
  })

  it('gera iniciais do nome', () => {
    expect(iniciais('Kauã Araujo')).toBe('KA')
    expect(iniciais('')).toBe('?')
  })

  it('monta link do WhatsApp com e sem número', () => {
    expect(linkWhatsApp('(27) 99999-0000', 'Oi')).toBe('https://wa.me/5527999990000?text=Oi')
    expect(linkWhatsApp('', 'Oi')).toBe('https://wa.me/?text=Oi')
  })
})

describe('reputação e preferências', () => {
  it('mostra "Novo" para quem ainda não tem nota', () => {
    expect(nota(null)).toBe('Novo')
    expect(nota(4.85)).toBe('4,9')
  })

  it('traduz as preferências de viagem', () => {
    const textos = listaPreferencias({ conversa: 'quieto', musica: false, animais: true, fumar: false }).map((p) => p.texto)
    expect(textos).toEqual(['Prefere silêncio', 'Sem música', 'Aceita animais', 'Não fuma no carro'])
  })

  it('formata membro desde e porcentagem', () => {
    expect(membroDesde('2026-03-10')).toBe('mar/2026')
    expect(porcentagem(0.125)).toBe('13%')
  })
})
