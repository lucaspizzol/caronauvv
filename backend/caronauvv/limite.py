"""
LIMITE DE REQUISICOES (rate limit) simples, em memoria

Usado nas rotas que podem ser chamadas muitas vezes (sugestao de bairro enquanto
digita, CEP, pedir carona). Conta as chamadas por usuario logado (ou IP) numa janela
de tempo; passou do limite, responde 429. Em memoria por processo: no servidor sem
estado (Vercel) cada instancia conta separado, o que ainda freia abuso de um cliente.
"""
import time
from collections import defaultdict, deque
from functools import wraps
from threading import Lock

from flask import current_app, g, request

from caronauvv.errors import ApiError

_chamadas: dict[str, deque] = defaultdict(deque)
_trava = Lock()


def _chave(nome: str) -> str:
    usuario = getattr(g, "usuario", None)
    quem = f"u{usuario.id}" if usuario is not None else f"ip{request.remote_addr}"
    return f"{nome}:{quem}"


def limitar(maximo: int, janela_seg: int = 60):
    """Decorator: no maximo `maximo` chamadas por `janela_seg` segundos por usuario/IP.
    Use DEPOIS do @login_required, para contar por usuario."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_app.config.get("RATE_LIMIT_DESLIGADO"):
                agora = time.monotonic()
                with _trava:
                    fila = _chamadas[_chave(func.__name__)]
                    while fila and fila[0] <= agora - janela_seg:
                        fila.popleft()
                    if len(fila) >= maximo:
                        raise ApiError("Muitas requisições seguidas. Aguarde um pouco e tente de novo.", 429)
                    fila.append(agora)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def zerar() -> None:
    """Usado nos testes."""
    with _trava:
        _chamadas.clear()
