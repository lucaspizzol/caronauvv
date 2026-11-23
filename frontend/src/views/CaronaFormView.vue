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
          <CampoBairro id="bairro" v-model="form.bairro_origem" :invalido="Boolean(erros.bairro_origem)" @escolher="escolheuBairro" />
          <div v-if="erros.bairro_origem" class="invalid-feedback d-block">{{ erros.bairro_origem }}</div>
        </div>
        <div class="col-md-7">
          <label class="form-label" for="endereco">Rua {{ form.sentido === 'ida' ? 'de saída' : 'de chegada' }}</label>
          <CampoRua
            id="endereco" v-model="form.endereco_origem" :cidade="cidadeDoBairro" :invalido="Boolean(erros.endereco_origem)"
            placeholder="Ex.: Rua Itaúnas, 120 (ou um ponto de referência)" @endereco="escolheuRua"
          />
          <div v-if="erros.endereco_origem" class="invalid-feedback d-block">{{ erros.endereco_origem }}</div>
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
        <div class="col-6 col-md-4">
          <label class="form-label" for="hora">Horário de saída</label>
          <input id="hora" v-model="form.hora" type="time" :class="['form-control', { 'is-invalid': erros.hora }]" />
          <div class="invalid-feedback">{{ erros.hora }}</div>
        </div>
        <div v-if="esperando > 0 && !editando" class="col-12">
          <div class="alert alert-info py-2 mb-0 small d-flex align-items-center gap-2" role="status">
            <i class="bi bi-people-fill fs-5"></i>
            <span><strong>{{ esperando }} {{ esperando === 1 ? 'aluno esperando' : 'alunos esperando' }}</strong> carona
              {{ form.sentido === 'ida' ? 'de' : 'para' }} {{ form.bairro_origem }} nesse horário. Ao publicar, eles são avisados na hora.</span>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <label class="form-label" for="vagas">Vagas</label>
          <input id="vagas" v-model.number="form.vagas" type="number" min="1" max="6" :class="['form-control', { 'is-invalid': erros.vagas }]" />
          <div class="invalid-feedback">{{ erros.vagas }}</div>
        </div>

        <div class="col-md-7">
          <label class="form-label" for="veiculo">Carro</label>
          <select id="veiculo" v-model="form.veiculo_id" class="form-select">
            <option :value="null">Não informar</option>
            <option v-for="v in veiculos" :key="v.id" :value="v.id">{{ v.modelo }} {{ v.cor }} · {{ v.placa }}</option>
          </select>
          <div class="form-text">
            <RouterLink to="/perfil#veiculos">Cadastre o carro</RouterLink> com o tipo de combustível e o consumo: o cálculo usa esses dados.
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

        <!-- ============ RATEIO: calculo do combustivel + adicional ============ -->
        <div class="col-12">
          <div class="rateio p-3">
            <div class="d-flex align-items-center gap-2 mb-3">
              <span class="rateio-icone"><i class="bi bi-calculator"></i></span>
              <div>
                <div class="fw-bold">Quanto cobrar de cada passageiro?</div>
                <div class="small text-secondary">
                  O combustível da viagem é dividido entre todos no carro; o adicional é a sua parte pela carona
                  (total de até {{ reais(teto) }} por pessoa).
                </div>
              </div>
            </div>

            <div class="row g-2">
              <div class="col-6 col-md-3">
                <label class="form-label mb-1 small" for="distancia">Distância (km)</label>
                <input
                  id="distancia" v-model.number="form.distancia_km" type="number" min="0" max="500" step="0.001" class="form-control"
                  :class="{ 'is-invalid': erros.distancia_km }" @input="distanciaManual"
                />
                <div class="form-text mt-1">{{ form.distancia_km ? `= ${Math.round(Number(form.distancia_km) * 1000).toLocaleString('pt-BR')} m` : 'Até a UVV' }}</div>
                <div class="invalid-feedback">{{ erros.distancia_km }}</div>
              </div>
              <div class="col-6 col-md-3">
                <label class="form-label mb-1 small" for="energia">Combustível</label>
                <select id="energia" v-model="calc.energia" class="form-select">
                  <option v-for="(info, chave) in ENERGIAS" :key="chave" :value="chave">{{ info.texto }}</option>
                </select>
              </div>
              <div class="col-6 col-md-3">
                <label class="form-label mb-1 small" for="consumo">Consumo ({{ unidadeConsumo(calc.energia) }})</label>
                <input
                  id="consumo" v-model.number="calc.consumo_km" type="number" min="0.1" max="60" step="0.1" class="form-control"
                  :placeholder="`média ${numeroBr(ENERGIAS[calc.energia].consumoMedio, 1)}`" :class="{ 'is-invalid': erros.consumo_km }"
                />
                <div class="invalid-feedback">{{ erros.consumo_km }}</div>
              </div>
              <div class="col-6 col-md-3">
                <label class="form-label mb-1 small" for="adicional">Adicional por pessoa</label>
                <div class="input-group has-validation">
                  <span class="input-group-text">R$</span>
                  <input
                    id="adicional" v-model.number="calc.adicional" type="number" min="0" step="0.05" class="form-control"
                    :class="{ 'is-invalid': erros.adicional_por_passageiro || erros.adicional }"
                  />
                  <div class="invalid-feedback">{{ erros.adicional_por_passageiro || erros.adicional }}</div>
                </div>
              </div>
            </div>

            <div class="d-flex flex-wrap align-items-center gap-2 mt-3">
              <button type="button" class="btn btn-warning fw-semibold" :disabled="!form.distancia_km || calculando" @click="ligarCalculo">
                <span v-if="calculando" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-fuel-pump me-1"></i>{{ modoCalculo ? 'Recalcular' : 'Calcular pelo combustível' }}
              </button>
              <span v-if="distanciaEstimadaPeloBairro && !calculo" class="small text-secondary">
                <i class="bi bi-info-circle me-1"></i>{{ textoDistancia }}
              </span>
              <span v-else-if="!form.distancia_km" class="small text-secondary">Informe a distância até a UVV.</span>
            </div>

            <!-- A conta, passo a passo -->
            <div v-if="modoCalculo && calculo" class="conta mt-3" aria-live="polite">
              <div class="linha"><span><i class="bi bi-signpost-2 me-1"></i>Distância</span><span>{{ distanciaTexto(calculo.distancia_m) }}</span></div>
              <div class="linha">
                <span><i :class="['bi me-1', ENERGIAS[calculo.energia].icone]"></i>{{ calculo.energia === 'eletrico' ? 'Energia gasta' : 'Combustível gasto' }}</span>
                <span>
                  {{ numeroBr(calculo.distancia_km, 3) }} km ÷ {{ numeroBr(calculo.consumo_km, 1) }} {{ unidadeConsumo(calculo.energia) }}
                  = <strong>{{ numeroBr(calculo.quantidade, 3) }} {{ calculo.unidade }}</strong>
                </span>
              </div>
              <div class="linha">
                <span><i class="bi bi-receipt me-1"></i>Custo da viagem</span>
                <span>{{ numeroBr(calculo.quantidade, 3) }} {{ calculo.unidade }} × {{ reais(calculo.preco_unidade) }} = <strong>{{ reais(calculo.custo_total) }}</strong></span>
              </div>
              <div class="linha">
                <span><i class="bi bi-people me-1"></i>Dividido por {{ calculo.ocupantes }} ({{ calculo.ocupantes === 2 ? 'você + 1 vaga' : `você + ${calculo.ocupantes - 1} vagas` }})</span>
                <span><strong>{{ reais(calculo.combustivel_por_pessoa) }}</strong> por pessoa</span>
              </div>
              <div class="linha"><span><i class="bi bi-plus-circle me-1"></i>Adicional pela carona</span><span>{{ reais(calculo.adicional) }}</span></div>
              <div class="linha total">
                <span>Valor por passageiro</span><span>{{ reais(calculo.valor_por_passageiro) }}</span>
              </div>
              <div v-if="calculo.consumo_estimado" class="small text-warning-emphasis mt-2">
                <i class="bi bi-exclamation-triangle me-1"></i>Consumo médio de um carro {{ ENERGIAS[calculo.energia].texto.toLowerCase() }}:
                informe o do seu carro para a conta ficar exata.
              </div>
              <div v-if="acimaDoTeto" class="small text-danger mt-2">
                <i class="bi bi-exclamation-octagon me-1"></i>Passa do máximo de {{ reais(teto) }} por pessoa: diminua o adicional.
              </div>
            </div>

            <!-- Valor final: vem do calculo ou o motorista digita -->
            <div class="row g-2 align-items-end mt-2">
              <div class="col-sm-5">
                <label class="form-label mb-1 small" for="valor">Valor por passageiro</label>
                <div class="input-group has-validation">
                  <span class="input-group-text">R$</span>
                  <input
                    id="valor" v-model.number="form.valor_por_passageiro" type="number" min="0" :max="teto" step="0.05"
                    :class="['form-control fw-semibold', { 'is-invalid': erros.valor_por_passageiro }]" @input="valorManual"
                  />
                  <div class="invalid-feedback">{{ erros.valor_por_passageiro }}</div>
                </div>
              </div>
              <div class="col-sm-7 small" :class="modoCalculo ? 'text-success' : 'text-secondary'">
                <template v-if="modoCalculo"><i class="bi bi-check-circle-fill me-1"></i>Calculado pelo combustível. O passageiro vê a conta.</template>
                <template v-else>Valor digitado por você (sem o detalhamento do combustível).</template>
              </div>
            </div>
          </div>
        </div>

        <div class="col-12">
          <label class="form-label" for="obs">Observações <span class="text-secondary fw-normal">(opcional)</span></label>
          <textarea id="obs" v-model.trim="form.observacoes" rows="2" maxlength="300" :class="['form-control', { 'is-invalid': erros.observacoes }]" placeholder="Ex.: saio pontualmente; cabe mochila no porta-malas"></textarea>
          <div class="invalid-feedback">{{ erros.observacoes }}</div>
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
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import CampoBairro from '../components/CampoBairro.vue'
import CampoRua from '../components/CampoRua.vue'
import api, { camposDoErro, mensagemDeErro } from '../services/api'
import { auth } from '../stores/auth'
import type {
  BairroSugestao, CalculoRateio, Carona, CidadeGrandeVitoria, DistanciaUvv, EnderecoCep, Energia, ErrosCampos,
  RespostaValorSugerido, Sentido, Veiculo
} from '../types/api'
import { distanciaTexto, ENERGIAS, hojeLocal, numeroBr, reais, unidadeConsumo } from '../utils/formato'
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

