"""
CALCULO DO RATEIO PELO COMBUSTIVEL

Quanto cada pessoa paga por uma carona, com a conta aberta:

    distancia (em metros)  ->  km  ->  litros (ou kWh no carro eletrico)
    litros x preco do litro  =  custo do combustivel da viagem
    custo / ocupantes (motorista + vagas)  =  combustivel por pessoa
    combustivel por pessoa + adicional do motorista  =  valor por passageiro

- A distancia chega em km com ate 3 casas (precisao de metro): 6,2 km = 6.200 m.
- Carro flex e hibrido usam o preco da gasolina; diesel, etanol e eletrico, o proprio.
- Sem o consumo do carro, usa a media de um carro popular daquele tipo
  (e avisa que e estimativa).
- Toda a conta usa Decimal (dinheiro nao pode ter erro de arredondamento de float)
  e so arredonda no fim, para centavos.
"""
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal

from caronauvv.admin.models import Configuracao
from caronauvv.errors import ApiError

CENTAVO = Decimal("0.01")

# Preco de cada energia: chave da configuracao do painel
PRECO_POR_ENERGIA = {
    "gasolina": "preco_gasolina",
    "flex": "preco_gasolina",      # o motorista informa o consumo com gasolina
    "hibrido": "preco_gasolina",   # hibrido comum: abastece gasolina e gasta menos
    "etanol": "preco_etanol",
    "diesel": "preco_diesel",
    "eletrico": "preco_kwh",
}

# Consumo medio quando o carro nao tem o consumo cadastrado (km/l; eletrico em km/kWh)
CONSUMO_MEDIO = {
    "gasolina": 12.0,
    "flex": 12.0,
    "etanol": 8.5,
    "diesel": 13.0,
    "hibrido": 18.0,
    "eletrico": 6.5,
}

NOMES = {
    "gasolina": "Gasolina", "flex": "Flex (gasolina)", "etanol": "Etanol",
    "diesel": "Diesel", "hibrido": "Híbrido (gasolina)", "eletrico": "Elétrico",
}


@dataclass
class Rateio:
    energia: str
    unidade: str                  # "L" ou "kWh"
    distancia_m: int              # distancia em metros (inteiro)
    distancia_km: Decimal
    consumo_km: Decimal           # km por litro (ou por kWh)
    consumo_estimado: bool        # True quando usou a media do tipo de carro
    quantidade: Decimal           # litros ou kWh gastos na viagem
    preco_unidade: Decimal        # R$ por litro ou por kWh
    custo_total: Decimal          # combustivel da viagem inteira
    ocupantes: int                # motorista + vagas
    combustivel_por_pessoa: Decimal
    adicional: Decimal
    valor_por_passageiro: Decimal

    def to_dict(self) -> dict:
        dados = asdict(self)
        for chave, valor in dados.items():
            if isinstance(valor, Decimal):
                dados[chave] = float(valor)
        dados["energia_nome"] = NOMES[self.energia]
        return dados


def _decimal(valor, campo: str) -> Decimal:
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except Exception:
        raise ApiError(f"{campo}: precisa ser um número.", campos={campo: "Precisa ser um número."})
    if not numero.is_finite():
        raise ApiError(f"{campo}: precisa ser um número.", campos={campo: "Precisa ser um número."})
    return numero


def calcular_rateio(distancia_km, vagas: int, energia: str = "flex", consumo_km=None, adicional=0) -> Rateio:
    """Conta completa do rateio. Levanta ApiError com o campo errado quando um dado nao serve."""
    if energia not in PRECO_POR_ENERGIA:
        raise ApiError("Tipo de energia inválido.", campos={"energia": "Escolha gasolina, etanol, flex, diesel, híbrido ou elétrico."})
    if not 1 <= int(vagas) <= 6:
        raise ApiError("As vagas vão de 1 a 6.", campos={"vagas": "De 1 a 6 vagas."})

    distancia_m = int((_decimal(distancia_km, "distancia_km") * 1000).to_integral_value(rounding=ROUND_HALF_UP))
    if not 0 < distancia_m <= 500_000:
        raise ApiError("Informe a distância (até 500 km).", campos={"distancia_km": "Informe a distância (até 500 km)."})

    estimado = consumo_km in (None, "", 0)
    consumo = Decimal(str(CONSUMO_MEDIO[energia])) if estimado else _decimal(consumo_km, "consumo_km")
    if not 0 < consumo <= 60:
        raise ApiError("O consumo vai de 0,1 a 60 km por litro (ou kWh).", campos={"consumo_km": "Entre 0,1 e 60."})

    extra = _decimal(adicional or 0, "adicional")
    if extra < 0:
        raise ApiError("O adicional não pode ser negativo.", campos={"adicional": "Não pode ser negativo."})

    preco = Configuracao.obter_decimal(PRECO_POR_ENERGIA[energia], "0")
    km = Decimal(distancia_m) / 1000
    quantidade = km / consumo
    custo_total = quantidade * preco
    ocupantes = int(vagas) + 1
    por_pessoa = (custo_total / ocupantes).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    extra = extra.quantize(CENTAVO, rounding=ROUND_HALF_UP)

    return Rateio(
        energia=energia,
        unidade="kWh" if energia == "eletrico" else "L",
        distancia_m=distancia_m,
        distancia_km=km,
        consumo_km=consumo,
        consumo_estimado=estimado,
        quantidade=quantidade.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        preco_unidade=preco,
        custo_total=custo_total.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        ocupantes=ocupantes,
        combustivel_por_pessoa=por_pessoa,
        adicional=extra,
        valor_por_passageiro=por_pessoa + extra,
    )
