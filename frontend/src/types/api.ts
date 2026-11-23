// ==========================================================
// Formato dos dados que a API Flask devolve (JSON).
// Cada interface espelha um to_dict() do back-end:
//   Usuario            -> auth/models.py  Usuario.to_dict()
//   Carona             -> caronas/models.py  Carona.to_dict()
//   Solicitacao        -> caronas/models.py  Solicitacao.to_dict()
//   Reputacao          -> avaliacoes/services.py  _calcular_reputacao()
//   Avaliacao/Pagamento-> avaliacoes/models.py
//   Notificacao        -> notificacoes/models.py
//   Alerta/Denuncia    -> seguranca/models.py
// Datas chegam como texto ISO "AAAA-MM-DDTHH:MM" no horario local.
// ==========================================================

export type DataIso = string

// ---------------- usuarios ----------------
export type NivelConversa = 'quieto' | 'depende' | 'conversador'

export interface Preferencias {
  conversa: NivelConversa
  musica: boolean
  animais: boolean
  fumar: boolean
}

export interface Selo {
  codigo:
    | 'email_uvv'
    | 'perfil_verificado'
    | 'identidade_verificada'
    | 'cnh_verificada'
    | 'pontual'
    | 'bem_avaliado'
    | 'sem_faltas'
  texto: string
}

export type Nivel = 'Calouro' | 'Veterano' | 'Embaixador' | (string & {})

export interface Reputacao {
  nota_media: number | null
  total_avaliacoes: number
  tags: { tag: string; total: number }[]
  viagens_motorista: number
  viagens_passageiro: number
  faltas: number
  taxa_cancelamento: number
  nivel: Nivel
  selos: Selo[]
}

/** Dados publicos de qualquer aluno (perfil publico, cartoes da busca). */
export interface Usuario {
  id: number
  nome: string
  curso: string | null
  bairro: string
  foto_url: string | null
  verificado: boolean
  email_verificado: boolean
  identidade_verificada: boolean // documento conferido pela administracao
  cnh_verificada: boolean
  bio: string | null
  preferencias: Preferencias
  membro_desde: string | null
  reputacao?: Reputacao
  // Dados de contato: so chegam para quem pode ver (dono da conta, carona aceita)
  matricula?: string
  email?: string
  telefone?: string
  endereco?: string | null
  chave_pix?: string | null
  is_admin?: boolean
  dois_fatores?: boolean
  verificacao_solicitada_em?: DataIso | null
}

/** O proprio usuario logado (GET /api/auth/me): sempre vem com os dados privados. */
export interface UsuarioLogado extends Usuario {
  matricula: string
  email: string
  telefone: string
  is_admin: boolean
  dois_fatores: boolean
}

/** Avatar so precisa do nome e da foto: serve para qualquer forma reduzida de usuario. */
export type PessoaComFoto = Pick<Usuario, 'nome'> & Partial<Pick<Usuario, 'foto_url'>>

/** Energia do carro: define o preco usado no calculo do combustivel. */
export type Energia = 'gasolina' | 'etanol' | 'flex' | 'diesel' | 'hibrido' | 'eletrico'

export interface Veiculo {
  id: number
  modelo: string
  cor: string
  placa?: string
  energia: Energia
  consumo_km: number | null // km por litro (eletrico: km por kWh)
}

export interface ContatoConfianca {
  id: number
  nome: string
  telefone: string
}

// ---------------- caronas ----------------
export type Sentido = 'ida' | 'volta'
export type StatusCarona = 'ativa' | 'lotada' | 'em_andamento' | 'concluida' | 'cancelada'
export type StatusSolicitacao = 'pendente' | 'aceita' | 'recusada' | 'cancelada' | 'expirada'

