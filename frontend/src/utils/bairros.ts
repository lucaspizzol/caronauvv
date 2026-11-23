// Sugestoes para o campo de bairro (o aluno pode digitar outro)
export const BAIRROS: readonly string[] = [
  'Boa Vista', 'Centro de Vila Velha', 'Coqueiral de Itaparica', 'Cobilândia', 'Glória', 'Ibes',
  'Itapuã', 'Jardim Camburi', 'Jardim da Penha', 'Jockey de Itaparica', 'Praia da Costa',
  'Praia de Itaparica', 'Santa Inês', 'Soteco', 'Divino Espírito Santo', 'Cariacica', 'Serra', 'Vitória - Centro'
]

// Distancia aproximada de carro entre o bairro e a UVV (campus Boa Vista), em km.
// So para preencher o campo "Distancia" ao oferecer carona: o motorista pode ajustar.
export const DISTANCIA_ATE_UVV_KM: Readonly<Record<string, number>> = {
  'Boa Vista': 1.5,
  'Centro de Vila Velha': 4,
  'Coqueiral de Itaparica': 7,
  'Cobilândia': 5,
  'Glória': 3,
  'Ibes': 3.5,
  'Itapuã': 6.2,
  'Jardim Camburi': 17,
  'Jardim da Penha': 14,
  'Jockey de Itaparica': 6.5,
  'Praia da Costa': 7.5,
  'Praia de Itaparica': 5,
  'Santa Inês': 4.5,
  'Soteco': 3,
  'Divino Espírito Santo': 3.5,
  'Cariacica': 12,
  'Serra': 28,
  'Vitória - Centro': 10
}

/** Distancia estimada do bairro ate a UVV (ignora maiusculas e acentos), ou null se o bairro nao estiver na lista. */
export function distanciaEstimada(bairro: string | null | undefined): number | null {
  const simples = (texto: string) => texto.normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase()
  const procurado = simples(bairro || '')
  if (!procurado) return null
  const achado = Object.keys(DISTANCIA_ATE_UVV_KM).find((b) => simples(b) === procurado)
  return achado ? DISTANCIA_ATE_UVV_KM[achado] : null
}
