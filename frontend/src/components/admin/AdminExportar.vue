<template>
  <!-- Exportar dados: planilhas CSV para Excel / Google Planilhas -->
  <section aria-labelledby="titulo-exportar">
    <h2 id="titulo-exportar" class="visually-hidden">Exportar dados</h2>

    <AlertaMensagem :texto="aviso.texto" :tipo="aviso.tipo" @fechar="aviso.texto = ''" />

    <div class="row g-3">
      <div v-for="rel in RELATORIOS" :key="rel.tipo" class="col-md-4">
        <div class="relatorio h-100">
          <div class="d-flex align-items-center gap-3 mb-2">
            <span class="icone" aria-hidden="true"><i :class="['bi', rel.icone]"></i></span>
            <div>
              <h3 class="h6 fw-bold mb-0">{{ rel.nome }}</h3>
              <div v-if="quantidade(rel.tipo) !== null" class="small text-secondary">{{ quantidade(rel.tipo) }} {{ quantidade(rel.tipo) === 1 ? 'linha' : 'linhas' }}</div>
            </div>
          </div>
          <p class="small text-secondary mb-3 flex-grow-1">{{ rel.conteudo }}</p>
          <button type="button" class="btn btn-primary w-100" :disabled="baixando !== null" @click="baixar(rel.tipo, rel.nome)">
            <span v-if="baixando === rel.tipo" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-file-earmark-spreadsheet me-1"></i>Baixar planilha (CSV)
          </button>
        </div>
      </div>
    </div>

    <ul class="regras small text-secondary mt-3 mb-0">
      <li><i class="bi bi-shield-lock me-1"></i>Sem telefone, chave Pix, senha ou foto de documento: só o necessário para a gestão (LGPD).</li>
      <li><i class="bi bi-clock-history me-1"></i>Cada download fica registrado no <RouterLink to="/admin/historico">Histórico</RouterLink>, com quem baixou e quando.</li>
      <li><i class="bi bi-table me-1"></i>Abre direto no Excel em português (separador ";" e vírgula decimal) e no Google Planilhas.</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import api, { mensagemDeErro } from '../../services/api'
import { painel } from '../../stores/admin'
import type { TipoAviso } from '../../stores/auth'
import AlertaMensagem from '../AlertaMensagem.vue'

type TipoRelatorio = 'usuarios' | 'avaliacoes' | 'viagens'

const RELATORIOS: { tipo: TipoRelatorio; nome: string; icone: string; conteudo: string }[] = [
  {
    tipo: 'usuarios',
    nome: 'Usuários',
    icone: 'bi-people-fill',
    conteudo: 'Nome, e-mail, matrícula, curso, bairro, selos e documentos verificados, situação da conta, média recebida, caronas oferecidas e viagens como passageiro.'
  },
  {
    tipo: 'avaliacoes',
    nome: 'Avaliações',
    icone: 'bi-star-half',
    conteudo: 'Data, carona e trecho, quem avaliou, quem foi avaliado (motorista ou passageiro), nota, comentário e etiquetas.'
  },
  {
    tipo: 'viagens',
    nome: 'Viagens',
    icone: 'bi-car-front-fill',
    conteudo: 'Saída, sentido, trecho, motorista, carro e placa, situação, vagas, quem viajou, faltas, distância, valor por passageiro e duração real.'
  }
]

const baixando = ref<TipoRelatorio | null>(null)
const aviso = reactive<{ texto: string; tipo: TipoAviso }>({ texto: '', tipo: 'success' })

function quantidade(tipo: TipoRelatorio): number | null {
  const r = painel.resumo
  if (!r) return null
  return tipo === 'usuarios' ? r.usuarios.total : tipo === 'avaliacoes' ? r.confianca.avaliacoes : r.caronas.total
}

/** A API exige o token, entao o arquivo vem pelo axios e o navegador salva a partir da memoria. */
async function baixar(tipo: TipoRelatorio, nome: string): Promise<void> {
  baixando.value = tipo
  aviso.texto = ''
  try {
    const resp = await api.get<Blob>(`/admin/exportar/${tipo}`, { responseType: 'blob' })
    const disposicao = String(resp.headers['content-disposition'] ?? '')
    const arquivo = /filename="([^"]+)"/.exec(disposicao)?.[1] ?? `caronauvv_${tipo}.csv`
    const url = URL.createObjectURL(resp.data)
    const link = document.createElement('a')
    link.href = url
    link.download = arquivo
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    aviso.tipo = 'success'
    aviso.texto = `Planilha de ${nome.toLowerCase()} baixada (${arquivo}).`
  } catch (e) {
    aviso.tipo = 'danger'
    aviso.texto = mensagemDeErro(e, 'Não foi possível gerar a planilha. Tente novamente.')
  } finally {
    baixando.value = null
  }
}
</script>

<style scoped>
.relatorio {
  display: flex;
  flex-direction: column;
  padding: 1.1rem 1.25rem;
  border-radius: 1rem;
  background: #eef3fa;
}

.icone {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 0.8rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  background: #fff;
  color: var(--uvv-azul-2);
}

.regras {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}
</style>
