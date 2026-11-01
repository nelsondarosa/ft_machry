from flask import Blueprint

from app.utils.parsing import entrada

from .repository import ProdutoRepository
from .schemas import ProdutoCreate, ProdutoOut, ProdutoUpdate
from .services import ProdutoService

bp = Blueprint("produtos", __name__)


def get_service() -> ProdutoService:
    return ProdutoService(ProdutoRepository())


def _saida(produto):
    return ProdutoOut.model_validate(produto).model_dump()


@bp.get("")
def listar():
    return [_saida(produto) for produto in get_service().listar()]


@bp.get("/<int:produto_id>")
def detalhar(produto_id: int):
    return _saida(get_service().obter(produto_id))


@bp.post("")
def criar():
    produto = get_service().criar(entrada(ProdutoCreate))
    return _saida(produto), 201


@bp.put("/<int:produto_id>")
def atualizar(produto_id: int):
    return _saida(get_service().atualizar(produto_id, entrada(ProdutoUpdate)))


@bp.delete("/<int:produto_id>")
def remover(produto_id: int):
    get_service().remover(produto_id)
    return "", 204
