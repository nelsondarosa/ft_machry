"""Rotas HTTP de estoque.

Controller puro: delega a leitura para o service e serializa com schemas.py
"""
from flask import Blueprint

from app.utils.errors import RegistroNaoEncontrado
from app.utils.paginacao import PaginacaoQuery, resposta_paginada
from app.utils.parsing import consulta, entrada

from . import schemas
from .repository import EstoqueRepository
from .services import EstoqueService

bp = Blueprint("estoque", __name__)


def get_service() -> EstoqueService:
    return EstoqueService(EstoqueRepository())


@bp.get("/inventario")
def inventario():
    filtro = consulta(schemas.InventarioQuery)
    pagina = get_service().listar_inventario(filtro, filtro.produto_id, filtro.lote_id)
    return resposta_paginada(pagina, schemas.ItemInventarioOut)


@bp.get("/movimentacoes")
def movimentacoes():
    filtro = consulta(schemas.MovimentacaoQuery)
    pagina = get_service().listar_movimentacoes(
        filtro, filtro.lote_id, filtro.usuario_id, filtro.tipo
    )
    return resposta_paginada(pagina, schemas.MovimentacaoOut)


@bp.get("/localizacoes")
def listar_localizacoes():
    pagina = get_service().listar_localizacoes(consulta(PaginacaoQuery))
    return resposta_paginada(pagina, schemas.LocalizacaoOut)


@bp.post("/localizacoes")
def criar_localizacao():
    dados = entrada(schemas.LocalizacaoCreate)
    nova = get_service().criar_localizacao(dados)
    return schemas.LocalizacaoOut.model_validate(nova).model_dump(), 201


@bp.put("/localizacoes/<int:loc_id>")
def atualizar_localizacao(loc_id):
    dados = entrada(schemas.LocalizacaoUpdate)
    atualizada = get_service().atualizar_localizacao(loc_id, dados)
    return schemas.LocalizacaoOut.model_validate(atualizada).model_dump()


@bp.delete("/localizacoes/<int:loc_id>")
def remover_localizacao(loc_id):
    get_service().remover_localizacao(loc_id)
    return {}, 204


@bp.get("/lotes")
def listar_lotes():
    filtro = consulta(schemas.LoteQuery)
    pagina = get_service().listar_lotes(filtro, filtro.produto_id, filtro.localizacao_id)
    return resposta_paginada(pagina, schemas.LoteListadoOut)


@bp.get("/lotes/<int:lote_id>")
def detalhar_lote(lote_id):
    lote = get_service().obter_lote(lote_id)
    if lote is None:
        raise RegistroNaoEncontrado("lote não encontrado")
    return schemas.LoteOut.model_validate(lote).model_dump()


@bp.post("/lotes")
def criar_lote():
    dados = entrada(schemas.LoteCreate)
    novo = get_service().criar_lote(dados)
    return schemas.LoteOut.model_validate(novo).model_dump(), 201


@bp.put("/lotes/<int:lote_id>")
def atualizar_lote(lote_id):
    dados = entrada(schemas.LoteUpdate)
    atualizado = get_service().atualizar_lote(lote_id, dados)
    return schemas.LoteOut.model_validate(atualizado).model_dump()


@bp.get("/lotes/<int:lote_id>/itens")
def listar_itens(lote_id):
    filtro = consulta(schemas.ItemLoteQuery)
    pagina = get_service().listar_itens(lote_id, filtro)
    return resposta_paginada(pagina, schemas.ItemLoteOut)


@bp.post("/lotes/<int:lote_id>/itens")
def adicionar_itens(lote_id):
    dados = entrada(schemas.ItensLoteCreate)
    itens = get_service().adicionar_itens(lote_id, dados)
    return [schemas.ItemLoteOut.model_validate(item).model_dump() for item in itens], 201


@bp.get("/itens/<int:item_id>")
def detalhar_item(item_id):
    item = get_service().obter_item(item_id)
    return schemas.ItemLoteOut.model_validate(item).model_dump()


@bp.put("/itens/<int:item_id>")
def atualizar_item(item_id):
    dados = entrada(schemas.ItemLoteUpdate)
    item = get_service().atualizar_item(item_id, dados)
    return schemas.ItemLoteOut.model_validate(item).model_dump()


@bp.post("/itens/<int:item_id>/abrir")
def abrir_item(item_id):
    item = get_service().abrir_item(item_id)
    return schemas.ItemLoteOut.model_validate(item).model_dump()


@bp.post("/movimentacoes")
def registrar_movimentacao():
    dados = entrada(schemas.MovimentacaoCreate)
    nova = get_service().registrar_movimentacao(dados)
    return schemas.MovimentacaoOut.model_validate(nova).model_dump(), 201


@bp.get("/sugestao-saida/<int:produto_id>")
def sugestao_saida(produto_id):
    filtro = consulta(schemas.SugestaoSaidaQuery)
    sugestao = get_service().sugestao_saida(produto_id, filtro.quantidade)
    return schemas.SugestaoSaidaOut.model_validate(sugestao).model_dump()
