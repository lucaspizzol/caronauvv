// ==========================================================
// Localizacao do celular (opcional). Nunca falha: se o aluno nao
// permitir, o navegador nao tiver GPS ou demorar, devolve null e a
// acao (embarque/desembarque) segue sem o local.
// ==========================================================
export interface Posicao {
  lat: number
  lng: number
}

export function posicaoAtual(tempoMs = 5000): Promise<Posicao | null> {
  return new Promise((resolve) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      resolve(null)
      return
    }
    const desistir = setTimeout(() => resolve(null), tempoMs + 500)
    navigator.geolocation.getCurrentPosition(
      (p) => {
        clearTimeout(desistir)
        resolve({ lat: Number(p.coords.latitude.toFixed(6)), lng: Number(p.coords.longitude.toFixed(6)) })
      },
      () => {
        clearTimeout(desistir)
        resolve(null)
      },
      { enableHighAccuracy: true, timeout: tempoMs, maximumAge: 30000 }
    )
  })
}
