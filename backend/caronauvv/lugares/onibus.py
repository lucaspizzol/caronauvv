"""
ONIBUS ATE A UVV (ESTIMATIVA, NAO E HORARIO OFICIAL)

Estudo de fontes (23/11/2026):
- O Transcol (Ceturb-ES / GVBus) NAO publica GTFS nem API aberta de horarios. Os horarios
  oficiais ficam no aplicativo ONIBUSGV e no site gvbus.org.br (sem dados abertos).
- O OpenStreetMap tem uma lista colaborativa das linhas ("Brazil/ES/Onibus/Lista", wiki
  editada em 03/2024 e marcada como "trabalho em progresso"). Dela vieram os NUMEROS e
  NOMES abaixo, copiados como estao. Desde 31/10/2026 as linhas municipais de Vila Velha
  passaram para o Transcol, entao a lista pode estar desatualizada.

Por isso o sistema NUNCA mostra horario: so sugere quais linhas costumam servir o trajeto
e manda o aluno conferir o horario no app oficial. A posicao dos terminais e aproximada
(centro do bairro onde cada terminal fica).
"""
from .services import achar_bairro, haversine_km, normalizar

FONTE = "Lista colaborativa de linhas do OpenStreetMap (wiki, 03/2024), conferida em 23/11/2026"
LINK_OFICIAL = "https://www.gvbus.org.br"
AVISO = ("Estimativa: o Transcol não publica horários em dados abertos. Confira o horário e o itinerário "
         "no aplicativo ÔnibusGV ou em gvbus.org.br antes de sair.")

# Linhas que passam pela Boa Vista / UVV (numero, nome como esta na fonte, noturna?)
LINHAS_UVV = (
    ("608", "T. IBES / BOA VISTA VIA SOTECO", False),
    ("606", "T. VILA VELHA/T. IBES VIA C.ITAPARICA/SANTA INÊS", False),
    ("1721", "Shopping Moxuara/U.V.V via Bela Aurora", False),
    ("664", "T. SÃO TORQUATO / T. VILA VELHA VIA BOA VISTA/P. COSTA CIRCULAR - NOTURNO", True),
)

# Outras linhas da lista (para achar a que sai do bairro do aluno ate um terminal)
LINHAS = (
    ("500", "Terminal Vila Velha/Terminal Itacibá"),
    ("503", "Terminal Laranjeiras / Terminal Vila Velha"),
    ("507", "T. LARANJEIRAS / T. IBES VIA 3ª PONTE/RETA DA PENHA"),
    ("510", "T. CARAPINA / T. VILA VELHA VIA 3º PONTE"),
    ("514", "T. IBES / T. VILA VELHA VIA 3ª PONTE/BEIRA MAR"),
    ("518", "T. CARAPINA / T. IBES VIA SERAFIM DERENZI"),
    ("520", "T. CARAPINA / T. VILA VELHA VIA RETA DA PENHA/3ª PONTE"),
    ("525", "T. VILA VELHA / T. ITACIBÁ VIA LINDENBERG/T. IBES/T. JARDIM AMÉRICA"),
    ("526", "T. CAMPO GRANDE / T. VILA VELHA VIA VASCO DA GAMA/EXPEDITO GARCIA"),
    ("531", "T .CAMPO GRANDE / T. VILA VELHA VIA MARUÍPE"),
    ("550", "SHOPPING VITÓRIA / T. VILA VELHA - VIA 3ª PONTE"),
    ("580", "PADRE GABRIEL / T. IBES VIA JARDIM PALMARES/COBILANDIA"),
    ("586", "VISTA LINDA / T. IBES VIA COBILANDIA"),
    ("590", "BANDEIRANTES / T. IBES VIA JARDIM MARILÂNDIA"),
    ("600", "T. ITAPARICA / T. IBES VIA ARAÇAS"),
    ("601", "T. IBES / SANTOS DUMONT"),
    ("603", "T. ITAPARICA / T. IBES VIA COLORADO"),
    ("604", "T. IBES / T. SÃO TORQUATO VIA SANTA RITA/ALVORADA"),
    ("605", "T. VILA VELHA / T. IBES VIA C.ITAPARICA/NOVO MEXICO"),
    ("607", "Glória/Terminal Ibes"),
    ("609", "T. ITAPARICA / BARRA DO JUCU"),
    ("610", "T. ITAPARICA / T. VILA VELHA VIA JÓQUEI DE ITAPARICA"),
    ("611", "T. ITAPARICA / PRAIA DA COSTA VIA ITAPOÃ/CREFES"),
    ("613", "PONTA DA FRUTA / T. ITAPARICA VIA ROD. DO SOL"),
    ("615", "T. VILA VELHA / PRAIA DE ITAPOÃ"),
    ("616", "MORADA DA BARRA / T. ITAPARICA VIA BARRAMARES"),
    ("617", "JOÃO GOULART / T. ITAPARICA VIA AV. CALIFÓRNIA"),
    ("618", "T. ITAPARICA / SÃO CONRADO"),
    ("625", "T. IBES / T. SÃO TORQUATO VIA ATAÍDE/SANTA RITA"),
    ("633", "T. IBES / T. SÃO TORQUATO VIA PLANALTO/ALVORADA"),
    ("635", "T. VILA VELHA / PRAINHA"),
    ("636", "T. VILA VELHA / T. ITAPARICA - VIA SANTA MONICA/SOTECO"),
    ("650", "T. VILA VELHA / T. IBES VIA PRAIA DE ITAPOÃ"),
    ("651", "T. VILA VELHA / PRAIA DA COSTA"),
    ("656", "T. ITAPARICA / T. VILA VELHA"),
    ("658", "T. IBES / T. SÃO TORQUATO VIA ARIBIRI/PAUL"),
    ("660", "T. ITAPARICA / T. SÃO TORQUATO VIA VILA GARRIDO"),
    ("662", "T. VILA VELHA / PRAIA DA COSTA VIA CREFES - CIRCULAR"),
)

