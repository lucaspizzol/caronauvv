<template>
  <div class="container py-4" style="max-width: 760px">
    <h1 class="titulo-pagina h3 mb-1">Notificações</h1>
    <p class="text-secondary mb-1">Pedidos, confirmações, cancelamentos e avaliações das suas caronas.</p>
    <p class="mb-3"><AoVivo :atualizado-em="atualizadoEm" /></p>

    <AlertaMensagem :texto="erro" @fechar="erro = ''" />

    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <div v-else-if="!notificacoes.length" class="card vazio">
      <i class="bi bi-bell-slash"></i>
      <p class="fw-semibold mb-0">Nenhuma notificação ainda.</p>
    </div>

    <div v-else class="d-flex flex-column gap-2">
      <component
        :is="destino(n) ? 'RouterLink' : 'div'"
        v-for="n in notificacoes"
        :key="n.id"
        :to="destino(n) || undefined"
        :class="['card p-3 text-reset text-decoration-none notificacao', { 'nao-lida': !n.lida, chegou: novas.has(n.id) }]"
      >
        <div class="d-flex gap-3">
          <i :class="['bi fs-4', icone(n.tipo).icone, icone(n.tipo).cor]"></i>
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between gap-2">
              <span class="fw-bold">{{ n.titulo }}</span>
              <span class="small text-secondary text-nowrap">{{ dataHora(n.criada_em) }}</span>
            </div>
            <div class="small">{{ n.texto }}</div>
          </div>
        </div>
      </component>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import AoVivo from '../components/AoVivo.vue'
import { useAoVivo } from '../composables/useAoVivo'
import api from '../services/api'
import { auth } from '../stores/auth'
import { dataHora } from '../utils/formato'

const notificacoes = ref([])
const carregando = ref(true)
const erro = ref('')
const novas = reactive(new Set())

const ICONES = {
  novo_pedido: { icone: 'bi-person-plus-fill', cor: 'text-primary' },
  vaga_confirmada: { icone: 'bi-check-circle-fill', cor: 'text-success' },
  vaga_recusada: { icone: 'bi-x-circle-fill', cor: 'text-danger' },
  carona_cancelada: { icone: 'bi-slash-circle-fill', cor: 'text-danger' },
  pedido_cancelado: { icone: 'bi-person-dash-fill', cor: 'text-warning' },
  viagem_iniciada: { icone: 'bi-car-front-fill', cor: 'text-info' },
  embarque_confirmado: { icone: 'bi-person-check-fill', cor: 'text-success' },
  avaliacao_pendente: { icone: 'bi-star-fill', cor: 'text-warning' },
  nova_avaliacao: { icone: 'bi-star-half', cor: 'text-warning' },
  pagamento_informado: { icone: 'bi-cash-coin', cor: 'text-success' },
  perfil_verificado: { icone: 'bi-patch-check-fill', cor: 'text-primary' },
  seguranca_conta: { icone: 'bi-shield-lock-fill', cor: 'text-primary' },
  alerta_seguranca: { icone: 'bi-exclamation-octagon-fill', cor: 'text-danger' }
}
const icone = (tipo) => ICONES[tipo] || { icone: 'bi-bell-fill', cor: 'text-secondary' }

// Para onde cada notificacao leva ao clicar
function destino(n) {
  if (['avaliacao_pendente', 'nova_avaliacao'].includes(n.tipo)) return '/avaliacoes'
  if (['novo_pedido', 'pedido_cancelado', 'pagamento_informado'].includes(n.tipo)) return '/minhas-caronas'
  if (['vaga_confirmada', 'vaga_recusada', 'carona_cancelada', 'viagem_iniciada', 'embarque_confirmado'].includes(n.tipo)) return '/meus-pedidos'
  if (n.tipo === 'alerta_seguranca' && auth.usuario?.is_admin) return '/admin'
  if (n.tipo === 'perfil_verificado') return '/perfil'
  return null
}

async function buscar() {
  const antes = new Set(notificacoes.value.map((n) => n.id))
  const { data } = await api.get('/notificacoes')
  notificacoes.value = data.notificacoes
  if (antes.size) {
    data.notificacoes.filter((n) => !antes.has(n.id)).forEach((n) => {
      novas.add(n.id)
      setTimeout(() => novas.delete(n.id), 2500)
    })
  }
  // Abrir a tela conta como "li tudo" (o destaque amarelo continua nesta visita)
  if (data.nao_lidas) await api.post('/notificacoes/lidas')
}

const { atualizadoEm } = useAoVivo(buscar)

onMounted(async () => {
  try {
    await buscar()
  } catch (e) {
    erro.value = e.mensagem
  } finally {
    carregando.value = false
  }
})
</script>
