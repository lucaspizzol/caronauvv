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
          <input
            id="bairro" v-model.trim="form.bairro_origem" list="lista-bairros" autocomplete="off" placeholder="Ex.: Itapuã"
            :class="['form-control', { 'is-invalid': erros.bairro_origem }]"
          />
          <datalist id="lista-bairros"><option v-for="b in BAIRROS" :key="b" :value="b" /></datalist>
          <div class="invalid-feedback">{{ erros.bairro_origem }}</div>
        </div>
        <div class="col-md-7">
          <label class="form-label" for="endereco">Rua {{ form.sentido === 'ida' ? 'de saída' : 'de chegada' }}</label>
          <input
            id="endereco" v-model.trim="form.endereco_origem" maxlength="255" placeholder="Ex.: Rua Itaúnas, 120 (ou um ponto de referência)"
            :class="['form-control', { 'is-invalid': erros.endereco_origem }]"
          />
          <div class="invalid-feedback">{{ erros.endereco_origem }}</div>
        </div>
        <div v-if="doPerfil" class="col-12 mt-1">
          <div class="form-text">
            <i class="bi bi-geo-alt me-1"></i>Bairro e rua vieram do seu perfil. Pode mudar só para esta carona; o endereço
            fixo fica em <RouterLink to="/perfil">Meu perfil</RouterLink>.
          </div>
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
          <div class="rateio p-3">
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="rateio-icone"><i class="bi bi-calculator"></i></span>
              <div>
                <div class="fw-bold">Quanto cobrar de cada passageiro?</div>
                <div class="small text-secondary">
                  Carona solidária: o rateio só divide o combustível entre você e os passageiros (máximo de {{ dinheiro(teto) }}).
                </div>
              </div>
            </div>
            <div class="d-flex flex-wrap align-items-end gap-2">
              <div>
                <label class="form-label mb-1 small" for="distancia">Distância até a UVV (km)</label>
                <input
                  id="distancia" v-model.number="form.distancia_km" type="number" min="0" max="500" step="0.1" class="form-control"
                  style="max-width: 9rem" :class="{ 'is-invalid': erros.distancia_km }" @input="distanciaManual"
                />
              </div>
              <button type="button" class="btn btn-warning fw-semibold" :disabled="!form.distancia_km || calculando" @click="sugerirValor">
                <span v-if="calculando" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-magic me-1"></i>Calcular rateio sugerido
              </button>
            </div>
            <div class="small mt-2" aria-live="polite">
              <span v-if="sugestao !== null" class="text-success">
                <i class="bi bi-check-circle-fill me-1"></i>Sugestão aplicada: <strong>{{ dinheiro(sugestao) }}</strong> por pessoa
                (combustível de {{ Number(form.distancia_km).toLocaleString('pt-BR') }} km dividido entre você e {{ form.vagas }} passageiro(s)). Você ainda pode mudar o valor.
              </span>
              <span v-else-if="distanciaEstimadaPeloBairro" class="text-secondary">
                <i class="bi bi-info-circle me-1"></i>Distância estimada pelo bairro {{ form.bairro_origem }}; ajuste se o seu trajeto for diferente.
              </span>
              <span v-else class="text-secondary">Informe a distância e clique em <strong>Calcular rateio sugerido</strong>.</span>
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

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import api, { mensagemDeErro } from '../services/api'
import { auth } from '../stores/auth'
import type { Carona, ErrosCampos, Sentido, Veiculo } from '../types/api'
import { BAIRROS, distanciaEstimada } from '../utils/bairros'
import { dinheiro, hojeLocal } from '../utils/formato'
import { errosDoServidor, regras, validar } from '../utils/validacao'

const props = withDefaults(defineProps<{ id?: string | null }>(), { id: null })
const router = useRouter()
const editando = computed(() => Boolean(props.id))

const DESTINOS = ['UVV - Entrada principal', 'UVV - Prédio Branco', 'UVV - Biopráticas', 'UVV - Estacionamento']

interface FormCarona {
  sentido: Sentido
  bairro_origem: string
  endereco_origem: string
  destino: string
  data: string // AAAA-MM-DD
  hora: string // HH:MM
  vagas: number
  valor_por_passageiro: number | ''
  veiculo_id: number | null
  reserva_automatica: boolean
  observacoes: string
  distancia_km: number | null
}

