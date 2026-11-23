<template>
  <div :class="logado ? 'container py-4' : 'tela-login py-4'">
    <div :class="logado ? '' : 'container'" style="max-width: 860px">
      <!-- Sem login: cabecalho proprio com volta para o login -->
      <div v-if="!logado" class="d-flex justify-content-between align-items-center mb-3">
        <RouterLink to="/login" class="marca h4 mb-0 text-decoration-none"><i class="bi bi-car-front-fill me-1"></i>Carona<span>UVV</span></RouterLink>
        <RouterLink to="/login" class="btn btn-sm btn-light">Entrar</RouterLink>
      </div>

      <div :class="{ 'card p-3 p-md-4': !logado }">
        <h1 class="titulo-pagina h3 mb-1">Perguntas frequentes</h1>
        <p class="text-secondary mb-3">Como o CaronaUVV funciona, como protegemos você e como o valor é calculado.</p>

        <label class="visually-hidden" for="faq-busca">Procurar nas perguntas</label>
        <div class="input-group mb-3">
          <span class="input-group-text"><i class="bi bi-search"></i></span>
          <input id="faq-busca" v-model.trim="busca" type="search" class="form-control" placeholder="Procurar (ex.: PIN, Pix, ônibus)" />
        </div>

        <section v-for="grupo in gruposFiltrados" :key="grupo.titulo" class="mb-4">
          <h2 class="h6 fw-bold text-uppercase text-secondary mb-2"><i :class="['bi me-1', grupo.icone]"></i>{{ grupo.titulo }}</h2>
          <div class="accordion">
            <div v-for="item in grupo.itens" :key="item.id" class="accordion-item">
              <h3 class="accordion-header">
                <button
                  :id="`faq-b-${item.id}`" type="button"
                  :class="['accordion-button', { collapsed: !aberto(item.id) }]"
                  :aria-expanded="aberto(item.id)" :aria-controls="`faq-r-${item.id}`"
                  @click="alternar(item.id)"
                >
                  {{ item.pergunta }}
                </button>
              </h3>
              <div
                v-show="aberto(item.id)" :id="`faq-r-${item.id}`" class="accordion-collapse"
                role="region" :aria-labelledby="`faq-b-${item.id}`"
              >
                <div class="accordion-body small">
                  <p v-for="(paragrafo, i) in item.resposta" :key="i" :class="i === item.resposta.length - 1 ? 'mb-0' : 'mb-2'">{{ paragrafo }}</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <p v-if="!gruposFiltrados.length" class="text-secondary">Nenhuma pergunta com "{{ busca }}". Tente outra palavra.</p>

        <div class="alert alert-light border small mb-0">
          <i class="bi bi-life-preserver me-1"></i>Não achou a resposta? Fale com a administração pelo e-mail institucional da UVV.
          Em emergência, ligue <a href="tel:190" class="fw-bold">190</a>.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { logado } from '../stores/auth'
import { normalizar } from '../utils/bairros'

// ==========================================================
// Perguntas frequentes (pagina publica). Acordeao do Bootstrap
// controlado pelo Vue (sem o JavaScript do Bootstrap), com
// aria-expanded/aria-controls para leitores de tela.
// Os numeros (30 min, 15 min, R$ 5,00...) sao os padroes do painel.
// ==========================================================
interface Pergunta {
  id: string
  pergunta: string
  resposta: string[]
}
interface Grupo {
  titulo: string
  icone: string
  itens: Pergunta[]
}