// Dados do calculo do combustivel (o carro escolhido preenche energia e consumo)
const calc = reactive<{ energia: Energia; consumo_km: number | ''; adicional: number | '' }>({
  energia: 'flex',
  consumo_km: '',
  adicional: 0
})
const modoCalculo = ref(false) // true: o valor vem da conta (e o servidor refaz a conta ao salvar)
const calculo = ref<CalculoRateio | null>(null)
const acimaDoTeto = ref(false)
const teto = ref(5)
const veiculos = ref<Veiculo[]>([])
const erros = ref<ErrosCampos>({})
const erroApi = ref('')
const carregando = ref(true)
const salvando = ref(false)
const calculando = ref(false)
const doPerfil = ref(false) // bairro e rua preenchidos com o endereco do perfil
const distanciaEstimadaPeloBairro = ref(false) // vira false quando o motorista digita a distancia

const cidadeDoBairro = ref<CidadeGrandeVitoria>('Vila Velha') // para sugerir as ruas da cidade certa
const textoDistancia = ref('')

// Bairro escolhido/digitado: preenche a distancia ate a UVV (se o motorista nao tiver digitado uma).
// O servidor usa a rota real de carro (OSRM); se o servico cair, a estimativa pelas coordenadas.
let esperaDistancia: ReturnType<typeof setTimeout> | undefined
watch(
  () => form.bairro_origem,
  (bairro) => {
    clearTimeout(esperaDistancia)
    if (form.distancia_km && !distanciaEstimadaPeloBairro.value) return
    esperaDistancia = setTimeout(() => void distanciaDoBairro(bairro), 400)
  }
)