const form = reactive<FormCarona>({
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
const sugestao = ref<number | null>(null)
const veiculos = ref<Veiculo[]>([])
const erros = ref<ErrosCampos>({})
const erroApi = ref('')
const carregando = ref(true)
const salvando = ref(false)
const calculando = ref(false)
const doPerfil = ref(false) // bairro e rua preenchidos com o endereco do perfil
const distanciaEstimadaPeloBairro = ref(false) // vira false quando o motorista digita a distancia

// Escolheu o bairro: preenche a distancia ate a UVV (se o motorista nao tiver digitado uma)
watch(
  () => form.bairro_origem,
  (bairro) => {
    if (form.distancia_km && !distanciaEstimadaPeloBairro.value) return
    const km = distanciaEstimada(bairro)
    form.distancia_km = km
    distanciaEstimadaPeloBairro.value = km !== null
  }
)

// Mudou a distancia ou as vagas: a sugestao antiga deixa de valer
watch(
  () => [form.distancia_km, form.vagas],
  () => (sugestao.value = null)
)

function distanciaManual(): void {
  distanciaEstimadaPeloBairro.value = false
}

async function sugerirValor(): Promise<void> {
  calculando.value = true
  try {
    const { data } = await api.get<{ valor_sugerido: number; teto: number }>('/caronas/valor-sugerido', {
      params: { distancia_km: form.distancia_km, vagas: form.vagas || 1 }
    })
    sugestao.value = data.valor_sugerido
    teto.value = data.teto
    form.valor_por_passageiro = data.valor_sugerido
  } catch (e) {
    erroApi.value = mensagemDeErro(e)
  } finally {
    calculando.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get<{ veiculos: Veiculo[] }>('/veiculos')
    veiculos.value = data.veiculos
    if (!editando.value && veiculos.value.length === 1) form.veiculo_id = veiculos.value[0].id

    // Carona nova: comeca com o bairro e a rua do perfil (o motorista pode trocar)
    if (!editando.value && auth.usuario) {
      form.bairro_origem = auth.usuario.bairro || ''
      form.endereco_origem = auth.usuario.endereco || ''
      doPerfil.value = Boolean(form.bairro_origem || form.endereco_origem)
    }

    if (editando.value) {
      const { data: d } = await api.get<{ carona: Carona }>(`/caronas/${props.id}`)
      const c = d.carona
      Object.assign(form, {
        sentido: c.sentido,
        bairro_origem: c.bairro_origem,
        endereco_origem: c.endereco_origem || '',
        destino: c.destino,
        data: c.data_hora_saida.slice(0, 10),
        hora: c.data_hora_saida.slice(11, 16),
        vagas: c.vagas,
        valor_por_passageiro: c.valor_por_passageiro,
        veiculo_id: c.veiculo?.id ?? null,
        reserva_automatica: c.reserva_automatica,
        observacoes: c.observacoes || '',
        distancia_km: c.distancia_km
      } satisfies FormCarona)
      if (!DESTINOS.includes(c.destino)) DESTINOS.push(c.destino)
    }
  } catch (e) {
    erroApi.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
})

function validarForm(): ErrosCampos {
  const e = validar(form, {
    bairro_origem: [regras.obrigatorio],
    endereco_origem: [regras.obrigatorio],
    data: [regras.obrigatorio],
    hora: [regras.obrigatorio],
    vagas: [(v) => (Number.isInteger(v) && Number(v) >= 1 && Number(v) <= 6 ? null : 'De 1 a 6 vagas.')],
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

async function salvar(): Promise<void> {
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
    void router.push({ name: 'minhas-caronas', query: { ok: editando.value ? 'editada' : 'criada' } })
  } catch (e) {
    erroApi.value = mensagemDeErro(e)
    erros.value = { ...erros.value, ...errosDoServidor(e, Object.keys(form)) }
  } finally {
    salvando.value = false
  }
}
</script>

<style scoped>
/* Bloco do rateio em destaque (amarelo UVV) para o motorista nao deixar de calcular */
.rateio {
  background: #fff8e1;
  border: 1px solid #ffe08a;
  border-left: 4px solid var(--uvv-amarelo);
  border-radius: 0.75rem;
}

.rateio-icone {
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--uvv-amarelo);
  color: var(--uvv-azul);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
}
</style>
