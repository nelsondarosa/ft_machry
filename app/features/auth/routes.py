from flask import Blueprint, g, session

from app.features.usuarios.repository import UsuarioRepository
from app.features.usuarios.schemas import UsuarioOut
from app.utils.parsing import entrada

from .schemas import LoginInput
from .services import AuthService

bp = Blueprint("auth", __name__)


def get_service() -> AuthService:
    return AuthService(UsuarioRepository())


def _saida(usuario):
    return UsuarioOut.model_validate(usuario).model_dump()


@bp.post("/login")
def login():
    usuario = get_service().autenticar(entrada(LoginInput))
    if usuario is None:
        return {"erro": "Usuário ou senha inválidos"}, 401
    session.clear()
    session["usuario_id"] = usuario.id
    session.permanent = True
    return _saida(usuario)


@bp.post("/logout")
def logout():
    session.clear()
    return "", 204


@bp.get("/me")
def me():
    if not getattr(g, "usuario", None):
        return {"erro": "Autenticação necessária"}, 401
    return _saida(g.usuario)
