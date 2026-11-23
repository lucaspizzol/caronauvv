<template>
  <div class="container py-4" style="max-width: 760px">
    <h1 class="titulo-pagina h3 mb-1">Avaliações</h1>
    <p class="text-secondary">
      Depois de cada viagem, motorista e passageiro se avaliam. A nota fica escondida até os dois avaliarem
      (ou até 7 dias), assim ninguém avalia por vingança.
    </p>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <div v-if="carregando" class="text-center py-5"><span class="spinner-border text-primary"></span></div>

    <div v-else-if="!pendentes.length" class="card vazio">
      <i class="bi bi-star"></i>
      <p class="fw-semibold mb-1">Nenhuma avaliação pendente.</p>
      <p class="small mb-0">Quando uma viagem terminar, ela aparece aqui por 14 dias.</p>
    </div>

    <div v-else class="d-flex flex-column gap-3">
      <form v-for="p in pendentes" :key="p.solicitacao_id" class="card p-3" novalidate @submit.prevent="enviar(p)">
        <div class="d-flex align-items-center gap-3 mb-2">
          <AvatarUsuario :usuario="p.avaliado" />
          <div>
            <div class="fw-bold">
              Como foi {{ p.papel_avaliado === 'motorista' ? 'a viagem com' : 'levar' }}
              <RouterLink :to="`/usuarios/${p.avaliado.id}`">{{ p.avaliado.nome }}</RouterLink>?
            </div>
            <div class="small text-secondary">
              {{ p.papel_avaliado === 'motorista' ? 'Motorista' : 'Passageiro(a)' }} ·
              {{ dataCurta(p.carona.data_hora_saida) }} {{ hora(p.carona.data_hora_saida) }} ·
              {{ p.carona.sentido === 'ida' ? `${p.carona.bairro_origem} → UVV` : `UVV → ${p.carona.bairro_origem}` }}
            </div>
          </div>
        </div>

        <EstrelasNota v-model="form(p).nota" :rotulo="`Nota para ${p.avaliado.nome}`" />
        <div v-if="erros[p.solicitacao_id]?.nota" class="small text-danger">{{ erros[p.solicitacao_id].nota }}</div>

        <div class="mt-3">
          <div class="form-label mb-1">Elogios <span class="text-secondary fw-normal">(opcional)</span></div>
          <div class="d-flex flex-wrap gap-2">
            <button
              v-for="tag in p.tags_sugeridas"
              :key="tag"
              type="button"
              :class="['btn btn-sm tag-escolha', form(p).tags.includes(tag) ? 'btn-primary' : 'btn-outline-secondary']"
              :aria-pressed="form(p).tags.includes(tag)"
              @click="alternarTag(p, tag)"
            >
              {{ tag }}
            </button>
          </div>
        </div>

        <div class="mt-3">
          <label class="form-label" :for="`com-${p.solicitacao_id}`">Comentário <span class="text-secondary fw-normal">(opcional)</span></label>
          <textarea :id="`com-${p.solicitacao_id}`" v-model.trim="form(p).comentario" rows="2" maxlength="500" class="form-control" placeholder="Conte como foi a viagem"></textarea>
        </div>

        <div class="d-flex justify-content-between align-items-center mt-3">
          <RouterLink :to="`/usuarios/${p.avaliado.id}#denunciar`" class="small text-danger">Teve um problema sério? Denunciar</RouterLink>
          <button class="btn btn-primary" :disabled="enviando === p.solicitacao_id">
            <span v-if="enviando === p.solicitacao_id" class="spinner-border spinner-border-sm me-1"></span>Enviar avaliação
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import AlertaMensagem from '../components/AlertaMensagem.vue'
import AvatarUsuario from '../components/AvatarUsuario.vue'
import EstrelasNota from '../components/EstrelasNota.vue'
import api, { camposDoErro, mensagemDeErro } from '../services/api'
import type { TipoAviso } from '../stores/auth'
import type { AvaliacaoPendente, ErrosCampos } from '../types/api'
import { dataCurta, hora } from '../utils/formato'

interface FormAvaliacao {
  nota: number
  tags: string[]
  comentario: string
}

const pendentes = ref<AvaliacaoPendente[]>([])
const carregando = ref(true)
const enviando = ref<number | null>(null)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })
const formularios = reactive<Record<number, FormAvaliacao>>({}) // solicitacao_id -> formulario
const erros = reactive<Record<number, ErrosCampos>>({})

function form(p: AvaliacaoPendente): FormAvaliacao {
  if (!formularios[p.solicitacao_id]) formularios[p.solicitacao_id] = { nota: 0, tags: [], comentario: '' }
  return formularios[p.solicitacao_id]
}

function alternarTag(p: AvaliacaoPendente, tag: string): void {
  const tags = form(p).tags
  const i = tags.indexOf(tag)
  if (i >= 0) tags.splice(i, 1)
  else tags.push(tag)
}

async function carregar(): Promise<void> {
  try {
    const { data } = await api.get<{ pendentes: AvaliacaoPendente[] }>('/avaliacoes/pendentes')
    pendentes.value = data.pendentes
  } catch (e) {
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  } finally {
    carregando.value = false
  }
}

async function enviar(p: AvaliacaoPendente): Promise<void> {
  const dados = form(p)
  erros[p.solicitacao_id] = dados.nota ? {} : { nota: 'Escolha uma nota de 1 a 5 estrelas.' }
  if (!dados.nota) return
  enviando.value = p.solicitacao_id
  try {
    await api.post(`/solicitacoes/${p.solicitacao_id}/avaliacao`, dados)
    pendentes.value = pendentes.value.filter((x) => x.solicitacao_id !== p.solicitacao_id)
    aviso.texto = `Obrigado! Sua avaliação de ${p.avaliado.nome.split(' ')[0]} foi registrada.`
    aviso.tipo = 'success'
  } catch (e) {
    erros[p.solicitacao_id] = camposDoErro(e)
    aviso.texto = mensagemDeErro(e)
    aviso.tipo = 'danger'
  } finally {
    enviando.value = null
  }
}

onMounted(carregar)
</script>
