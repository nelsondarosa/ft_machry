from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import or_, text

from db.database_config import db

from app.features.usuarios.models import Usuario
from app.utils.constantes import Constantes
from app.utils.paginacao import PaginacaoQuery, paginar, paginar_sql
from app.utils.interfaces.repository import RepositorioBase

from .models import (
    ItemLote, Localizacao, Lote, MovimentacaoEstoque, MovimentacaoItem, Produto,
    ProdutoTransformacao,
)


class EstoqueRepository(RepositorioBase):
    # -- inventário / movimentações -----------------------------------------

    def listar_inventario(
        self,
        paginacao: PaginacaoQuery,
        produto_id: Optional[int] = None,
        lote_id: Optional[int] = None,
    ):
        sql = "SELECT * FROM vw_inventario WHERE 1=1"
        params: dict = {}
        if produto_id is not None:
            sql += " AND produto_id = :produto_id"
            params["produto_id"] = produto_id
        if lote_id is not None:
            sql += " AND lote_id = :lote_id"
            params["lote_id"] = lote_id
        sql += " ORDER BY produto, data_validade, lote_id"
        return paginar_sql(sql, params, paginacao)

    def listar_movimentacoes(
        self,
        paginacao: PaginacaoQuery,
        lote_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
        tipo: Optional[str] = None,
    ):
        sql = "SELECT * FROM movimentacao_estoque WHERE 1=1"
        params: dict = {}
        if lote_id is not None:
            sql += " AND lote_id = :lote_id"
            params["lote_id"] = lote_id
        if usuario_id is not None:
            sql += " AND usuario_id = :usuario_id"
            params["usuario_id"] = usuario_id
        if tipo is not None:
            sql += " AND tipo = :tipo"
            params["tipo"] = tipo
        sql += " ORDER BY id DESC"
        return paginar_sql(sql, params, paginacao)

    def obter_movimentacao(self, mov_id: int) -> Optional[MovimentacaoEstoque]:
        return db.session.get(MovimentacaoEstoque, mov_id)

    def inserir_movimentacao(
        self, *, tipo, lote_origem: Lote, lote_destino: Optional[Lote], quantidade,
        quantidade_destino, motivo, usuario_id, observacao,
    ) -> MovimentacaoEstoque:
        mov = MovimentacaoEstoque(
            tipo=tipo,
            lote_id=lote_origem.id,
            lote_destino_id=lote_destino.id if lote_destino is not None else None,
            quantidade=quantidade,
            quantidade_destino=quantidade_destino,
            motivo=motivo,
            usuario_id=usuario_id,
            observacao=observacao,
        )
        db.session.add(mov)
        self._aplicar_saldo(
            tipo=tipo, lote_origem=lote_origem, lote_destino=lote_destino,
            quantidade=quantidade, quantidade_destino=quantidade_destino,
        )
        db.session.flush()
        db.session.refresh(mov)
        return mov

    def _aplicar_saldo(self, *, tipo, lote_origem: Lote, lote_destino: Optional[Lote],
                        quantidade, quantidade_destino) -> None:
        if tipo in Constantes.TIPOS_SOMAM_NA_ORIGEM:
            lote_origem.quantidade += quantidade
        elif tipo in Constantes.TIPOS_SUBTRAEM_DA_ORIGEM:
            lote_origem.quantidade -= quantidade

        if tipo in Constantes.TIPOS_COM_DESTINO:
            lote_destino.quantidade += quantidade_destino if quantidade_destino is not None else quantidade

    def transformacao_cadastrada(self, produto_origem_id: int, produto_destino_id: int) -> bool:
        return db.session.get(ProdutoTransformacao, (produto_origem_id, produto_destino_id)) is not None

    # -- localização -----------------------------------------------------------

    def listar_localizacoes(self, paginacao: PaginacaoQuery):
        return paginar(
            db.select(Localizacao).order_by(Localizacao.nome, Localizacao.id), paginacao
        )

    def obter_localizacao(self, loc_id: int) -> Optional[Localizacao]:
        return db.session.get(Localizacao, loc_id)

    def inserir_localizacao(self, *, nome, tipo, parent_id, foto_url) -> Localizacao:
        localizacao = Localizacao(nome=nome, tipo=tipo, parent_id=parent_id, foto_url=foto_url)
        db.session.add(localizacao)
        db.session.commit()
        return localizacao

    def atualizar_localizacao(self, loc_id: int, campos: dict) -> None:
        localizacao = db.session.get(Localizacao, loc_id)
        for campo, valor in campos.items():
            setattr(localizacao, campo, valor)

    def remover_localizacao(self, loc_id: int) -> bool:
        localizacao = db.session.get(Localizacao, loc_id)
        if localizacao is None:
            return False
        db.session.delete(localizacao)
        return True

    def existe_incompatibilidade_tipo(self, loc_id: int, novo_tipo: str) -> bool:
        return (
            db.session.query(Lote)
            .join(Produto, Produto.id == Lote.produto_id)
            .filter(Lote.localizacao_id == loc_id, Produto.conservacao != novo_tipo)
            .first()
            is not None
        )

    # -- lote --------------------------------------------------------------------

    def listar_lotes(
        self,
        paginacao: PaginacaoQuery,
        produto_id: Optional[int] = None,
        localizacao_id: Optional[int] = None,
    ):
        sql = """SELECT l.*, p.nome AS produto, loc.nome AS localizacao,
                    CASE 
                        WHEN l.data_validade IS NOT NULL AND l.data_validade < :hoje
                        THEN TRUE
                        ELSE FALSE
                    END AS vencido
               ,
                        COALESCE(i.total, 0) AS itens_total,
                        COALESCE(i.disponiveis, 0) AS itens_disponiveis,
                        COALESCE(i.reservados, 0) AS itens_reservados,
                        COALESCE(i.em_uso, 0) AS itens_em_uso,
                        COALESCE(i.consumidos, 0) AS itens_consumidos,
                        COALESCE(i.vencidos, 0) AS itens_vencidos
                   FROM lote l
                  JOIN produto p ON p.id = l.produto_id
                  JOIN localizacao loc ON loc.id = l.localizacao_id
               
                   LEFT JOIN (
                        SELECT lote_id, COUNT(*) AS total,
                               SUM(CASE WHEN status = 'DISPONIVEL'
                                    AND (data_validade IS NULL OR data_validade >= :hoje) THEN 1 ELSE 0 END) AS disponiveis,
                               SUM(CASE WHEN status = 'RESERVADA'
                                    AND (data_validade IS NULL OR data_validade >= :hoje) THEN 1 ELSE 0 END) AS reservados,
                               SUM(CASE WHEN status = 'EM_USO'
                                    AND (data_validade IS NULL OR data_validade >= :hoje) THEN 1 ELSE 0 END) AS em_uso,
                               SUM(CASE WHEN status = 'CONSUMIDA' THEN 1 ELSE 0 END) AS consumidos,
                               SUM(CASE WHEN status IN ('DISPONIVEL', 'RESERVADA', 'EM_USO') AND data_validade < :hoje THEN 1 ELSE 0 END) AS vencidos
                          FROM item_lote GROUP BY lote_id
                   ) i ON i.lote_id = l.id
                  WHERE 1=1"""
                
        params: dict = {"hoje": date.today().isoformat()}
        if produto_id is not None:
            sql += " AND l.produto_id = :produto_id"
            params["produto_id"] = produto_id
        if localizacao_id is not None:
            sql += " AND l.localizacao_id = :localizacao_id"
            params["localizacao_id"] = localizacao_id
        sql += " ORDER BY l.data_validade IS NULL, l.data_validade, l.id"
        return paginar_sql(sql, params, paginacao)

    def obter_lote(self, lote_id: int, para_atualizacao: bool = False) -> Optional[Lote]:
        return db.session.get(Lote, lote_id, with_for_update=para_atualizacao)

    def inserir_lote(
        self, *, produto_id, localizacao_id, data_producao, data_validade, custo_unitario,
        fornecedor=None, nota_fiscal=None,
    ) -> Lote:
        lote = Lote(
            produto_id=produto_id,
            localizacao_id=localizacao_id,
            quantidade=0,
            data_producao=data_producao,
            data_validade=data_validade,
            custo_unitario=custo_unitario,
            fornecedor=fornecedor,
            nota_fiscal=nota_fiscal,
        )
        db.session.add(lote)
        db.session.flush()
        db.session.refresh(lote)
        return lote

    def atualizar_lote(self, lote_id: int, campos: dict) -> None:
        lote = db.session.get(Lote, lote_id)
        for campo, valor in campos.items():
            setattr(lote, campo, valor)

    def lotes_fefo_disponiveis(self, produto_id: int):
        return db.session.execute(
            text(
                """SELECT * FROM lote WHERE produto_id = :produto_id AND quantidade > 0
                   AND (data_validade IS NULL OR data_validade >= :hoje)
                   ORDER BY data_validade IS NULL, data_validade, criado_em, id"""
            ),
            {"produto_id": produto_id, "hoje": date.today().isoformat()},
        ).mappings().all()

    # -- itens do lote -----------------------------------------------------------

    def listar_itens(self, paginacao: PaginacaoQuery, lote_id: int, status: Optional[str] = None):
        consulta = db.select(ItemLote).where(ItemLote.lote_id == lote_id)
        if status is not None:
            consulta = consulta.where(ItemLote.status == status)
        return paginar(consulta.order_by(ItemLote.lote_origem_id, ItemLote.sequencia), paginacao)

    def obter_item(self, item_id: int, para_atualizacao: bool = False) -> Optional[ItemLote]:
        return db.session.get(ItemLote, item_id, with_for_update=para_atualizacao)

    def lote_tem_itens(self, lote_id: int) -> bool:
        return db.session.execute(
            db.select(ItemLote.id).where(ItemLote.lote_id == lote_id).limit(1)
        ).first() is not None

    def itens_por_ids(self, item_ids: list[int]) -> list[ItemLote]:
        return list(db.session.execute(
            db.select(ItemLote).where(ItemLote.id.in_(item_ids))
            .order_by(ItemLote.id).with_for_update()
        ).scalars())

    def itens_fefo(self, lote_id: int) -> list[ItemLote]:
        """Itens que podem ser usados, na ordem em que devem sair do estoque."""
        hoje = date.today().isoformat()
        consulta = (
            db.select(ItemLote)
            .where(ItemLote.lote_id == lote_id)
            .where(ItemLote.status.in_(Constantes.STATUS_ITEM_LIVRES))
            .where(or_(ItemLote.data_validade.is_(None), ItemLote.data_validade >= hoje))
            .order_by(
                ItemLote.status != "EM_USO",
                ItemLote.data_validade.is_(None),
                ItemLote.data_validade,
                ItemLote.lote_origem_id,
                ItemLote.sequencia,
            )
            .with_for_update()
        )
        return list(db.session.execute(consulta).scalars())

    def itens_ativos(self, lote_id: int) -> list[ItemLote]:
        """Itens que ainda contam no saldo do lote."""
        consulta = (
            db.select(ItemLote)
            .where(ItemLote.lote_id == lote_id)
            .where(ItemLote.status.in_(Constantes.STATUS_ITEM_ATIVOS))
        )
        return list(db.session.execute(consulta).scalars())

    def proxima_sequencia(self, lote_origem_id: int) -> int:
        maior = db.session.execute(
            db.select(db.func.max(ItemLote.sequencia))
            .where(ItemLote.lote_origem_id == lote_origem_id)
        ).scalar()
        return (maior or 0) + 1

    def inserir_itens(self, itens: list[ItemLote]) -> list[ItemLote]:
        db.session.add_all(itens)
        db.session.flush()
        return itens

    def vincular_item(self, movimentacao_id: int, item_id: int, quantidade: float) -> None:
        """Registra que a movimentação usou `quantidade` do item."""
        vinculo = MovimentacaoItem(
            movimentacao_id=movimentacao_id, item_id=item_id, quantidade=quantidade
        )
        db.session.add(vinculo)
        db.session.flush()

    # -- entidades de outras features, lidas só para validação cruzada --------

    def obter_produto(self, produto_id: int) -> Optional[Produto]:
        return db.session.get(Produto, produto_id)

    def obter_produto_ativo(self, produto_id: int) -> Optional[Produto]:
        produto = db.session.get(Produto, produto_id)
        return produto if produto is not None and produto.ativo else None

    def obter_usuario_ativo(self, usuario_id: int) -> Optional[Usuario]:
        usuario = db.session.get(Usuario, usuario_id)
        return usuario if usuario is not None and usuario.ativo else None