async function distanciaDoBairro(bairro: string): Promise<void> {
  if (!bairro.trim()) return
  try {
    const { data } = await api.get<DistanciaUvv>('/lugares/distancia', { params: { bairro } })
    if (form.distancia_km && !distanciaEstimadaPeloBairro.value) return // o motorista digitou enquanto isso
    form.distancia_km = data.km
    distanciaEstimadaPeloBairro.value = true
    cidadeDoBairro.value = data.cidade
    textoDistancia.value = data.metodo === 'osrm'
      ? `Distância de carro de ${data.bairro} até a UVV pela rota do mapa (~${data.duracao_min} min sem trânsito); ajuste se o trajeto for diferente.`
      : `Distância estimada de ${data.bairro} até a UVV pelas coordenadas do bairro; ajuste se o trajeto for diferente.`
  } catch {
    // bairro fora da lista: o motorista informa a distancia
    if (distanciaEstimadaPeloBairro.value) form.distancia_km = null
    distanciaEstimadaPeloBairro.value = false
  }
}

// Quantos alunos estao na fila do "Pedir carona" para este bairro/sentido/horario
const esperando = ref(0)
let esperaDemanda: ReturnType<typeof setTimeout> | undefined
watch(
  () => [form.bairro_origem, form.sentido, form.data, form.hora],
  () => {
    clearTimeout(esperaDemanda)
    esperaDemanda = setTimeout(async () => {
      if (!form.bairro_origem || !form.data || !form.hora) {
        esperando.value = 0
        return
      }
      try {
        const { data } = await api.get<{ alunos: number }>('/pedidos-carona/demanda', {
          params: { bairro: form.bairro_origem, sentido: form.sentido, data_hora: `${form.data}T${form.hora}` }
        })
        esperando.value = data.alunos
      } catch {
        esperando.value = 0
      }
    }, 400)
  },
  { immediate: true }
)

