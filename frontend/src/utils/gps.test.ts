import { afterEach, describe, expect, it, vi } from 'vitest'

import { posicaoAtual } from './gps'

describe('localização opcional do celular', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('devolve null sem GPS no navegador', async () => {
    vi.stubGlobal('navigator', {})
    expect(await posicaoAtual()).toBeNull()
  })

  it('arredonda a posição para 6 casas', async () => {
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: (ok: (p: { coords: { latitude: number; longitude: number } }) => void) =>
          ok({ coords: { latitude: -20.36170123456, longitude: -40.30750987654 } })
      }
    })
    expect(await posicaoAtual()).toEqual({ lat: -20.361701, lng: -40.30751 })
  })

  it('devolve null se o aluno não permitir', async () => {
    vi.stubGlobal('navigator', {
      geolocation: { getCurrentPosition: (_ok: unknown, erro: () => void) => erro() }
    })
    expect(await posicaoAtual()).toBeNull()
  })
})
