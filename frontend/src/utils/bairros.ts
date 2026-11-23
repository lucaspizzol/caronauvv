// ==========================================================
// Bairros e distancia ate a UVV.
// A lista completa dos bairros da Grande Vitoria fica no servidor
// (GET /api/lugares/bairros?q=), que tambem calcula a distancia real
// de carro (OSRM) com plano B. Aqui ficam as regras usadas na tela.
// ==========================================================

/** Campus Boa Vista da UVV, em Vila Velha (mesma coordenada do servidor). */
export const UVV: readonly [number, number] = [-20.3617, -40.3075]

/** As ruas nao sao linha reta: na Grande Vitoria o trajeto de carro e ~35% maior. */
export const FATOR_ROTA = 1.35

/** "  Itapuã " -> "itapua" (sem acento, minusculo, espacos simples) */
export function normalizar(texto: string | null | undefined): string {
  return (texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().split(/\s+/).filter(Boolean).join(' ')
}

/** O aluno digitou um endereco ("Rua Itapemirim", "Av. Hugo Musso") no campo Bairro? */
export function pareceEndereco(texto: string | null | undefined): boolean {
  return /^(rua|r\.|av\.?|avenida|travessa|tv\.|rodovia|rod\.|estrada|alameda|al\.|praca)(\s|$)/.test(normalizar(texto))
}

/** Distancia em linha reta entre dois pontos (km), formula de Haversine. */
export function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const rad = (g: number) => (g * Math.PI) / 180
  const dLat = rad(lat2 - lat1)
  const dLng = rad(lng2 - lng1)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(a))
}

/** Estimativa de carro ate a UVV: linha reta x fator de rota, 1 casa, minimo 1 km (igual ao servidor). */
export function distanciaAteUvvKm(lat: number, lng: number): number {
  return Math.max(1, Math.round(haversineKm(lat, lng, UVV[0], UVV[1]) * FATOR_ROTA * 10) / 10)
}