export interface Carona {
  id: number
  sentido: Sentido
  bairro_origem: string
  endereco_origem: string | null
  destino: string
  origem_lat: number | null
  origem_lng: number | null
  distancia_km: number | null
  duracao_min: number | null
  data_hora_saida: DataIso
  vagas: number
  vagas_restantes: number
  valor_por_passageiro: number
  reserva_automatica: boolean
  prioridade_ate: DataIso | null // fila do Pedir carona: ate esta hora so quem estava na fila pede vaga
  observacoes: string | null
  status: StatusCarona
  iniciada_em: DataIso | null
  concluida_em: DataIso | null
  motorista: Usuario & { reputacao: Reputacao }
  veiculo: Veiculo | null
  rateio: RateioCarona | null // como o valor foi composto (nulo se o motorista digitou o valor)
}

/** Detalhamento do valor guardado na carona: combustivel + adicional = valor por passageiro. */
export interface RateioCarona {
  energia: Energia
  consumo_km: number | null
  combustivel: number
  adicional: number
  transito_percentual: number // acrescimo no consumo pelo transito (horario de pico + trechos)
  trechos_transito: TrechoTransito[]
}

/** Trechos criticos de transito da Grande Vitoria (caronas/combustivel.py: TRECHOS). */
export type TrechoTransito = 'terceira_ponte' | 'segunda_ponte' | 'rodovia_do_sol' | 'br101_carapina'

/** GET /api/caronas/valor-sugerido com energia: a conta completa (caronas/combustivel.py). */
export interface CalculoRateio {
  energia: Energia
  energia_nome: string
  unidade: 'L' | 'kWh'
  distancia_m: number
  distancia_km: number
  consumo_km: number
  consumo_estimado: boolean
  quantidade: number
  preco_unidade: number
  custo_total: number
  ocupantes: number
  combustivel_por_pessoa: number
  adicional: number
  valor_por_passageiro: number
  transito_percentual: number
  transito_motivos: string[]
  quantidade_sem_transito: number
}

export interface RespostaValorSugerido {
  valor_sugerido: number
  teto: number
  acima_do_teto?: boolean
  calculo?: CalculoRateio
}

// ---------------- documentos (identidade e CNH) ----------------
export type TipoDocumento = 'identidade' | 'cnh'
export type StatusDocumento = 'nao_enviado' | 'pendente' | 'aprovado' | 'recusado'

export interface Documento {
  id?: number
  tipo: TipoDocumento
  status: StatusDocumento
  validade?: string | null // AAAA-MM-DD (CNH)
  vencido?: boolean
  tem_imagem?: boolean // false depois da analise: a imagem e apagada (LGPD)
  motivo_recusa?: string | null
  enviado_em?: DataIso | null
  analisado_em?: DataIso | null
}

/** Documento na fila do painel, com quem enviou. */
export interface DocumentoAdmin extends Documento {
  id: number
  usuario: { id: number; nome: string; matricula: string; email: string; foto_url: string | null }
}

export interface Pagamento {
  id: number
  valor: number
  metodo: string
  status: string
  pix_copia_cola: string | null
  pago_em: DataIso | null
}

export interface Solicitacao {
  id: number
  carona_id: number
  status: StatusSolicitacao
  endereco_embarque: string | null
  mensagem: string | null
  desvio_min: number | null
  criada_em: DataIso | null
  respondida_em: DataIso | null
  expira_em: DataIso | null
  passageiro: Usuario & { reputacao: Reputacao }
  embarcou_em: DataIso | null
  desembarcou_em: DataIso | null
  faltou: boolean
  pagamento: Pagamento | null
  ja_avaliei?: boolean
  pin_embarque?: string
}

// ---------------- avaliacoes ----------------
export type Papel = 'motorista' | 'passageiro'

export interface Avaliacao {
  id: number
  nota: number
  comentario: string | null
  tags: string[]
  avaliador: { id: number; nome: string; foto_url: string | null }
  papel_avaliado: Papel
  criada_em: DataIso
}

