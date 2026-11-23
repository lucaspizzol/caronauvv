import { describe, expect, it } from 'vitest'

import { dataCurtaNumerica, distanciaTexto, ENERGIAS, numeroBr, reais, unidadeConsumo } from './formato'
import { medidasReduzidas } from './imagem'

// O texto de dinheiro usa espaco especial entre "R$" e o numero: troca por espaco comum para comparar
const semEspacoEspecial = (texto: string) => texto.replace(/\s/g, ' ')

describe('cálculo do combustível na tela', () => {
  it('mostra a distância em km e em metros', () => {
    expect(distanciaTexto(6200)).toBe('6,2 km (6.200 m)')
    expect(distanciaTexto(17_045)).toBe('17,045 km (17.045 m)')
    expect(distanciaTexto(850)).toBe('850 m')
  })

  it('usa km/l para combustível e km/kWh para o elétrico', () => {
    expect(unidadeConsumo('flex')).toBe('km/l')
    expect(unidadeConsumo('hibrido')).toBe('km/l')
    expect(unidadeConsumo('eletrico')).toBe('km/kWh')
    expect(ENERGIAS.eletrico.unidade).toBe('kWh')
  })

  it('tem a mesma média de consumo que o servidor (caronas/combustivel.py)', () => {
    expect(Object.fromEntries(Object.entries(ENERGIAS).map(([e, info]) => [e, info.consumoMedio]))).toEqual({
      flex: 12, gasolina: 12, etanol: 8.5, diesel: 13, hibrido: 18, eletrico: 6.5
    })
  })

  it('formata números e reais no padrão brasileiro', () => {
    expect(numeroBr(0.496, 3)).toBe('0,496')
    expect(numeroBr(12.5, 1)).toBe('12,5')
    expect(semEspacoEspecial(reais(0))).toBe('R$ 0,00') // adicional zero aparece como R$ 0,00, não "Grátis"
    expect(semEspacoEspecial(reais(0.78))).toBe('R$ 0,78')
  })
})

describe('foto do documento', () => {
  it('reduz mantendo a proporção, sem recortar', () => {
    expect(medidasReduzidas(4000, 3000, 1600)).toEqual({ largura: 1600, altura: 1200 })
    expect(medidasReduzidas(3000, 4000, 1600)).toEqual({ largura: 1200, altura: 1600 })
  })

  it('não aumenta imagem pequena', () => {
    expect(medidasReduzidas(800, 600, 1600)).toEqual({ largura: 800, altura: 600 })
  })
})

describe('datas sem hora (validade da CNH)', () => {
  it('não volta um dia por causa do fuso horário', () => {
    expect(dataCurtaNumerica('2029-05-10')).toBe('10/05/2029')
    expect(dataCurtaNumerica('2026-01-01')).toBe('01/01/2026')
  })
})
