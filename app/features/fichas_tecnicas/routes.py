from flask import Blueprint

from app.utils.parsing import entrada

from .repository import FichaTecnicaRepository
from .schemas import FaseCatalogoOut, FichaTecnicaInput
from .services import FichaTecnicaService

bp = Blueprint("fichas_tecnicas", __name__)


def get_service() -> FichaTecnicaService:
    return FichaTecnicaService(FichaTecnicaRepository())


def _serializar(ficha):
    return {
        "id": ficha.id,
        "produto_id": ficha.produto_id,
        "produto": ficha.produto.nome,
        "unidade_rendimento": ficha.produto.unidade_medida,
        "rendimento": float(ficha.rendimento),
        "observacao": ficha.observacao,
        "fases": [
            {
                "id": fase.id,
                "fase_id": fase.fase_id,
                "fase": fase.fase.nome,
                "ordem": fase.ordem,
                "tempo_previsto_min": fase.tempo_previsto_min,
            }
            for fase in ficha.fases
        ],
        "componentes": [
            {
                "id": componente.id,
                "produto_id": componente.produto_id,
                "produto": componente.produto.nome,
                "unidade_medida": componente.produto.unidade_medida,
                "quantidade": float(componente.quantidade),
                "ficha_tecnica_fase_id": componente.ficha_tecnica_fase_id,
                "fase_ordem": componente.fase.ordem if componente.fase else None,
            }
            for componente in ficha.componentes
        ],
    }


@bp.get("/fases")
def listar_fases():
    return [
        FaseCatalogoOut.model_validate(fase).model_dump()
        for fase in get_service().listar_fases()
    ]


@bp.get("")
def listar():
    return [_serializar(ficha) for ficha in get_service().listar()]


@bp.get("/<int:ficha_id>")
def detalhar(ficha_id: int):
    return _serializar(get_service().obter(ficha_id))


@bp.post("")
def criar():
    return _serializar(get_service().criar(entrada(FichaTecnicaInput))), 201


@bp.put("/<int:ficha_id>")
def atualizar(ficha_id: int):
    return _serializar(
        get_service().atualizar(ficha_id, entrada(FichaTecnicaInput))
    )


@bp.delete("/<int:ficha_id>")
def remover(ficha_id: int):
    get_service().remover(ficha_id)
    return "", 204