// ---------------- notificacoes e seguranca ----------------
export interface Notificacao {
  id: number
  tipo: string
  titulo: string
  texto: string
  carona_id: number | null
  lida: boolean
  criada_em: DataIso
}

export interface Alerta {
  id: number
  carona_id: number | null
  usuario: Usuario | null
  tipo: string
  detalhe: string | null
  lat: number | null
  lng: number | null
  resposta: string | null
  status: string
  criado_em: DataIso
  resolvido_em: DataIso | null
}

export interface Denuncia {
  id: number
  denunciante: Usuario
  denunciado: Usuario & { is_active: boolean }
  carona_id: number | null
  motivo: string
  descricao: string | null
  status: string
  resolucao: string | null
  criada_em: DataIso
  encerrada_em: DataIso | null
}

export interface LinkCompartilhado {
  token: string
  carona_id: number
  expira_em: DataIso
  ativo: boolean
  acessos: number
}

// ---------------- respostas comuns ----------------
/** Login e cadastro devolvem o token e o usuario (ou o desafio da segunda etapa). */
export interface RespostaSessao {
  token: string
  usuario: UsuarioLogado
  codigo_dev?: string
}

/** Erro de formulario por campo: { email: 'E-mail inválido.' } */
export type ErrosCampos = Record<string, string>

// ---------------- telas especificas ----------------
/** GET /api/solicitacoes/minhas: cada pedido vem com a carona junto. */
export interface SolicitacaoComCarona extends Solicitacao {
  carona: Carona
}

/** GET /api/usuarios/<id> (perfil publico com reputacao). */
export interface PerfilPublico extends Usuario {
  reputacao: Reputacao
  avaliacoes: Avaliacao[]
  veiculos: Veiculo[]
}

/** GET /api/avaliacoes/pendentes */
export interface AvaliacaoPendente {
  solicitacao_id: number
  papel_avaliado: Papel
  avaliado: { id: number; nome: string; curso: string | null; foto_url: string | null }
  carona: Pick<Carona, 'id' | 'sentido' | 'bairro_origem' | 'destino' | 'data_hora_saida'>
  tags_sugeridas: string[]
}

/** GET /api/acompanhar/<token> (link da familia, sem login). */
export interface ViagemAcompanhada {
  compartilhado_por: string
  status: StatusCarona
  sentido: Sentido
  origem: string
  destino: string
  data_hora_saida: DataIso
  iniciada_em: DataIso | null
  motorista: { nome: string; curso: string | null; verificado: boolean; foto_url: string | null }
  veiculo: Veiculo | null
  ultima_posicao: { lat: number; lng: number; em: DataIso } | null
  trilha: [number, number][]
  expira_em: DataIso
}

// ---------------- painel da administracao ----------------
export interface UsuarioAdmin extends UsuarioLogado {
  is_active: boolean
  ultimo_login_em: DataIso | null
  suspenso_em: DataIso | null
  suspenso_motivo: string | null // "Exclusão automática: média 2,0..." ou suspensão pela administração
  media_recebida: number | null // média de TODAS as avaliações recebidas (o admin vê as "às cegas")
  avaliacoes_recebidas: number
}

/** GET /api/admin/resumo */
export interface ResumoAdmin {
  usuarios: {
    total: number
    ativos_30_dias: number
    verificados: number
    suspensos: number
    verificacoes_pendentes: number
    documentos_pendentes: number
  }
  caronas: { total: number; por_status: Partial<Record<StatusCarona, number>> }
  viagens: {
    concluidas: number
    em_andamento_agora: number
    passageiros_transportados: number
    taxa_ocupacao: number
    km_compartilhados: number
    co2_evitado_kg: number
    taxa_faltas: number
  }
  confianca: {
    nota_media: number | null
    avaliacoes: number
    denuncias_abertas: number
    alertas_aguardando: number
    avaliacoes_baixas_abertas: number
    excluidos_automaticamente: number
  }
  medias: MediasViagens
  /** Grafico da visao geral: ultimos 30 dias, do mais antigo para hoje. */
  caronas_por_dia: CaronasDoDia[]
  demanda_sem_oferta: { bairro: string; buscas: number }[]
  bairros_com_mais_oferta: { bairro: string; caronas: number }[]
}

