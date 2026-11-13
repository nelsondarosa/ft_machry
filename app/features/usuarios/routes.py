from flask import Blueprint, g

from app.utils.paginacao import PaginacaoQuery, resposta_paginada
from app.utils.parsing import consulta, entrada
from app.utils.permissoes import exigir_papeis

from .repository import UsuarioRepository
from .schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate
from .services import UsuarioService

bp = Blueprint("usuarios", __name__)


def get_service() -> UsuarioService:
    return UsuarioService(UsuarioRepository())


def _saida(usuario):
    return UsuarioOut.model_validate(usuario).model_dump()


@bp.get("")
@exigir_papeis("OWNER")
def listar():
    return resposta_paginada(get_service().listar(consulta(PaginacaoQuery)), UsuarioOut)


@bp.post("")
@exigir_papeis("OWNER")
def criar():
    usuario = get_service().criar(entrada(UsuarioCreate))
    return _saida(usuario), 201


@bp.put("/<int:usuario_id>")
@exigir_papeis("OWNER")
def atualizar(usuario_id: int):
    usuario = get_service().atualizar(usuario_id, entrada(UsuarioUpdate), g.usuario.id)
    return _saida(usuario)
