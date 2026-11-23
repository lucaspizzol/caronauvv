<template>
  <div class="mapa-trilha-caixa">
    <div ref="alvo" class="mapa-trilha" role="img" :aria-label="descricao" :style="{ height: `${altura}px` }"></div>
    <p class="small text-secondary mb-0 mt-1">
      Mapa © colaboradores do <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>
    </p>
  </div>
</template>

<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import type { CircleMarker, Map as MapaLeaflet, Polyline } from 'leaflet'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

// ==========================================================
// Mapa da viagem (Leaflet + mapa do OpenStreetMap, sem chave):
// linha azul = trilha GPS; pontos verdes/vermelhos = onde cada
// passageiro entrou/saiu. O Leaflet so carrega quando o mapa aparece.
// ==========================================================
export interface MarcaMapa {
  lat: number
  lng: number
  texto: string
  tipo: 'entrada' | 'saida' | 'carro'
}

const props = withDefaults(
  defineProps<{ trilha: [number, number][]; marcas?: MarcaMapa[]; descricao?: string; altura?: number }>(),
  {
    marcas: () => [],
    descricao: 'Mapa com o trajeto da viagem',
    altura: 260
  }
)

const CORES: Record<MarcaMapa['tipo'], string> = { entrada: '#198754', saida: '#dc3545', carro: '#163f82' }
const UVV: [number, number] = [-20.3617, -40.3075]

const alvo = ref<HTMLDivElement | null>(null)
let mapa: MapaLeaflet | null = null
let camadas: (Polyline | CircleMarker)[] = []

async function desenhar(): Promise<void> {
  if (!alvo.value) return
  const L = await import('leaflet')
  if (!mapa) {
    mapa = L.map(alvo.value, { scrollWheelZoom: false }).setView(UVV, 14)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapa)
  }
  camadas.forEach((c) => c.remove())
  camadas = []
  const pontos: [number, number][] = [...props.trilha, ...props.marcas.map((m): [number, number] => [m.lat, m.lng])]
  if (props.trilha.length > 1) {
    camadas.push(L.polyline(props.trilha, { color: '#163f82', weight: 5, opacity: 0.8 }).addTo(mapa))
  }
  for (const m of props.marcas) {
    camadas.push(
      L.circleMarker([m.lat, m.lng], { radius: 8, color: '#fff', weight: 2, fillColor: CORES[m.tipo], fillOpacity: 1 })
        .bindTooltip(m.texto)
        .addTo(mapa)
    )
  }
  if (pontos.length > 1) mapa.fitBounds(L.latLngBounds(pontos), { padding: [24, 24], maxZoom: 16 })
  else if (pontos.length === 1) mapa.setView(pontos[0], 16)
}

onMounted(() => void desenhar())
watch(() => [props.trilha, props.marcas], () => void desenhar(), { deep: true })
onBeforeUnmount(() => {
  mapa?.remove()
  mapa = null
})
</script>

<style scoped>
.mapa-trilha {
  border-radius: var(--bs-border-radius-lg);
  border: 1px solid var(--bs-border-color);
  z-index: 0;
}
</style>