export interface Configuracao {
  chave: string
  valor: string
  descricao: string | null
}

/** GET /api/admin/banco: estrutura lida dos modelos do SQLAlchemy. */
export interface ColunaBanco {
  nome: string
  tipo: string
  pk: boolean
  fk: string | null // "tabela.coluna"
  obrigatorio: boolean
  unico: boolean
}

export interface TabelaBanco {
  nome: string
  linhas: number
  colunas: ColunaBanco[]
}

export interface EstruturaBanco {
  banco: string
  versao_migracao: string | null
  tabelas: TabelaBanco[]
}

// ----------------------------------------------------------
// Lugares (lugares/routes.py): bairros, CEP, ruas e distancia ate a UVV
// ----------------------------------------------------------
export type CidadeGrandeVitoria = 'Vila Velha' | 'Vitória' | 'Cariacica' | 'Serra'

export interface BairroSugestao {
  nome: string
  cidade: CidadeGrandeVitoria
  lat: number
  lng: number
  distancia_uvv_km: number
}

export interface EnderecoCep {
  cep: string
  rua: string
  bairro: string
  cidade: string
  uf: string
}

export interface DistanciaUvv {
  bairro: string
  cidade: CidadeGrandeVitoria
  km: number
  duracao_min: number | null
  metodo: 'osrm' | 'estimativa'
}

// ----------------------------------------------------------
// Pedir carona (caronas/fila.py: pedido_to_dict)
// ----------------------------------------------------------
export type StatusPedidoCarona = 'aberto' | 'atendido' | 'expirado' | 'cancelado'

export interface PedidoCarona {
  id: number
  bairro: string
  sentido: Sentido
  data: string // AAAA-MM-DD
  hora_inicio: string // HH:MM
  hora_fim: string
  status: StatusPedidoCarona
  criado_em: DataIso
  carona_id: number | null
  posicao: number | null // 1 = primeiro da fila (so nos abertos)
  caronas_compativeis: number
  sem_prioridade_por_falta: boolean
}

// Onibus ate a UVV (lugares/onibus.py): ESTIMATIVA, sem horario oficial
export interface LinhaOnibus {
  numero: string
  nome: string
  noturna?: boolean
}

export interface RecomendacaoOnibus {
  bairro: string
  sentido: Sentido
  hora: number
  estimativa: true
  caminho: string
  terminal_troca: string | null
  terminal_mais_proximo: { nome: string; distancia_km: number } | null
  linhas_ate_uvv: LinhaOnibus[]
  linhas_do_bairro: LinhaOnibus[]
  aviso: string
  fonte: string
  link_oficial: string
}

// Resumo da viagem (caronas/viagem.py)
export interface PontoGps {
  lat: number
  lng: number
}

export interface PassageiroResumo {
  solicitacao_id: number
  nome: string
  faltou: boolean
  entrou_em: DataIso | null
  saiu_em: DataIso | null
  entrada: PontoGps | null
  saida: PontoGps | null
  minutos_a_bordo: number | null
  km_a_bordo: number | null
}

export interface ResumoViagem {
  carona_id: number
  status: StatusCarona
  saida_prevista: DataIso
  iniciada_em: DataIso | null
  concluida_em: DataIso | null
  atraso_saida_min: number | null
  duracao_min: number | null
  distancia_km: number | null
  distancia_pela_trilha: boolean
  velocidade_media_kmh: number | null
  trilha: [number, number][]
  passageiros: PassageiroResumo[]
}

export interface MediasViagens {
  viagens_medidas: number
  tempo_medio_viagem_min: number | null
  atraso_medio_saida_min: number | null
  velocidade_media_kmh: number | null
  tempo_medio_a_bordo_min: number | null
}

