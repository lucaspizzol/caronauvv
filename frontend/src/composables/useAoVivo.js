import { onBeforeUnmount, onMounted, ref } from 'vue'

// ==========================================================
// Atualizacao automatica ("ao vivo") das telas.
// Chama `atualizar()` a cada `intervalo` ms enquanto a tela estiver aberta,
// sem sobrepor requisicoes e pausando quando a aba fica escondida.
// Assim, com motorista e passageiro em duas janelas, um ve a acao do
// outro em poucos segundos, sem recarregar a pagina.
// ==========================================================
export const INTERVALO_PADRAO = 5000

export function useAoVivo(atualizar, intervalo = INTERVALO_PADRAO) {
  const atualizadoEm = ref(null)
  let timer = null
  let ocupado = false

  async function tick() {
    if (ocupado || document.visibilityState === 'hidden') return
    ocupado = true
    try {
      await atualizar()
      atualizadoEm.value = new Date()
    } catch {
      /* falha silenciosa: a proxima rodada tenta de novo */
    } finally {
      ocupado = false
    }
  }

  function aoVoltarParaAba() {
    if (document.visibilityState === 'visible') tick()
  }

  onMounted(() => {
    atualizadoEm.value = new Date()
    timer = setInterval(tick, intervalo)
    document.addEventListener('visibilitychange', aoVoltarParaAba)
  })

  onBeforeUnmount(() => {
    clearInterval(timer)
    document.removeEventListener('visibilitychange', aoVoltarParaAba)
  })

  return { atualizadoEm, atualizarAgora: tick }
}
