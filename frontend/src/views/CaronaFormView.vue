<template>
  <div class="container py-4" style="max-width: 760px">
    <RouterLink :to="editando ? '/minhas-caronas' : '/caronas'" class="small text-decoration-none"><i class="bi bi-arrow-left me-1"></i>Voltar</RouterLink>
    <h1 class="titulo-pagina h3 mt-2 mb-1">{{ editando ? 'Editar carona' : 'Oferecer carona' }}</h1>
    <p class="text-secondary">
      {{ editando ? 'Os passageiros já aceitos continuam na carona.' : 'Publique seu trajeto e escolha quem vai com você.' }}
    </p>

    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <form v-else class="card p-4" novalidate @submit.prevent="salvar">
      <AlertaMensagem :texto="erroApi" @fechar="erroApi = ''" />

      <!-- Sentido -->
      <label class="form-label">Sentido</label>
      <div class="btn-group w-100 mb-3" role="group">
        <input id="ida" v-model="form.sentido" class="btn-check" type="radio" value="ida" />
        <label class="btn btn-outline-primary" for="ida"><i class="bi bi-house me-1"></i>Ida: bairro → UVV</label>
        <input id="volta" v-model="form.sentido" class="btn-check" type="radio" value="volta" />
        <label class="btn btn-outline-primary" for="volta"><i class="bi bi-mortarboard me-1"></i>Volta: UVV → bairro</label>
      </div>

      <div class="row g-3">
        <div class="col-md-5">
          <label class="form-label" for="bairro">Bairro {{ form.sentido === 'ida' ? 'de saída' : 'de chegada' }}</label>
          <input id="bairro" v-model.trim="form.bairro_origem" list="lista-bairros" :class="['form-control', { 'is-invalid': erros.bairro_origem }]" />
          <datalist id="lista-bairros"><option v-for="b in BAIRROS" :key="b" :value="b" /></datalist>
          <div class="invalid-feedback">{{ erros.bairro_origem }}</div>
        </div>
        <div class="col-md-7">
          <label class="form-label" for="endereco">{{ form.sentido === 'ida' ? 'Ponto de saída' : 'Ponto de chegada no bairro' }}</label>
          <input id="endereco" v-model.trim="form.endereco_origem" maxlength="255" :class="['form-control', { 'is-invalid': erros.endereco_origem }]" placeholder="Rua, número ou referência" />
          <div class="invalid-feedback">{{ erros.endereco_origem }}</div>
        </div>
        <div class="col-12">
          <label class="form-label" for="destino">{{ form.sentido === 'ida' ? 'Destino na UVV' : 'Saída da UVV' }}</label>
          <select id="destino" v-model="form.destino" class="form-select">
            <option v-for="d in DESTINOS" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>

        <div class="col-6 col-md-4">
          <label class="form-label" for="data">Data</label>
          <input id="data" v-model="form.data" type="date" :min="hojeLocal()" :class="['form-control', { 'is-invalid': erros.data }]" />
          <div class="invalid-feedback">{{ erros.data }}</div>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label" for="hora">Horário de saída</label>
          <input id="hora" v-model="form.hora" type="time" :class="['form-control', { 'is-invalid': erros.hora }]" />
          <div class="invalid-feedback">{{ erros.hora }}</div>
        </div>
        <div class="col-6 col-md-2">
          <label class="form-label" for="vagas">Vagas</label>
          <input id="vagas" v-model.number="form.vagas" type="number" min="1" max="6" :class="['form-control', { 'is-invalid': erros.vagas }]" />
          <div class="invalid-feedback">{{ erros.vagas }}</div>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label" for="valor">Rateio (R$)</label>
          <div class="input-group has-validation">
            <span class="input-group-text">R$</span>
            <input id="valor" v-model.number="form.valor_por_passageiro" type="number" min="0" :max="teto" step="0.50" :class="['form-control', { 'is-invalid': erros.valor_por_passageiro }]" />
            <div class="invalid-feedback">{{ erros.valor_por_passageiro }}</div>
          </div>
        </div>

        <!-- Carona solidaria: valor sugerido = combustivel dividido entre todos -->
        <div class="col-12">
          <div class="bg-light rounded-3 p-3 d-flex flex-wrap align-items-end gap-2">
            <div>
              <label class="form-label mb-1" for="distancia">Distância aproximada <span class="text-secondary fw-normal">(km, opcional)</span></label>
              <input id="distancia" v-model.number="form.distancia_km" type="number" min="0" max="500" step="0.1" class="form-control" style="max-width: 9rem" :class="{ 'is-invalid': erros.distancia_km }" />
            </div>
            <button type="button" class="btn btn-outline-primary" :disabled="!form.distancia_km" @click="sugerirValor">
              <i class="bi bi-calculator me-1"></i>Sugerir rateio
            </button>
            <div class="small text-secondary flex-grow-1">
              <span v-if="sugestao !== null">Sugestão: <strong>{{ dinheiro(sugestao) }}</strong> por pessoa (combustível dividido entre você e {{ form.vagas }} passageiro(s)).</span>
              <span v-else>O CaronaUVV é carona solidária: o rateio só divide o combustível (máximo de {{ dinheiro(teto) }}).</span>
            </div>
          </div>
        </div>

        <div class="col-12">
          <label class="form-label" for="obs">Observações <span class="text-secondary fw-normal">(opcional)</span></label>
          <textarea id="obs" v-model.trim="form.observacoes" rows="2" maxlength="300" :class="['form-control', { 'is-invalid': erros.observacoes }]" placeholder="Ex.: saio pontualmente; cabe mochila no porta-malas"></textarea>
          <div class="invalid-feedback">{{ erros.observacoes }}</div>
        </div>

        <div class="col-md-7">
          <label class="form-label" for="veiculo">Carro</label>
          <select id="veiculo" v-model="form.veiculo_id" class="form-select">
            <option :value="null">Não informar</option>
            <option v-for="v in veiculos" :key="v.id" :value="v.id">{{ v.modelo }} {{ v.cor }} · {{ v.placa }}</option>
          </select>
          <div class="form-text">
            <RouterLink to="/perfil#veiculos">Cadastrar um carro</RouterLink> para o passageiro reconhecer você.
          </div>
        </div>
        <div class="col-md-5 d-flex align-items-center">
          <div class="form-check form-switch mt-md-3">
            <input id="auto" v-model="form.reserva_automatica" class="form-check-input" type="checkbox" role="switch" />
            <label class="form-check-label" for="auto">
              Aceitar pedidos automaticamente
              <span class="d-block small text-secondary">O passageiro já sai com a vaga confirmada.</span>
            </label>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-4">
        <RouterLink :to="editando ? '/minhas-caronas' : '/caronas'" class="btn btn-light">Cancelar</RouterLink>
        <button type="submit" class="btn btn-primary px-4" :disabled="salvando">
          <span v-if="salvando" class="spinner-border spinner-border-sm me-1"></span>
          {{ editando ? 'Salvar alterações' : 'Publicar carona' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import api from '../services/api'
import { BAIRROS } from '../utils/bairros'
import { dinheiro, hojeLocal } from '../utils/formato'
import { errosDoServidor, regras, validar } from '../utils/validacao'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const editando = computed(() => Boolean(props.id))

const DESTINOS = ['UVV - Entrada principal', 'UVV - Prédio Branco', 'UVV - Biopráticas', 'UVV - Estacionamento']

const form = reactive({
  sentido: 'ida',
  bairro_origem: '',
  endereco_origem: '',
  destino: DESTINOS[0],
  data: hojeLocal(1),
  hora: '18:30',
  vagas: 3,
  valor_por_passageiro: 0,
  veiculo_id: null,
  reserva_automatica: false,
  observacoes: '',
  distancia_km: null
})
const teto = ref(5)
const sugestao = ref(null)

async function sugerirValor() {
  try {
    const { data } = await api.get('/caronas/valor-sugerido', {
      params: { distancia_km: form.distancia_km, vagas: form.vagas || 1 }
    })
    sugestao.value = data.valor_sugerido
    teto.value = data.teto
    form.valor_por_passageiro = data.valor_sugerido
  } catch (e) {
    erroApi.value = e.mensagem
  }
}
const veiculos = ref([])
const erros = ref({})
const erroApi = ref('')
const carregando = ref(true)
const salvando = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get('/veiculos')
    veiculos.value = data.veiculos
    if (!editando.value && veiculos.value.length === 1) form.veiculo_id = veiculos.value[0].id

    if (editando.value) {
      const { data: d } = await api.get(`/caronas/${props.id}`)
      const c = d.carona
      Object.assign(form, {
        sentido: c.sentido,
        bairro_origem: c.bairro_origem,
        endereco_origem: c.endereco_origem,
        destino: c.destino,
        data: c.data_hora_saida.slice(0, 10),
        hora: c.data_hora_saida.slice(11, 16),
        vagas: c.vagas,
        valor_por_passageiro: c.valor_por_passageiro,
        veiculo_id: c.veiculo?.id ?? null,
        reserva_automatica: c.reserva_automatica,
        observacoes: c.observacoes || '',
        distancia_km: c.distancia_km
      })
      if (!DESTINOS.includes(c.destino)) DESTINOS.push(c.destino)
    }
  } catch (e) {
    erroApi.value = e.mensagem
  } finally {
    carregando.value = false
  }
})

