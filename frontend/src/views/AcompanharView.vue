<template>
  <!-- Pagina PUBLICA: o "link da familia". Abre sem login. -->
  <div class="tela-login py-4">
    <div class="container" style="max-width: 620px">
      <div class="text-center mb-3">
        <div class="marca h3 mb-0"><i class="bi bi-car-front-fill me-1"></i>Carona<span>UVV</span></div>
        <div class="text-white-50 small">Acompanhamento de viagem</div>
      </div>

      <div class="card p-4">
        <div v-if="carregando" class="text-center py-4"><span class="spinner-border text-primary"></span></div>

        <div v-else-if="erro" class="text-center py-3">
          <i class="bi bi-flag-fill display-6 text-secondary"></i>
          <p class="fw-semibold mt-2 mb-0">{{ erro }}</p>
        </div>

        <template v-else-if="v">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div>
              <div class="small text-secondary">{{ v.compartilhado_por }} compartilhou esta viagem com você</div>
              <h1 class="h5 fw-bold mb-0">{{ v.status === 'em_andamento' ? 'Viagem em andamento' : 'Viagem agendada' }}</h1>
            </div>
            <StatusBadge :status="v.status" />
          </div>
          <p class="mb-2"><AoVivo :atualizado-em="atualizadoEm" /></p>

          <div class="rota my-3">
            <div class="ponto mb-2">
              <div class="small text-secondary">{{ v.sentido === 'ida' ? 'Saída' : 'Saída da UVV' }} · {{ dataHora(v.data_hora_saida) }}</div>
              <div class="fw-bold">{{ v.sentido === 'ida' ? v.origem : v.destino }}</div>
            </div>
            <div class="ponto fim">
              <div class="small text-secondary">Destino</div>
              <div class="fw-bold">{{ v.sentido === 'ida' ? v.destino : v.origem }}</div>
            </div>
          </div>

          <div class="bg-light rounded-3 p-3 small">
            <div><i class="bi bi-person-fill me-2"></i><strong>Motorista:</strong> {{ v.motorista.nome }}
              <i v-if="v.motorista.verificado" class="bi bi-patch-check-fill text-primary" title="Perfil verificado pela UVV"></i>
              <span v-if="v.motorista.curso" class="text-secondary"> · {{ v.motorista.curso }}</span>
            </div>
            <div v-if="v.veiculo" class="mt-1">
              <i class="bi bi-car-front-fill me-2"></i><strong>Carro:</strong> {{ v.veiculo.modelo }} {{ v.veiculo.cor }}
              <span class="badge text-bg-dark font-monospace ms-1">{{ v.veiculo.placa }}</span>
            </div>
            <div v-if="v.iniciada_em" class="mt-1"><i class="bi bi-play-circle me-2"></i>Iniciada às {{ hora(v.iniciada_em) }}</div>
          </div>

          <!-- Ultima posicao enviada pelo GPS do motorista (mapa do OpenStreetMap) -->
          <div v-if="v.ultima_posicao" class="mt-3">
            <div class="small fw-semibold mb-1"><i class="bi bi-geo-alt-fill text-danger me-1"></i>Última localização · {{ hora(v.ultima_posicao.em) }}</div>
            <iframe class="mapa-viagem" :src="mapa" title="Mapa com a localização do carro" loading="lazy"></iframe>
            <a :href="`https://www.openstreetmap.org/?mlat=${v.ultima_posicao.lat}&mlon=${v.ultima_posicao.lng}#map=16/${v.ultima_posicao.lat}/${v.ultima_posicao.lng}`" target="_blank" rel="noopener" class="small">Abrir mapa maior</a>
          </div>
          <p v-else class="small text-secondary mt-3 mb-0"><i class="bi bi-geo me-1"></i>A localização aparece aqui quando o motorista ligar o GPS durante a viagem.</p>

          <div class="alert alert-light border small mt-3 mb-0">
            Este link para de funcionar quando a viagem termina. Em caso de emergência, ligue <a href="tel:190" class="fw-bold">190</a>.
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import AoVivo from '../components/AoVivo.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAoVivo } from '../composables/useAoVivo'
import api from '../services/api'
import { dataHora, hora } from '../utils/formato'

const props = defineProps({ token: { type: String, required: true } })

const v = ref(null)
const erro = ref('')
const carregando = ref(true)

const mapa = computed(() => {
  const p = v.value?.ultima_posicao
  if (!p) return ''
  const d = 0.006
  return `https://www.openstreetmap.org/export/embed.html?bbox=${p.lng - d},${p.lat - d},${p.lng + d},${p.lat + d}&layer=mapnik&marker=${p.lat},${p.lng}`
})

async function buscar() {
  try {
    const { data } = await api.get(`/acompanhar/${props.token}`)
    v.value = data.viagem
    erro.value = ''
  } catch (e) {
    v.value = null
    erro.value = e.mensagem
  }
}

const { atualizadoEm } = useAoVivo(buscar, 10000)

onMounted(async () => {
  await buscar()
  carregando.value = false
})
</script>