const GRUPOS: Grupo[] = [
  {
    titulo: 'Como funciona', icone: 'bi-info-circle', itens: [
      { id: 'o-que-e', pergunta: 'O que é o CaronaUVV?', resposta: [
        'Uma plataforma de caronas solidárias só para alunos da UVV: quem vai de carro oferece as vagas e quem precisa pede uma vaga, dividindo apenas o custo do combustível.'] },
      { id: 'pedir-vaga', pergunta: 'Como eu peço uma vaga?', resposta: [
        'Em Buscar caronas, filtre pelo seu bairro, sentido (ida ou volta) e horário e toque em "Pedir vaga". O motorista recebe o pedido na hora.',
        'Quando ele aceitar, o telefone dele e o seu PIN de embarque aparecem em Meus pedidos.'] },
      { id: '30-min', pergunta: 'Quanto tempo o motorista tem para responder?', resposta: [
        '30 minutos. Na tela aparece a contagem regressiva. Se ele não responder, o pedido expira, você é avisado e pode pedir outra carona.',
        'Se a carona sai em menos tempo, o prazo vai até 2 horas antes da saída (ou até a saída, se já estiver perto).'] },
      { id: 'pedir-carona', pergunta: 'Não achei carona. O que faço?', resposta: [
        'Use "Pedir carona": diga o bairro, o dia e a faixa de horário. Você entra numa fila por ordem de chegada (até 3 pedidos abertos).',
        'Quando um motorista oferecer carona compatível, você é avisado. Nos primeiros 15 minutos só quem estava na fila consegue pedir a vaga; se a carona tem reserva automática, as vagas ficam guardadas para os primeiros da fila. Quem faltou numa viagem nos últimos 30 dias perde a prioridade.'] },
      { id: 'onibus', pergunta: 'O app mostra horário de ônibus?', resposta: [
        'Não mostramos horário de ônibus porque o Transcol não publica esses dados de forma aberta. Em "Que horas você vai sair?" sugerimos as linhas que costumam servir o seu trajeto até a UVV, marcadas como estimativa, com o link para os horários oficiais (aplicativo ÔnibusGV ou gvbus.org.br).'] },
      { id: 'bairro', pergunta: 'Por que o campo Bairro não aceita "Rua..."?', resposta: [
        'O bairro é usado para achar caronas perto de você. A rua vai no campo de rua/endereço. Ao digitar, o app sugere todos os bairros da Grande Vitória, sem precisar de acento; também dá para preencher pelo CEP.'] }
    ]
  },
  {
    titulo: 'Segurança', icone: 'bi-shield-check', itens: [
      { id: 'quem-usa', pergunta: 'Quem pode usar?', resposta: [
        'Só quem confirma um e-mail institucional @uvv.br. Contas podem ser suspensas pela administração depois de denúncias.'] },
      { id: 'documentos', pergunta: 'O que são os documentos verificados? Vocês guardam minha identidade?', resposta: [
        'Você pode enviar a identidade (passageiro) e a CNH (motorista) para ganhar o selo de verificado. A administração confere e a imagem é apagada logo depois da análise; fica guardado só o resultado (aprovado/recusado e a validade), seguindo a LGPD.'] },
      { id: 'pin', pergunta: 'Para que serve o PIN de embarque?', resposta: [
        'É um código de 4 números que só você vê. Ao entrar no carro, fale o PIN para o motorista digitar: isso garante que você entrou no carro certo e registra a hora (e, se o celular permitir, o local) de entrada. Na saída, toque em "Desembarquei".'] },
      { id: 'familia', pergunta: 'Como a minha família acompanha a viagem?', resposta: [
        'Em "Compartilhar viagem" você gera um link para mandar a quem quiser. Ele mostra o motorista, o carro, a placa e o trajeto no mapa enquanto a viagem acontece, e para de funcionar quando ela termina.'] },
      { id: 'emergencia', pergunta: 'E se algo der errado durante a viagem?', resposta: [
        'Use o botão "Emergência": ele avisa a administração na hora (com a sua localização, se permitir) e oferece ligar para o 190. Se o carro ficar parado fora da rota, o app pergunta se está tudo bem.'] },
      { id: '2fa', pergunta: 'Como deixar minha conta mais protegida?', resposta: [
        'Em Meu perfil, ligue a verificação em duas etapas com um aplicativo autenticador. Guarde os códigos de reserva em lugar seguro.'] },
      { id: 'privacidade', pergunta: 'Quem vê meu telefone e a placa do carro?', resposta: [
        'Ninguém antes do aceite. O telefone do motorista e a placa só aparecem para passageiros com vaga confirmada; o telefone do passageiro só aparece para o motorista depois que ele aceita. As trilhas de GPS são apagadas depois de 30 dias.'] },
      { id: 'avaliacao', pergunta: 'Como funcionam as avaliações?', resposta: [
        'Depois da viagem, motorista e passageiro se avaliam. É "às cegas": a nota só aparece quando os dois avaliarem (ou depois de 7 dias), para ninguém avaliar por vingança.'] },
      { id: 'denunciar', pergunta: 'Como denuncio alguém?', resposta: [
        'No perfil da pessoa, toque em "Denunciar". Só dá para denunciar quem dividiu uma carona com você, para evitar denúncias falsas. A administração analisa e pode suspender a conta.'] }
    ]
  },
  {
    titulo: 'Valor e pagamento', icone: 'bi-cash-coin', itens: [
      { id: 'valor', pergunta: 'Como o valor da carona é calculado?', resposta: [
        'É só para dividir o combustível: distância ÷ consumo do carro = litros (ou kWh no elétrico); litros × preço = custo da viagem; o custo é dividido entre o motorista e as vagas. O motorista pode somar um pequeno adicional.',
        'O passageiro vê a conta aberta. Ninguém pode cobrar mais que R$ 5,00 por pessoa (o teto do painel).'] },
      { id: 'transito', pergunta: 'Por que a conta tem "trânsito"?', resposta: [
        'No horário de pico (dia útil, 6h30–8h30 e 17h–19h30) o anda-e-para gasta mais combustível: a conta soma 25% ao consumo e mais 10% por trecho crítico escolhido (Terceira Ponte, Segunda Ponte, Rodovia do Sol, BR-101/Carapina), até 50%. Fora do pico não há acréscimo. É uma estimativa por horário, não trânsito em tempo real.'] },
      { id: 'pix', pergunta: 'Como eu pago?', resposta: [
        'Pelo Pix copia e cola gerado no app com a chave do motorista, ou em dinheiro. Você marca que pagou e o motorista confirma.'] }
    ]
  }
]

const busca = ref('')
const abertos = reactive(new Set<string>(['o-que-e']))

const gruposFiltrados = computed<Grupo[]>(() => {
  const termo = normalizar(busca.value)
  if (!termo) return GRUPOS
  return GRUPOS.map((g) => ({
    ...g,
    itens: g.itens.filter((i) => normalizar(`${i.pergunta} ${i.resposta.join(' ')}`).includes(termo))
  })).filter((g) => g.itens.length)
})

// Procurando: as respostas encontradas ja aparecem abertas
const aberto = (id: string): boolean => Boolean(busca.value) || abertos.has(id)

function alternar(id: string): void {
  if (busca.value) busca.value = ''
  if (abertos.has(id)) abertos.delete(id)
  else abertos.add(id)
}
</script>
