from werkzeug.security import check_password_hash

from app.features.usuarios.models import Usuario
from app.features.usuarios.repository import UsuarioRepository

from .schemas import LoginInput


class AuthService:
    def __init__(self, repository: UsuarioRepository) -> None:
        self.repository = repository

    def autenticar(self, dados: LoginInput) -> Usuario | None:
        usuario = self.repository.obter_por_username(dados.username)
        if usuario is None or not usuario.ativo:
            return None
        if not check_password_hash(usuario.senha_hash, dados.password):
            return None
        return usuario