function validarForm() {
  const e = validar(form, {
    bairro_origem: [regras.obrigatorio],
    endereco_origem: [regras.obrigatorio],
    data: [regras.obrigatorio],
    hora: [regras.obrigatorio],
    vagas: [(v) => (Number.isInteger(v) && v >= 1 && v <= 6 ? null : 'De 1 a 6 vagas.')],
    valor_por_passageiro: [
      (v) => (v === '' || v === null || Number(v) >= 0 ? null : 'O valor não pode ser negativo.'),
      (v) => (Number(v || 0) <= teto.value ? null : `Carona solidária: máximo de ${dinheiro(teto.value)} por pessoa.`)
    ]
  })
  // Regra de negocio (tambem validada na API): saida precisa ser no futuro
  if (!e.data && !e.hora && new Date(`${form.data}T${form.hora}`) <= new Date()) {
    e.hora = 'A saída precisa ser no futuro.'
  }
  return e
}

async function salvar() {
  erroApi.value = ''
  erros.value = validarForm()
  if (Object.keys(erros.value).length) return

  const { data, hora, ...resto } = form
  const dados = {
    ...resto,
    valor_por_passageiro: Number(form.valor_por_passageiro || 0),
    distancia_km: form.distancia_km || null,
    data_hora_saida: `${data}T${hora}`
  }

  salvando.value = true
  try {
    if (editando.value) {
      await api.put(`/caronas/${props.id}`, dados)
    } else {
      await api.post('/caronas', dados)
    }
    router.push({ name: 'minhas-caronas', query: { ok: editando.value ? 'editada' : 'criada' } })
  } catch (e) {
    erroApi.value = e.mensagem
    erros.value = { ...erros.value, ...errosDoServidor(e, Object.keys(form)) }
  } finally {
    salvando.value = false
  }
}
</script>
