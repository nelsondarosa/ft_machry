from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.utils.constantes import Constantes
from db.database_config import db
from app.features.produtos.models import Produto


class Localizacao(db.Model):
    __tablename__ = "localizacao"
    __table_args__ = (
        db.CheckConstraint(
            Constantes.sql_in("tipo", Constantes.TIPOS_CONSERVACAO),
            name="ck_localizacao_tipo",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False, unique=True)
    tipo = db.Column(db.Text, nullable=False, default="SECO", server_default="SECO")
    parent_id = db.Column(db.Integer, db.ForeignKey("localizacao.id"))
    foto_url = db.Column(db.Text)


class Lote(db.Model):
    __tablename__ = "lote"
    __table_args__ = (
        db.CheckConstraint("quantidade >= 0", name="ck_lote_quantidade"),
        db.Index("idx_lote_fifo", "produto_id", "data_validade", "localizacao_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    localizacao_id = db.Column(db.Integer, db.ForeignKey("localizacao.id"), nullable=False)
    quantidade = db.Column(db.Numeric(asdecimal=False), nullable=False, default=0, server_default="0")
    data_producao = db.Column(db.String)
    data_validade = db.Column(db.String)
    custo_unitario = db.Column(db.Numeric(asdecimal=False))
    criado_em = db.Column(
        db.String,
        nullable=False,
        server_default=db.text("(CAST(CURRENT_TIMESTAMP AS TEXT))"),
    )


class MovimentacaoEstoque(db.Model):
    __tablename__ = "movimentacao_estoque"
    __table_args__ = (
        db.CheckConstraint(
            Constantes.sql_in("tipo", Constantes.TIPOS_MOVIMENTACAO),
            name="ck_movimentacao_tipo",
        ),
        db.CheckConstraint("quantidade > 0", name="ck_movimentacao_quantidade"),
        db.CheckConstraint(
            "quantidade_destino IS NULL OR quantidade_destino > 0",
            name="ck_movimentacao_quantidade_destino",
        ),
        db.CheckConstraint(
            "lote_destino_id IS NULL OR lote_destino_id <> lote_id",
            name="ck_movimentacao_lotes_diferentes",
        ),
        db.Index("idx_mov_lote", "lote_id", "criado_em"),
        db.Index("idx_mov_sp", "solicitacao_producao_id"),
        db.Index("idx_mov_sp_componente", "sp_componente_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Text, nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lote.id"), nullable=False)
    lote_destino_id = db.Column(db.Integer, db.ForeignKey("lote.id"))
    quantidade = db.Column(db.Numeric(asdecimal=False), nullable=False)
    quantidade_destino = db.Column(db.Numeric(asdecimal=False))
    motivo = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    solicitacao_producao_id = db.Column(
        db.Integer, db.ForeignKey("solicitacao_producao.id")
    )
    sp_componente_id = db.Column(db.Integer, db.ForeignKey("sp_componente.id"))
    observacao = db.Column(db.Text)
    criado_em = db.Column(
        db.String,
        nullable=False,
        server_default=db.text("(CAST(CURRENT_TIMESTAMP AS TEXT))"),
    )

    @classmethod
    def from_row(cls, row) -> "MovimentacaoEstoque":
        return cls(**{chave: row[chave] for chave in row.keys()})


class ProdutoTransformacao(db.Model):
    __tablename__ = "produto_transformacao"
    __table_args__ = (
        db.CheckConstraint(
            "produto_origem_id <> produto_destino_id",
            name="ck_transformacao_produtos_diferentes",
        ),
    )

    produto_origem_id = db.Column(
        db.Integer, db.ForeignKey("produto.id"), primary_key=True
    )
    produto_destino_id = db.Column(
        db.Integer, db.ForeignKey("produto.id"), primary_key=True
    )


@dataclass
class ItemInventario:
    produto_id: int
    produto: str
    tipo_produto: str
    unidade_medida: str
    lote_id: int
    quantidade: float
    data_validade: Optional[str]
    localizacao: str

    @classmethod
    def from_row(cls, row) -> "ItemInventario":
        return cls(**{chave: row[chave] for chave in row.keys()})


@dataclass
class LoteListado:
    id: int
    produto_id: int
    localizacao_id: int
    quantidade: float
    data_producao: Optional[str]
    data_validade: Optional[str]
    custo_unitario: Optional[float]
    criado_em: str
    produto: str
    localizacao: str

    @classmethod
    def from_row(cls, row) -> "LoteListado":
        return cls(**{chave: row[chave] for chave in row.keys()})


@dataclass
class LoteSugerido:
    lote_id: int
    quantidade: float
    data_validade: Optional[str]


@dataclass
class SugestaoSaida:
    produto_id: int
    quantidade_solicitada: float
    lotes: list[LoteSugerido]
    quantidade_faltante: float
