<template>
  <!-- Foto de perfil: escolher, trocar e remover -->
  <div class="d-flex align-items-center gap-3 mb-3">
    <div class="position-relative">
      <AvatarUsuario :usuario="auth.usuario" :tamanho="5" />
      <span v-if="enviando" class="foto-carregando"><span class="spinner-border spinner-border-sm text-light"></span></span>
    </div>
    <div class="min-w-0">
      <div class="fw-bold text-truncate">{{ auth.usuario?.nome }}</div>
      <div class="small text-secondary text-truncate">Matrícula {{ auth.usuario?.matricula }} · {{ auth.usuario?.email }}</div>
      <div class="d-flex flex-wrap align-items-center gap-2 mt-2">
        <!-- o <label> abre a janela de escolher arquivo; no celular oferece camera ou galeria -->
        <label :class="['btn btn-sm btn-outline-primary mb-0', { disabled: enviando }]" for="arquivo-foto">
          <i class="bi bi-camera me-1"></i>{{ auth.usuario?.foto_url ? 'Trocar foto' : 'Adicionar foto' }}
        </label>
        <input id="arquivo-foto" ref="campo" type="file" class="visually-hidden" :accept="TIPOS_ACEITOS.join(',')" :disabled="enviando" @change="escolher" />
        <BotaoConfirmar v-if="auth.usuario?.foto_url" texto="Remover" pergunta="Remover a foto?" icone="bi-trash" :acao="remover" />
      </div>
    </div>
  </div>
  <p v-if="!auth.usuario?.foto_url && !msg.texto" class="small text-secondary mt-n2">
    <i class="bi bi-person-bounding-box me-1"></i>Uma foto do seu rosto ajuda o motorista e o passageiro a se reconhecerem no ponto de encontro.
  </p>
  <AlertaMensagem :texto="msg.texto" :tipo="msg.tipo" @fechar="msg.texto = ''" />
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import api, { mensagemDeErro } from '../services/api'
import { atualizarUsuario, auth, type TipoAviso } from '../stores/auth'
import type { UsuarioLogado } from '../types/api'
import { prepararFoto, TIPOS_ACEITOS, validarArquivoDeFoto } from '../utils/imagem'
import AlertaMensagem from './AlertaMensagem.vue'
import AvatarUsuario from './AvatarUsuario.vue'
import BotaoConfirmar from './BotaoConfirmar.vue'

const campo = ref<HTMLInputElement | null>(null)
const enviando = ref(false)
const msg = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

function avisar(texto: string, tipo: TipoAviso = 'success'): void {
  msg.texto = texto
  msg.tipo = tipo
}

function limparCampo(): void {
  if (campo.value) campo.value.value = '' // permite escolher o mesmo arquivo de novo
}

async function escolher(evento: Event): Promise<void> {
  const arquivo = (evento.target as HTMLInputElement).files?.[0]
  if (!arquivo) return
  msg.texto = ''
  const problema = validarArquivoDeFoto(arquivo)
  if (problema) {
    avisar(problema, 'danger')
    limparCampo()
    return
  }
  enviando.value = true
  try {
    // recorta em quadrado e reduz no navegador; so entao envia (multipart/form-data)
    const foto = await prepararFoto(arquivo)
    const formulario = new FormData()
    formulario.append('foto', foto, 'foto.jpg')
    const { data } = await api.put<{ usuario: UsuarioLogado }>('/auth/me/foto', formulario)
    atualizarUsuario(data.usuario)
    avisar('Foto atualizada.')
  } catch (e) {
    avisar(mensagemDeErro(e, 'Não deu para enviar a foto.'), 'danger')
  } finally {
    enviando.value = false
    limparCampo()
  }
}

async function remover(): Promise<void> {
  try {
    const { data } = await api.delete<{ usuario: UsuarioLogado }>('/auth/me/foto')
    atualizarUsuario(data.usuario)
    avisar('Foto removida.')
  } catch (e) {
    avisar(mensagemDeErro(e), 'danger')
  }
}
</script>
