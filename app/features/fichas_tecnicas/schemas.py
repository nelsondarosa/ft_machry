from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FichaFaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fase_id: int = Field(gt=0)
    ordem: int = Field(gt=0)
    tempo_previsto_min: int = Field(gt=0)


class FichaComponenteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_id: int = Field(gt=0)
    quantidade: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    fase_ordem: int | None = Field(default=None, gt=0)


class FichaTecnicaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_id: int = Field(gt=0)
    rendimento: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=2000)
    fases: list[FichaFaseInput] = Field(min_length=1)
    componentes: list[FichaComponenteInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_duplicidades_e_referencias(self):
        ordens = [fase.ordem for fase in self.fases]
        if len(ordens) != len(set(ordens)):
            raise ValueError("a ordem das fases não pode se repetir")

        produtos = [componente.produto_id for componente in self.componentes]
        if len(produtos) != len(set(produtos)):
            raise ValueError("um componente não pode se repetir na ficha")

        ordens_validas = set(ordens)
        for componente in self.componentes:
            if componente.fase_ordem is not None and componente.fase_ordem not in ordens_validas:
                raise ValueError(
                    f"a fase de ordem {componente.fase_ordem} não pertence à ficha"
                )
        return self


class FichaLoteFase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fase: str = Field(min_length=1, max_length=100)
    ordem: int = Field(gt=0)
    tempo_previsto_min: int = Field(gt=0)


class FichaLoteComponente(BaseModel):
    """Componente referenciado pelo nome. Quantidade nula significa "a gosto" (q.b.)."""

    model_config = ConfigDict(extra="forbid")

    produto: str = Field(min_length=1, max_length=150)
    quantidade: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    unidade: str | None = Field(default=None, max_length=20)
    fase_ordem: int | None = Field(default=None, gt=0)


class FichaLoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto: str = Field(min_length=1, max_length=150)
    rendimento: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    observacao: str | None = Field(default=None, max_length=2000)
    fases: list[FichaLoteFase] = Field(min_length=1)
    componentes: list[FichaLoteComponente] = Field(default_factory=list)


class FichaLoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fichas: list[dict] = Field(min_length=1, max_length=200)


class FaseCatalogoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
