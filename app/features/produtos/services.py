from app.utils.errors import RegistroNaoEncontrado

from .models import Produto
from .repository import ProdutoRepository
from .schemas import ProdutoCreate, ProdutoUpdate


class ProdutoService:
    def __init__(self, repository: ProdutoRepository) -> None:
        self.repository = repository

    def listar(self) -> list[Produto]:
        return self.repository.listar_ativos()

    def obter(self, produto_id: int) -> Produto:
        produto = self.repository.obter_ativo(produto_id)
        if produto is None:
            raise RegistroNaoEncontrado("produto não encontrado")
        return produto

    def criar(self, dados: ProdutoCreate) -> Produto:
        with self.repository.transacao():
            self._validar_grupo(dados.grupo_id)
            return self.repository.inserir(dados.model_dump())

    def atualizar(self, produto_id: int, dados: ProdutoUpdate) -> Produto:
        with self.repository.transacao():
            produto = self.obter(produto_id)
            campos = dados.model_dump(exclude_unset=True)
            if "grupo_id" in campos:
                self._validar_grupo(campos["grupo_id"])
            if campos.get("tipo") == "INSUMO" and self.repository.possui_ficha(produto_id):
                raise ValueError("produto com ficha técnica não pode se tornar insumo")
            return self.repository.atualizar(produto, campos)

    def remover(self, produto_id: int) -> None:
        with self.repository.transacao():
            self.repository.desativar(self.obter(produto_id))

    def _validar_grupo(self, grupo_id: int | None) -> None:
        if grupo_id is not None and not self.repository.grupo_existe(grupo_id):
            raise ValueError("grupo de produto não encontrado")
