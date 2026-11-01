from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TipoProduto = Literal["INSUMO", "INTERMEDIARIO", "FINAL"]
TipoConservacao = Literal["CONGELADO", "RESFRIADO", "SECO"]


class ProdutoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=150)
    tipo: TipoProduto
    unidade_medida: str = Field(min_length=1, max_length=20)
    grupo_id: int | None = Field(default=None, gt=0)
    conservacao: TipoConservacao = "SECO"
    validade_obrigatoria: int = Field(default=0, ge=0, le=1)
    validade_padrao_dias: int | None = Field(default=None, ge=0)
    foto_url: str | None = None

    @field_validator("nome", "unidade_medida")
    @classmethod
    def limpar_texto_obrigatorio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("campo obrigatório não pode ser vazio")
        return valor


class ProdutoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=150)
    tipo: TipoProduto | None = None
    unidade_medida: str | None = Field(default=None, min_length=1, max_length=20)
    grupo_id: int | None = Field(default=None, gt=0)
    conservacao: TipoConservacao | None = None
    validade_obrigatoria: int | None = Field(default=None, ge=0, le=1)
    validade_padrao_dias: int | None = Field(default=None, ge=0)
    foto_url: str | None = None

    @field_validator("nome", "unidade_medida")
    @classmethod
    def limpar_texto(cls, valor: str | None) -> str:
        if valor is None:
            raise ValueError("campo não pode ser nulo")
        valor = valor.strip()
        if not valor:
            raise ValueError("campo não pode ser vazio")
        return valor

    @model_validator(mode="after")
    def validar_campos(self):
        if not self.model_fields_set:
            raise ValueError("nenhum campo de produto informado")
        return self


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo: str
    unidade_medida: str
    grupo_id: int | None
    conservacao: str
    validade_obrigatoria: int
    validade_padrao_dias: int | None
    foto_url: str | None
    ativo: int
    criado_em: str
