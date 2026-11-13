from flask import Flask, g, request, session

from app.features.usuarios.models import Usuario
from app.utils.constantes import Constantes
from db.database_config import db


def _carregar_usuario() -> None:
    usuario_id = session.get("usuario_id")
    g.usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
    if g.usuario is not None and not g.usuario.ativo:
        session.clear()
        g.usuario = None


def _autorizar(papel: str, metodo: str, caminho: str):
    """Devolve None quando o acesso é permitido, ou a resposta de erro 403."""
    if papel == "OWNER":
        return None
    if papel == "ADMIN":
        if caminho.startswith("/api/usuarios"):
            return {"erro": "você não tem permissão para esta ação"}, 403
        if caminho.startswith(("/api/produtos", "/api/fichas-tecnicas")) and metodo != "GET":
            return {"erro": "somente a proprietária pode alterar produtos e fichas"}, 403
        return None
    if papel == "USER" and metodo == "GET" and caminho.startswith(("/api/producao", "/api/fichas-tecnicas")):
        return None
    if (
        papel == "USER"
        and metodo == "PUT"
        and caminho.startswith("/api/producao/solicitacoes/")
        and caminho.endswith("/status")
    ):
        return None
    return {"erro": "você não tem permissão para acessar este recurso"}, 403


def registrar_middleware_autenticacao(app: Flask) -> None:
    @app.before_request
    def autenticar_e_autorizar():
        _carregar_usuario()
        if not request.path.startswith("/api/") or (
            request.path in Constantes.ROTAS_PUBLICAS
            or request.path.startswith(Constantes.PREFIXOS_PUBLICOS)
        ):
            return None
        if g.usuario is None:
            return {"erro": "autenticação necessária"}, 401
        if request.path in Constantes.ROTAS_DE_SESSAO:
            return None
        return _autorizar(g.usuario.papel, request.method, request.path)
