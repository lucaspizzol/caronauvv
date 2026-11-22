from functools import wraps

from flask import g, request

from caronauvv.errors import ApiError

from .services import usuario_do_token


def login_required(view):
    """
    Exige o cabecalho "Authorization: Bearer <token>".
    O usuario logado fica disponivel em g.usuario dentro da rota.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        tipo, _, token = request.headers.get("Authorization", "").partition(" ")
        if tipo.lower() != "bearer" or not token:
            raise ApiError("Faça login para continuar.", 401)
        g.usuario = usuario_do_token(token)
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    """Como login_required, mas so deixa passar administradores (painel /admin)."""

    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.usuario.is_admin:
            raise ApiError("Área restrita à administração.", 403)
        return view(*args, **kwargs)

    return wrapper
