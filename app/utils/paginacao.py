"""Paginação das listagens da API, baseada no Flask-SQLAlchemy.

O consumidor escolhe a página com `page` e o tamanho com `per_page` na query
string (os mesmos nomes que o Flask-SQLAlchemy usa por padrão).
"""
from __future__ import annotations

from typing import Any, Callable

from flask_sqlalchemy.pagination import Pagination
from pydantic import BaseModel, Field
from sqlalchemy import Select, text

from db.database_config import db

POR_PAGINA_PADRAO = 20
POR_PAGINA_MAXIMO = 100


class PaginacaoQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=POR_PAGINA_PADRAO, ge=1, le=POR_PAGINA_MAXIMO)


def paginar(consulta: Select, paginacao: PaginacaoQuery) -> Pagination:
    """Pagina um `select()` de entidades ORM."""
    return db.paginate(
        consulta,
        page=paginacao.page,
        per_page=paginacao.per_page,
        max_per_page=POR_PAGINA_MAXIMO,
        error_out=False,
    )


class SQLPagination(Pagination):
    """Paginação para SQL textual, cujas linhas viram mappings.

    `db.paginate` devolve só a primeira coluna de cada linha (`.scalars()`),
    então consultas `text()` com várias colunas precisam desta implementação.
    """

    def _query_items(self) -> list[Any]:
        sql = f"{self._query_args['sql']} LIMIT :_pg_limite OFFSET :_pg_offset"
        params = {
            **self._query_args["params"],
            "_pg_limite": self.per_page,
            "_pg_offset": self._query_offset,
        }
        return list(db.session.execute(text(sql), params).mappings().all())

    def _query_count(self) -> int:
        sql = f"SELECT COUNT(*) FROM ({self._query_args['sql']}) AS _pg_total"
        return db.session.execute(text(sql), self._query_args["params"]).scalar_one()


def paginar_sql(sql: str, params: dict, paginacao: PaginacaoQuery) -> Pagination:
    """Pagina uma consulta SQL textual; `sql` não deve conter LIMIT/OFFSET."""
    return SQLPagination(
        page=paginacao.page,
        per_page=paginacao.per_page,
        max_per_page=POR_PAGINA_MAXIMO,
        error_out=False,
        sql=sql,
        params=params,
    )


def resposta_paginada(
    pagina: Pagination, saida: type[BaseModel] | Callable[[Any], Any]
) -> dict:
    """Monta o envelope paginado.

    `saida` pode ser um schema Pydantic de saída (serializado com
    `model_validate(...).model_dump()`) ou uma função que serializa um item.
    """
    if isinstance(saida, type) and issubclass(saida, BaseModel):
        serializar = lambda item: saida.model_validate(item).model_dump()  # noqa: E731
    else:
        serializar = saida
    return {
        "items": [serializar(item) for item in pagina.items],
        "page": pagina.page,
        "per_page": pagina.per_page,
        "total": pagina.total,
        "pages": pagina.pages,
    }