function escolheuBairro(b: BairroSugestao): void {
  cidadeDoBairro.value = b.cidade
}

function escolheuRua(r: EnderecoCep): void {
  if (r.bairro) form.bairro_origem = r.bairro
}

// Escolheu o carro: o calculo passa a usar a energia e o consumo dele
watch(
  () => form.veiculo_id,
  (id) => {
    const carro = veiculos.value.find((v) => v.id === id)
    if (!carro) return
    calc.energia = carro.energia
    calc.consumo_km = carro.consumo_km ?? ''
  }
)

// Mudou algum dado da conta: refaz o calculo sozinho (com uma pequena espera enquanto digita)
let espera: ReturnType<typeof setTimeout> | undefined
watch(
  () => [form.distancia_km, form.vagas, calc.energia, calc.consumo_km, calc.adicional],
  () => {
    if (!modoCalculo.value) return
    clearTimeout(espera)
    espera = setTimeout(() => void calcular(), 350)
  }
)

function distanciaManual(): void {
  distanciaEstimadaPeloBairro.value = false
}

function valorManual(): void {
  // digitou o valor: deixa de ser o valor calculado
  modoCalculo.value = false
}

async function calcular(): Promise<void> {
  if (!form.distancia_km || !(Number(form.vagas) >= 1)) {
    calculo.value = null
    return
  }
  calculando.value = true
  try {
    const { data } = await api.get<RespostaValorSugerido>('/caronas/valor-sugerido', {
      params: {
        distancia_km: form.distancia_km,
        vagas: form.vagas,
        energia: calc.energia,
        consumo_km: calc.consumo_km || undefined,
        adicional: calc.adicional || 0
      }
    })
    teto.value = data.teto
    calculo.value = data.calculo ?? null
    acimaDoTeto.value = Boolean(data.acima_do_teto)
    erros.value = {}
    if (modoCalculo.value) form.valor_por_passageiro = data.valor_sugerido
  } catch (e) {
    erros.value = { ...erros.value, ...camposDoErro(e) }
    calculo.value = null
  } finally {
    calculando.value = false
  }
}

