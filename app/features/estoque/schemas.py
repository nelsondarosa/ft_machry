"""Schemas Pydantic de entrada (validação) e saída (serialização) da API de estoque."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

TipoLocalizacao = Literal["SECO", "RESFRIADO", "CONGELADO"]
TipoMovimentacao = Literal[
    "ENTRADA", "SAIDA", "AJUSTE_ENTRADA", "AJUSTE_SAIDA",
    "TRANSFERENCIA", "TRANSFORMACAO",
]


class LocalizacaoCreate(BaseModel):
    nome: str
    tipo: TipoLocalizacao = "SECO"
    parent_id: Optional[int] = Field(default=None, gt=0, strict=True)
    foto_url: Optional[str] = None

    @model_validator(mode="after")
    def _nome_nao_vazio(self):
        self.nome = self.nome.strip()
        if not self.nome:
            raise ValueError("nome e tipo de localização são obrigatórios/válidos")
        return self


class LocalizacaoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Optional[str] = None
    tipo: Optional[TipoLocalizacao] = None
    parent_id: Optional[int] = Field(default=None, gt=0, strict=True)
    foto_url: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _nao_vazio(cls, dados):
        if not isinstance(dados, dict) or not dados:
            raise ValueError("campos inválidos ou ausentes")
        return dados

    @model_validator(mode="after")
    def _nome_valido(self):
        if self.nome is not None:
            self.nome = self.nome.strip()
            if not self.nome:
                raise ValueError("nome vazio")
        return self


class LocalizacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo: str
    parent_id: Optional[int] = None
    foto_url: Optional[str] = None


class LoteCreate(BaseModel):
    produto_id: int = Field(gt=0, strict=True)
    localizacao_id: int = Field(gt=0, strict=True)
    data_producao: Optional[date] = None
    data_validade: Optional[date] = None
    custo_unitario: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False, strict=True)

    @model_validator(mode="after")
    def _ordem_datas(self):
        if self.data_producao and self.data_validade and self.data_producao > self.data_validade:
            raise ValueError("validade anterior à produção")
        return self


class LoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_producao: Optional[date] = None
    data_validade: Optional[date] = None
    custo_unitario: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False, strict=True)

    @model_validator(mode="before")
    @classmethod
    def _nao_vazio(cls, dados):
        if not isinstance(dados, dict) or not dados:
            raise ValueError(
                "somente datas e custo podem ser editados; saldo muda por movimentação"
            )
        return dados


class LoteQuery(BaseModel):
    produto_id: Optional[int] = Field(default=None, gt=0)
    localizacao_id: Optional[int] = Field(default=None, gt=0)


class LoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    localizacao_id: int
    quantidade: float
    data_producao: Optional[str] = None
    data_validade: Optional[str] = None
    custo_unitario: Optional[float] = None
    criado_em: str


class LoteListadoOut(LoteOut):
    produto: str
    localizacao: str


class MovimentacaoCreate(BaseModel):
    tipo: TipoMovimentacao
    lote_id: int = Field(gt=0, strict=True)
    usuario_id: int = Field(gt=0, strict=True)
    quantidade: float = Field(gt=0, allow_inf_nan=False, strict=True)
    lote_destino_id: Optional[int] = Field(default=None, gt=0, strict=True)
    quantidade_destino: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False, strict=True)
    motivo: Optional[str] = None
    observacao: Optional[str] = None

    @model_validator(mode="after")
    def _regras_cruzadas(self):
        self.motivo = self.motivo.strip() if self.motivo else None
        if self.motivo == "":
            self.motivo = None
        if self.tipo in {"SAIDA", "AJUSTE_ENTRADA", "AJUSTE_SAIDA"} and not self.motivo:
            raise ValueError("motivo obrigatório")
        exige_destino = self.tipo in {"TRANSFERENCIA", "TRANSFORMACAO"}
        if exige_destino != (self.lote_destino_id is not None):
            raise ValueError(
                "lote_destino_id obrigatório apenas para transferência/transformação"
            )
        exige_qtd_destino = self.tipo == "TRANSFORMACAO"
        if exige_qtd_destino != (self.quantidade_destino is not None):
            raise ValueError(
                "quantidade_destino obrigatória apenas para transformação"
            )
        if self.lote_destino_id is not None and self.lote_destino_id == self.lote_id:
            raise ValueError("origem e destino precisam ser diferentes")
        return self


class MovimentacaoQuery(BaseModel):
    limite: int = Field(default=100, ge=1, le=500)
    lote_id: Optional[int] = Field(default=None, gt=0)
    usuario_id: Optional[int] = Field(default=None, gt=0)
    tipo: Optional[str] = None

    @model_validator(mode="after")
    def _tipo_maiusculo(self):
        if self.tipo is not None:
            self.tipo = self.tipo.upper()
        return self


class MovimentacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    lote_id: int
    lote_destino_id: Optional[int] = None
    quantidade: float
    quantidade_destino: Optional[float] = None
    motivo: Optional[str] = None
    usuario_id: int
    solicitacao_producao_id: Optional[int] = None
    sp_componente_id: Optional[int] = None
    observacao: Optional[str] = None
    criado_em: str


class InventarioQuery(BaseModel):
    produto_id: Optional[int] = Field(default=None, gt=0)
    lote_id: Optional[int] = Field(default=None, gt=0)


class ItemInventarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_id: int
    produto: str
    tipo_produto: str
    unidade_medida: str
    lote_id: int
    quantidade: float
    data_validade: Optional[str] = None
    localizacao: str


class SugestaoSaidaQuery(BaseModel):
    quantidade: float = Field(gt=0, allow_inf_nan=False)


class LoteSugeridoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lote_id: int
    quantidade: float
    data_validade: Optional[str] = None


class SugestaoSaidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_id: int
    quantidade_solicitada: float
    lotes: list[LoteSugeridoOut]
    quantidade_faltante: float
    criterio: str = "FEFO: menor validade primeiro (somente lotes não vencidos)"
    aviso: str = "Sugestão de separação: não movimenta o estoque"
