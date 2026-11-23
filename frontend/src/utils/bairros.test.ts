import { describe, expect, it } from 'vitest'

import { BAIRROS, DISTANCIA_ATE_UVV_KM, distanciaEstimada } from './bairros'

describe('distância do bairro até a UVV', () => {
  it('estima a distância dos bairros da lista', () => {
    expect(distanciaEstimada('Itapuã')).toBe(6.2)
    expect(distanciaEstimada('Jardim Camburi')).toBe(17)
  })

  it('ignora maiúsculas, acentos e espaços nas pontas', () => {
    expect(distanciaEstimada('  itapua ')).toBe(6.2)
    expect(distanciaEstimada('GLORIA')).toBe(3)
  })

  it('devolve null para bairro fora da lista ou vazio', () => {
    expect(distanciaEstimada('Bairro Inventado')).toBeNull()
    expect(distanciaEstimada('')).toBeNull()
    expect(distanciaEstimada(null)).toBeNull()
  })

  it('tem distância para todo bairro sugerido no cadastro', () => {
    expect(BAIRROS.filter((b) => DISTANCIA_ATE_UVV_KM[b] === undefined)).toEqual([])
  })
})
