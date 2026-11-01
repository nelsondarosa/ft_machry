from werkzeug.security import generate_password_hash

from app.utils.errors import Conflito, RegistroNaoEncontrado

from .models import Usuario
from .repository import UsuarioRepository
from .schemas import UsuarioCreate, UsuarioUpdate


class UsuarioService:
    def __init__(self, repository: UsuarioRepository) -> None:
        self.repository = repository

    def listar(self) -> list[Usuario]:
        return self.repository.listar()

    def obter(self, usuario_id: int) -> Usuario:
        usuario = self.repository.obter(usuario_id)
        if usuario is None:
            raise RegistroNaoEncontrado("usuário não encontrado")
        return usuario

    def criar(self, dados: UsuarioCreate) -> Usuario:
        username = dados.username.lower()
        with self.repository.transacao():
            if self.repository.obter_por_username(username):
                raise Conflito("nome de usuário já cadastrado")
            return self.repository.inserir(
                {
                    "nome": dados.nome,
                    "username": username,
                    "senha_hash": generate_password_hash(dados.password),
                    "papel": dados.papel,
                }
            )

    def atualizar(self, usuario_id: int, dados: UsuarioUpdate, usuario_logado_id: int) -> Usuario:
        with self.repository.transacao():
            usuario = self.obter(usuario_id)
            if dados.nome is not None:
                usuario.nome = dados.nome.strip()
            if dados.password is not None:
                usuario.senha_hash = generate_password_hash(dados.password)
            if dados.papel is not None:
                usuario.papel = dados.papel
            if dados.ativo is not None:
                if usuario.id == usuario_logado_id and not dados.ativo:
                    raise Conflito("a conta em uso não pode ser desativada")
                usuario.ativo = dados.ativo
            return usuario
