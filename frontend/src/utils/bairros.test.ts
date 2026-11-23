import { describe, expect, it } from 'vitest'

import { distanciaAteUvvKm, haversineKm, normalizar, pareceEndereco, UVV } from './bairros'

describe('bairros', () => {
  it('normaliza ignorando acento, maiúsculas e espaços', () => {
    expect(normalizar('  Itapuã ')).toBe('itapua')
    expect(normalizar('PRAIA   da  Costa')).toBe('praia da costa')
    expect(normalizar(null)).toBe('')
  })

  it('reconhece quando digitaram uma rua no campo Bairro', () => {
    expect(pareceEndereco('rua itape')).toBe(true)
    expect(pareceEndereco('Av. Hugo Musso')).toBe(true)
    expect(pareceEndereco('Avenida Champagnat')).toBe(true)
    expect(pareceEndereco('Itapuã')).toBe(false)
    expect(pareceEndereco('Ruas Altas')).toBe(false) // bairro que comeca com "Rua..." sem ser endereco
  })
})

describe('distância até a UVV', () => {
  it('calcula a linha reta pela fórmula de Haversine', () => {
    // Itapua (-20.3523, -40.2897) fica a ~2 km da UVV
    expect(haversineKm(-20.3523, -40.2897, UVV[0], UVV[1])).toBeCloseTo(2.1, 1)
    expect(haversineKm(UVV[0], UVV[1], UVV[0], UVV[1])).toBe(0)
  })

  it('estima o trajeto de carro com o fator de rota (mínimo 1 km)', () => {
    expect(distanciaAteUvvKm(-20.3523, -40.2897)).toBeCloseTo(2.9, 1)
    expect(distanciaAteUvvKm(UVV[0], UVV[1])).toBe(1)
  })
})
