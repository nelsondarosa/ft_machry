from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Papel = Literal["OWNER", "ADMIN", "USER"]


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=120)
    username: str = Field(pattern=r"^[a-zA-Z0-9._-]+$", min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=200)
    papel: Papel

    @field_validator("nome", "username")
    @classmethod
    def limpar_texto(cls, valor: str) -> str:
        return valor.strip()


class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    papel: Papel | None = None
    ativo: int | None = Field(default=None, ge=0, le=1)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    username: str
    papel: str
    ativo: int