async function ligarCalculo(): Promise<void> {
  modoCalculo.value = true
  await calcular()
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
      if (c.rateio) {
        // carona calculada: mostra a mesma conta (energia e consumo usados naquele dia)
        await nextTick() // deixa o watch do carro rodar antes de aplicar a conta salva
        Object.assign(calc, { energia: c.rateio.energia, consumo_km: c.rateio.consumo_km ?? '', adicional: c.rateio.adicional })
        modoCalculo.value = true
      }
    } else {
      // os watches do bairro (distancia) e do carro (combustivel e consumo) rodam no proximo ciclo
      await nextTick()
      // carona nova com distancia conhecida: o valor ja aparece calculado
      if (form.distancia_km) modoCalculo.value = true
    }
    if (modoCalculo.value) await calcular()
  } catch (e) {
    erroApi.value = mensagemDeErro(e)
  } finally {
    carregando.value = false
  }
})

function validarForm(): ErrosCampos {
  const e = validar(form, {
    bairro_origem: [regras.obrigatorio, regras.bairro],
    endereco_origem: [regras.obrigatorio],
    data: [regras.obrigatorio],
    hora: [regras.obrigatorio],
    vagas: [(v) => (Number.isInteger(v) && Number(v) >= 1 && Number(v) <= 6 ? null : 'De 1 a 6 vagas.')],
    valor_por_passageiro: [
      (v) => (v === '' || v === null || Number(v) >= 0 ? null : 'O valor não pode ser negativo.'),
      (v) => (Number(v || 0) <= teto.value ? null : `Carona solidária: máximo de ${reais(teto.value)} por pessoa.`)
    ]
  })
  if (modoCalculo.value && !form.distancia_km) e.distancia_km = 'Informe a distância para calcular.'
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
  const dados: Record<string, unknown> = {
    ...resto,
    valor_por_passageiro: Number(form.valor_por_passageiro || 0),
    distancia_km: form.distancia_km || null,
    data_hora_saida: `${data}T${hora}`
  }
  if (modoCalculo.value) {
    // o servidor refaz a conta com estes dados (nao confia no valor que o navegador mandou)
    Object.assign(dados, {
      energia: calc.energia,
      consumo_km: calc.consumo_km === '' ? null : Number(calc.consumo_km),
      adicional_por_passageiro: Number(calc.adicional || 0)
    })
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
    erros.value = { ...erros.value, ...errosDoServidor(e, [...Object.keys(form), 'consumo_km', 'adicional_por_passageiro']) }
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

/* A conta, uma linha por passo */
.conta {
  background: #fff;
  border: 1px solid #ffe08a;
  border-radius: 0.6rem;
  padding: 0.5rem 0.85rem;
  font-size: 0.9rem;
}

.conta .linha {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.25rem 1rem;
  padding: 0.35rem 0;
  border-bottom: 1px dashed #eee3bd;
}

.conta .linha > span:first-child {
  color: var(--bs-secondary-color);
}

.conta .total {
  border-bottom: 0;
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--uvv-azul);
}

.conta .total > span:first-child {
  color: inherit;
}
</style>