# Terminais e o bairro onde ficam (posicao aproximada pelo centro do bairro)
TERMINAIS = {
    "T. Vila Velha": "Divino Espírito Santo",
    "T. Ibes": "Ibes",
    "T. Itaparica": "Praia de Itaparica",
    "T. São Torquato": "São Torquato",
    "T. Campo Grande": "Campo Grande",
    "T. Itacibá": "Itacibá",
    "T. Jardim América": "Jardim América",
    "T. Carapina": "Carapina",
    "T. Laranjeiras": "Parque Residencial Laranjeiras",
    "T. Jacaraípe": "Parque Jacaraípe",
}
# Terminais de onde sai linha que passa pela UVV
TERMINAL_LIGA_UVV = {"T. Ibes": "608", "T. Vila Velha": "606"}

# A fonte abrevia nomes: o que procurar no nome da linha para cada bairro
APELIDOS = {
    "itapua": ("itapoa", "itapua"), "praia de itapua": ("itapoa",), "praia da costa": ("praia da costa", "p. costa"),
    "coqueiral de itaparica": ("c.itaparica", "c. itaparica"), "jockey de itaparica": ("joquei de itaparica",),
    "gloria": ("gloria",), "santa ines": ("santa ines",), "soteco": ("soteco",), "cobilandia": ("cobilandia",),
}


def _noturna(hora: int) -> bool:
    return hora >= 23 or hora < 5


def _linhas_do_bairro(bairro: str) -> list[dict]:
    chave = normalizar(bairro)
    termos = APELIDOS.get(chave, (chave,))
    achadas = [{"numero": n, "nome": nome} for n, nome in LINHAS
               if any(t in normalizar(nome) for t in termos)]
    return achadas[:6]


def _cita_terminal(nome_linha: str, terminal: str) -> bool:
    """A fonte escreve "T. IBES", "T.IBES" ou "Terminal Ibes"."""
    lugar = normalizar(terminal.removeprefix("T. "))
    nome = normalizar(nome_linha).replace("terminal ", "t. ").replace("t.", "t. ").replace("t.  ", "t. ")
    return f"t. {lugar}" in nome


def _terminal_proximo(lat: float, lng: float) -> dict:
    melhor = None
    for terminal, bairro in TERMINAIS.items():
        b = achar_bairro(bairro)
        if b is None:
            continue
        km = haversine_km(lat, lng, b["lat"], b["lng"])
        if melhor is None or km < melhor["distancia_km"]:
            melhor = {"nome": terminal, "distancia_km": round(km, 1)}
    return melhor


def recomendar_onibus(bairro: str, sentido: str = "ida", hora: int = 7) -> dict | None:
    """Sugestao de onibus entre o bairro e a UVV (sem horario: so linhas e caminho)."""
    achado = achar_bairro(bairro)
    if achado is None:
        return None
    noite = _noturna(hora)
    linhas_uvv = [{"numero": n, "nome": nome, "noturna": noturna}
                  for n, nome, noturna in LINHAS_UVV if noturna == noite]
    do_bairro = _linhas_do_bairro(achado["nome"])
    terminal = _terminal_proximo(achado["lat"], achado["lng"])

    # Escolhe o terminal de troca: o que aparece numa linha do bairro e tem ligacao com a UVV
    troca = next((t for t in TERMINAL_LIGA_UVV for linha in do_bairro if _cita_terminal(linha["nome"], t)), None)
    if troca is None and terminal and terminal["nome"] in TERMINAL_LIGA_UVV:
        troca = terminal["nome"]
    troca = troca or "T. Ibes"

    perto = achado["distancia_uvv_km"] <= 3
    if perto:
        caminho = (f"{achado['nome']} fica a uns {str(achado['distancia_uvv_km']).replace('.', ',')} km da UVV: dá para ir a pé ou "
                   "de bicicleta, ou pegar uma linha que passa pela Boa Vista.")
    elif sentido == "ida":
        caminho = (f"Do bairro, pegue uma linha até o {troca} e, de lá, a {TERMINAL_LIGA_UVV[troca]} "
                   "até a Boa Vista (UVV).")
    else:
        caminho = (f"Da UVV, pegue a {TERMINAL_LIGA_UVV[troca]} até o {troca} e, de lá, uma linha para "
                   f"{achado['nome']}.")
    if noite:
        caminho += " À noite (23h às 5h) circulam só as linhas noturnas; o intervalo costuma ser maior."

    return {
        "bairro": achado["nome"], "sentido": sentido, "hora": hora, "estimativa": True,
        "caminho": caminho, "terminal_troca": None if perto else troca, "terminal_mais_proximo": terminal,
        "linhas_ate_uvv": linhas_uvv, "linhas_do_bairro": do_bairro,
        "aviso": AVISO, "fonte": FONTE, "link_oficial": LINK_OFICIAL,
    }
