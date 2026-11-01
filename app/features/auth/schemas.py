from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("username")
    @classmethod
    def normalizar_username(cls, valor: str) -> str:
        return valor.strip().lower()
