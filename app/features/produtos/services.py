from flask_sqlalchemy.pagination import Pagination
from pydantic import ValidationError

from app.utils.errors import RegistroNaoEncontrado, mensagem_validacao
from app.utils.paginacao import PaginacaoQuery
from app.utils.texto import normalizar_nome

from .models import Produto
from .repository import ProdutoRepository
from .schemas import ProdutoCreate, ProdutoLoteCreate, ProdutoUpdate


class ProdutoService:
    def __init__(self, repository: ProdutoRepository) -> None:
        self.repository = repository

    def listar(self, paginacao: PaginacaoQuery) -> Pagination:
        return self.repository.listar_ativos(paginacao)

    def obter(self, produto_id: int) -> Produto:
        produto = self.repository.obter_ativo(produto_id)
        if produto is None:
            raise RegistroNaoEncontrado("produto não encontrado")
        return produto

    def criar(self, dados: ProdutoCreate) -> Produto:
        with self.repository.transacao():
            self._validar_grupo(dados.grupo_id)
            return self.repository.inserir(dados.model_dump())

    def criar_lote(self, dados: ProdutoLoteCreate) -> tuple[list[Produto], list[str]]:
        """Cria todos os produtos ou nenhum; erros indicam a posição do item.

        Produtos com o mesmo nome e conservação de um produto ativo são ignorados,
        para que reimportar um arquivo não duplique o catálogo.
        """
        itens: list[ProdutoCreate] = []
        for posicao, bruto in enumerate(dados.produtos, start=1):
            try:
                itens.append(ProdutoCreate.model_validate(bruto))
            except ValidationError as exc:
                campo = ".".join(str(parte) for parte in exc.errors()[0]["loc"])
                detalhe = f"{campo}: " if campo else ""
                raise ValueError(f"produto {posicao}: {detalhe}{mensagem_validacao(exc)}") from exc
        with self.repository.transacao():
            existentes = {(normalizar_nome(p.nome), p.conservacao) for p in self.repository.ativos()}
            criados, ignorados = [], []
            for posicao, item in enumerate(itens, start=1):
                if (normalizar_nome(item.nome), item.conservacao) in existentes:
                    ignorados.append(item.nome)
                    continue
                try:
                    self._validar_grupo(item.grupo_id)
                except ValueError as exc:
                    raise ValueError(f"produto {posicao}: {exc}") from exc
                criados.append(self.repository.inserir(item.model_dump()))
            return criados, ignorados

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
