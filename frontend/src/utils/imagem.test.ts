import { describe, expect, it } from 'vitest'

import { recorteCentral, validarArquivoDeFoto } from './imagem'

describe('foto de perfil', () => {
  it('recorta o maior quadrado do meio da imagem', () => {
    expect(recorteCentral(4000, 3000)).toEqual({ x: 500, y: 0, lado: 3000 }) // deitada
    expect(recorteCentral(3000, 4000)).toEqual({ x: 0, y: 500, lado: 3000 }) // em pé
    expect(recorteCentral(800, 800)).toEqual({ x: 0, y: 0, lado: 800 }) // já quadrada
    expect(recorteCentral(301, 200)).toEqual({ x: 50, y: 0, lado: 200 }) // sobra ímpar
  })

  it('só aceita JPG, PNG ou WebP', () => {
    expect(validarArquivoDeFoto({ type: 'image/jpeg', size: 1000 })).toBe('')
    expect(validarArquivoDeFoto({ type: 'image/webp', size: 1000 })).toBe('')
    expect(validarArquivoDeFoto({ type: 'application/pdf', size: 1000 })).toBe('Use uma foto em JPG, PNG ou WebP.')
    expect(validarArquivoDeFoto({ type: 'image/gif', size: 1000 })).toBe('Use uma foto em JPG, PNG ou WebP.')
    expect(validarArquivoDeFoto(null)).toBe('Escolha uma foto.')
  })

  it('recusa arquivo grande demais antes de tentar abrir', () => {
    expect(validarArquivoDeFoto({ type: 'image/png', size: 16 * 1024 * 1024 })).toBe('A foto passou de 15 MB.')
    expect(validarArquivoDeFoto({ type: 'image/png', size: 15 * 1024 * 1024 })).toBe('')
  })
})
