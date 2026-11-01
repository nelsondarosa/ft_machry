"""Rotas HTTP de produção.

Controller puro: delega a leitura para o service e serializa com schemas.py

"""
from flask import Blueprint, g

from app.utils.parsing import entrada

from . import schemas
from .repository import ProducaoRepository
from .services import ProducaoService

bp = Blueprint("producao", __name__)


def get_service() -> ProducaoService:
    return ProducaoService(ProducaoRepository())


@bp.get("/solicitacoes")
def listar_solicitacoes():
    itens = get_service().listar_solicitacoes()
    return [schemas.SolicitacaoProducaoOut.model_validate(i).model_dump() for i in itens]


@bp.post("/solicitacoes")
def criar_solicitacao():
    dados = entrada(schemas.SolicitacaoCreate)
    item = get_service().criar_solicitacao(dados.ficha_tecnica_id, g.usuario.id)
    return schemas.SolicitacaoProducaoOut.model_validate(item).model_dump(), 201


@bp.put("/solicitacoes/<int:sp_id>/status")
def atualizar_status(sp_id: int):
    dados = entrada(schemas.SolicitacaoStatusUpdate)
    item = get_service().atualizar_status(sp_id, dados.status)
    return schemas.SolicitacaoProducaoOut.model_validate(item).model_dump()


@bp.get("/solicitacoes/<int:sp_id>")
def detalhar_solicitacao(sp_id):
    detalhe = get_service().obter_detalhe(sp_id)
    return schemas.SolicitacaoDetalheOut.model_validate(detalhe).model_dump()
