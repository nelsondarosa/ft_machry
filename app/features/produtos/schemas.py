from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.constantes import Constantes
from app.utils.texto import padronizar_nome




class ProdutoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=150)
    tipo: Constantes.TipoProduto
    unidade_medida: Constantes.UnidadeMedida
    grupo_id: int | None = Field(default=None, gt=0)
    subdivisao: str | None = Field(default=None, max_length=100)
    conservacao: Constantes.TipoConservacao = "SECO"
    validade_obrigatoria: int = Field(default=0, ge=0, le=1)
    validade_padrao_dias: int | None = Field(default=None, ge=0)
    foto_url: str | None = None

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("campo obrigatório não pode ser vazio")
        return padronizar_nome(valor)


class ProdutoLoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produtos: list[dict] = Field(min_length=1, max_length=500)


class ProdutoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=150)
    tipo: Constantes.TipoProduto | None = None
    unidade_medida: Constantes.UnidadeMedida | None = None
    grupo_id: int | None = Field(default=None, gt=0)
    subdivisao: str | None = Field(default=None, max_length=100)
    conservacao: Constantes.TipoConservacao | None = None
    validade_obrigatoria: int | None = Field(default=None, ge=0, le=1)
    validade_padrao_dias: int | None = Field(default=None, ge=0)
    foto_url: str | None = None

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, valor: str | None) -> str:
        if valor is None:
            raise ValueError("campo não pode ser nulo")
        valor = valor.strip()
        if not valor:
            raise ValueError("campo não pode ser vazio")
        return padronizar_nome(valor)

    @field_validator("unidade_medida")
    @classmethod
    def unidade_nao_nula(cls, valor):
        if valor is None:
            raise ValueError("campo não pode ser nulo")
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
    subdivisao: str | None
    conservacao: str
    validade_obrigatoria: int
    validade_padrao_dias: int | None
    foto_url: str | None
    ativo: int
    criado_em: str