// ---------------- painel em tempo real (admin/monitor.py) ----------------
export type SituacaoPassageiro = 'aguardando' | 'a_bordo' | 'desembarcou' | 'faltou'

export interface PessoaMonitor {
  id: number
  nome: string
  foto_url: string | null
  telefone: string
  is_active: boolean
}

/** GET /api/admin/viagens: uma viagem acontecendo agora (ou saindo / recém-concluída). */
export interface ViagemAoVivo {
  id: number
  status: StatusCarona
  sentido: Sentido
  bairro_origem: string
  endereco_origem: string | null
  destino: string
  data_hora_saida: DataIso
  iniciada_em: DataIso | null
  concluida_em: DataIso | null
  minutos_em_viagem: number | null
  motorista: PessoaMonitor
  veiculo: Veiculo | null
  passageiros: (PessoaMonitor & { solicitacao_id: number; situacao: SituacaoPassageiro; entrou_em: DataIso | null; saiu_em: DataIso | null })[]
  ultima_posicao: { lat: number; lng: number; em: DataIso; segundos_atras: number } | null
  velocidade_kmh: number | null
  trilha: [number, number][]
  alertas_abertos: number
}

export interface PainelViagens {
  atualizado_em: DataIso
  viagens: ViagemAoVivo[]
  totais: { em_andamento: number; saindo_em_breve: number; concluidas_recentes: number; passageiros_a_bordo: number }
}

/** GET /api/admin/avaliacoes: avaliação vista pelo admin (inclusive as "às cegas"). */
export interface AvaliacaoAdmin {
  id: number
  nota: number
  comentario: string | null
  tags: string[]
  criada_em: DataIso
  revelada: boolean
  papel_avaliado: Papel
  avaliador: { id: number; nome: string; foto_url: string | null }
  avaliado: { id: number; nome: string; foto_url: string | null; is_active: boolean }
  carona: { id: number; bairro_origem: string; destino: string; sentido: Sentido; data_hora_saida: DataIso }
}

export interface UsuarioEmRisco {
  id: number
  nome: string
  foto_url: string | null
  media: number
  avaliacoes: number
  is_active: boolean
  suspenso_motivo: string | null
}

export interface PainelAvaliacoes {
  regras: { nota_alerta: number; media_minima: number; minimo_avaliacoes: number }
  estatisticas: {
    total: number
    media_geral: number | null
    ultimas_24h: number
    distribuicao: Record<'1' | '2' | '3' | '4' | '5', number>
    alertas_abertos: number
  }
  avaliacoes: AvaliacaoAdmin[]
  em_risco: UsuarioEmRisco[]
  excluidos: { id: number; nome: string; foto_url: string | null; suspenso_em: DataIso | null; motivo: string | null; is_active: boolean }[]
}

/** Um dia do grafico "Caronas nos ultimos 30 dias" (pela data de saida). */
export interface CaronasDoDia {
  dia: string // AAAA-MM-DD
  concluidas: number
  canceladas: number
  outras: number // ativas, lotadas ou em andamento
  total: number
}

/** GET /api/admin/historico: uma acao da administracao (admin null = feita pelo sistema). */
export type TipoAcaoAdmin =
  | 'aprovar_selo'
  | 'recusar_selo'
  | 'suspender'
  | 'reativar'
  | 'remover_foto'
  | 'resetar_2fa'
  | 'aprovar_documento'
  | 'recusar_documento'
  | 'analisar_denuncia'
  | 'encerrar_denuncia'
  | 'resolver_alerta'
  | 'alterar_regras'
  | 'exportar_dados'
  | 'exclusao_automatica'

export interface AcaoAdmin {
  id: number
  acao: TipoAcaoAdmin
  admin: { id: number; nome: string } | null
  alvo: { id: number | null; nome: string } | null
  detalhe: string | null
  criado_em: string
}
