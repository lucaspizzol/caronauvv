<template>
  <!-- Resumo de uma carona: horario, trajeto, motorista, carro, vagas e valor -->
  <div class="d-flex gap-2 gap-sm-3">
    <div class="text-center coluna-hora" style="min-width: 4.5rem">
      <div class="horario">{{ hora(carona.data_hora_saida) }}</div>
      <div class="small text-secondary fw-semibold mt-1">{{ dataCurta(carona.data_hora_saida) }}</div>
      <span class="badge rounded-pill text-bg-light border mt-2">
        <i :class="['bi', carona.sentido === 'ida' ? 'bi-arrow-right' : 'bi-arrow-left']"></i>
        {{ carona.sentido === 'ida' ? 'Ida' : 'Volta' }}
      </span>
    </div>

    <div class="flex-grow-1 min-w-0">
      <div class="rota mb-2">
        <div class="ponto mb-2">
          <div class="fw-bold">{{ carona.sentido === 'ida' ? carona.bairro_origem : carona.destino }}</div>
          <div class="small text-secondary text-truncate">
            {{ carona.sentido === 'ida' ? carona.endereco_origem : 'Saída da UVV' }}
          </div>
        </div>
        <div class="ponto fim">
          <div class="fw-bold">{{ carona.sentido === 'ida' ? carona.destino : carona.bairro_origem }}</div>
          <div v-if="carona.sentido === 'volta'" class="small text-secondary text-truncate">{{ carona.endereco_origem }}</div>
        </div>
      </div>

      <div class="d-flex flex-wrap align-items-center gap-3 small">
        <span class="d-inline-flex align-items-center gap-2">
          <AvatarUsuario :usuario="carona.motorista" :tamanho="2.2" />
          <span>
            <RouterLink :to="`/usuarios/${carona.motorista?.id}`" class="fw-semibold text-reset">{{ carona.motorista?.nome }}</RouterLink>
            <span v-if="carona.motorista?.curso" class="text-secondary d-none d-sm-inline"> · {{ carona.motorista.curso }}</span>
            <span class="d-block"><ReputacaoResumo :usuario="carona.motorista" /></span>
          </span>
        </span>
        <span v-if="carona.veiculo" class="text-secondary">
          <i class="bi bi-car-front me-1"></i>{{ carona.veiculo.modelo }} {{ carona.veiculo.cor }}
          <span v-if="carona.veiculo.placa" class="badge text-bg-light border ms-1">{{ carona.veiculo.placa }}</span>
        </span>
      </div>
      <div v-if="carona.observacoes" class="small text-secondary mt-2"><i class="bi bi-chat-left-text me-1"></i>{{ carona.observacoes }}</div>
    </div>

    <div class="text-end coluna-preco" style="min-width: 5.5rem">
      <div class="fw-bold fs-5" :class="Number(carona.valor_por_passageiro) === 0 ? 'text-success' : ''">
        {{ dinheiro(carona.valor_por_passageiro) }}
      </div>
      <div class="small text-secondary">por pessoa</div>
      <div class="vagas-bolinhas mt-2" :title="`${carona.vagas_restantes} de ${carona.vagas} vagas livres`">
        <i v-for="n in carona.vagas" :key="n" :class="['bi', n <= carona.vagas - carona.vagas_restantes ? 'bi-person-fill text-secondary' : 'bi-person text-primary']"></i>
      </div>
      <div class="small fw-semibold" :class="carona.vagas_restantes > 0 ? 'text-primary' : 'text-secondary'">
        {{ carona.vagas_restantes }} {{ carona.vagas_restantes === 1 ? 'vaga' : 'vagas' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Carona } from '../types/api'
import { dataCurta, dinheiro, hora } from '../utils/formato'
import AvatarUsuario from './AvatarUsuario.vue'
import ReputacaoResumo from './ReputacaoResumo.vue'

defineProps<{ carona: Carona }>()
</script>
