from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from db.database_config import db


class SolicitacaoProducao(db.Model):
    __tablename__ = "solicitacao_producao"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('ABERTA', 'EM_SEPARACAO', 'EM_PRODUCAO', 'CONCLUIDA', 'CANCELADA')",
            name="ck_solicitacao_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    ficha_tecnica_id = db.Column(
        db.Integer, db.ForeignKey("ficha_tecnica.id"), nullable=False
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    status = db.Column(db.Text, nullable=False, default="ABERTA", server_default="ABERTA")
    criado_em = db.Column(
        db.String,
        nullable=False,
        server_default=db.text("(CAST(CURRENT_TIMESTAMP AS TEXT))"),
    )
    concluido_em = db.Column(db.String)


class SpFase(db.Model):
    __tablename__ = "sp_fase"
    __table_args__ = (
        db.UniqueConstraint(
            "solicitacao_producao_id", "ordem", name="uq_sp_fase_ordem"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    solicitacao_producao_id = db.Column(
        db.Integer, db.ForeignKey("solicitacao_producao.id"), nullable=False
    )
    fase_id = db.Column(db.Integer, db.ForeignKey("fase_producao.id"), nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    tempo_previsto_min = db.Column(db.Integer, nullable=False)
    tempo_realizado_min = db.Column(db.Integer)


class SpComponente(db.Model):
    __tablename__ = "sp_componente"
    __table_args__ = (
        db.UniqueConstraint(
            "solicitacao_producao_id", "produto_id", name="uq_sp_componente_produto"
        ),
        db.CheckConstraint("quantidade_prevista > 0", name="ck_sp_quantidade_prevista"),
    )

    id = db.Column(db.Integer, primary_key=True)
    solicitacao_producao_id = db.Column(
        db.Integer, db.ForeignKey("solicitacao_producao.id"), nullable=False
    )
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade_prevista = db.Column(db.Numeric(asdecimal=False), nullable=False)
    sp_fase_id = db.Column(db.Integer, db.ForeignKey("sp_fase.id"))


@dataclass
class ComponenteSolicitacao:
    sp_componente_id: int
    solicitacao_producao_id: int
    produto_id: int
    componente: str
    unidade_medida: str
    fase_ordem: Optional[int]
    fase: Optional[str]
    quantidade_prevista: float
    quantidade_realizada: float
    custo_realizado: Optional[float]

    @classmethod
    def from_row(cls, row) -> "ComponenteSolicitacao":
        return cls(**{chave: row[chave] for chave in row.keys()})


@dataclass
class FaseSolicitacao:
    ordem: int
    fase: str
    tempo_previsto_min: int
    tempo_realizado_min: Optional[int]

    @classmethod
    def from_row(cls, row) -> "FaseSolicitacao":
        return cls(**{chave: row[chave] for chave in row.keys()})


@dataclass
class LoteProduzido:
    solicitacao_producao_id: int
    lote_id: int
    quantidade: float
    criado_em: str

    @classmethod
    def from_row(cls, row) -> "LoteProduzido":
        return cls(**{chave: row[chave] for chave in row.keys()})


@dataclass
class SolicitacaoDetalhe:
    solicitacao: SolicitacaoProducao
    componentes: list[ComponenteSolicitacao]
    fases: list[FaseSolicitacao]
    lotes_produzidos: list[LoteProduzido]
