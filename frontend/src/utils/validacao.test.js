import { describe, expect, it } from 'vitest'

import { errosDoServidor, regras, validar } from './validacao'

describe('regras de validação dos formulários', () => {
  it('exige campo preenchido', () => {
    expect(regras.obrigatorio('')).toBe('Campo obrigatório.')
    expect(regras.obrigatorio('   ')).toBe('Campo obrigatório.')
    expect(regras.obrigatorio('Ana')).toBeNull()
  })

  it('só aceita e-mail institucional da UVV', () => {
    expect(regras.emailUvv('ana@uvv.br')).toBeNull()
    expect(regras.emailUvv('ana@aluno.uvv.br')).toBeNull()
    expect(regras.emailUvv('ana@gmail.com')).toMatch(/institucional/)
    expect(regras.emailUvv('ana@fakeuvv.br')).toMatch(/institucional/)
  })

  it('valida telefone com DDD', () => {
    expect(regras.telefone('(27) 99999-0000')).toBeNull()
    expect(regras.telefone('99999-0000')).toMatch(/DDD/)
  })

  it('valida matrícula, código e PIN', () => {
    expect(regras.matricula('202416377')).toBeNull()
    expect(regras.matricula('12a')).not.toBeNull()
    expect(regras.codigo('123456')).toBeNull()
    expect(regras.codigo('12345')).toBe('O código tem 6 números.')
    expect(regras.pin('4821')).toBeNull()
    expect(regras.pin('48')).toBe('O PIN tem 4 números.')
  })

  it('aceita placa antiga e Mercosul', () => {
    expect(regras.placa('KAU-2B34')).toBeNull()
    expect(regras.placa('abc1234')).toBeNull()
    expect(regras.placa('AB12345')).not.toBeNull()
  })
})

describe('validar()', () => {
  it('devolve só o primeiro erro de cada campo', () => {
    const erros = validar({ email: '', senha: '123' }, {
      email: [regras.obrigatorio, regras.email],
      senha: [regras.obrigatorio, regras.senha]
    })
    expect(erros).toEqual({
      email: 'Campo obrigatório.',
      senha: 'A senha precisa ter pelo menos 6 caracteres.'
    })
  })

  it('permite regra que compara campos (confirmar senha)', () => {
    const iguais = (v, d) => (v === d.senha ? null : 'As senhas não conferem.')
    expect(validar({ senha: 'abcdef', confirmar: 'abcdeg' }, { confirmar: [iguais] })).toEqual({
      confirmar: 'As senhas não conferem.'
    })
  })
})

describe('errosDoServidor()', () => {
  it('usa os erros por campo da API só para campos do formulário', () => {
    const erroApi = { campos: { email: 'Use seu e-mail institucional.', geral: 'x' } }
    expect(errosDoServidor(erroApi, ['email', 'senha'])).toEqual({ email: 'Use seu e-mail institucional.' })
    expect(errosDoServidor({}, ['email'])).toEqual({})
  })
})
