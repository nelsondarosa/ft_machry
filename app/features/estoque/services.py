"""Regras de negócio do estoque, orquestrando o repository."""
from __future__ import annotations

from typing import Optional

from flask_sqlalchemy.pagination import Pagination

from app.utils.constantes import Constantes
from app.utils.errors import RegistroNaoEncontrado
from app.utils.paginacao import PaginacaoQuery

from . import models, schemas
from .repository import EstoqueRepository


class EstoqueService:
    def __init__(self, repository: EstoqueRepository) -> None:
        self.repository = repository

    def listar_inventario(
        self,
        paginacao: PaginacaoQuery,
        produto_id: Optional[int] = None,
        lote_id: Optional[int] = None,
    ) -> Pagination:
        pagina = self.repository.listar_inventario(paginacao, produto_id, lote_id)
        pagina.items = [models.ItemInventario.from_row(r) for r in pagina.items]
        return pagina

    def listar_movimentacoes(
        self,
        paginacao: PaginacaoQuery,
        lote_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
        tipo: Optional[str] = None,
    ) -> Pagination:
        pagina = self.repository.listar_movimentacoes(paginacao, lote_id, usuario_id, tipo)
        pagina.items = [models.MovimentacaoEstoque.from_row(r) for r in pagina.items]
        return pagina

    def registrar_movimentacao(
        self, dados: schemas.MovimentacaoCreate
    ) -> models.MovimentacaoEstoque:
        with self.repository.transacao():
            origem = self._obter_lote_ou_falhar(dados.lote_id, para_atualizacao=True)
            self._validar_usuario_ativo(dados.usuario_id)
            self._validar_saldo_suficiente(origem, dados)
            destino = None
            if dados.lote_destino_id is not None:
                destino = self._validar_lote_destino(origem, dados)
            return self.repository.inserir_movimentacao(
                tipo=dados.tipo,
                lote_origem=origem,
                lote_destino=destino,
                quantidade=dados.quantidade,
                quantidade_destino=dados.quantidade_destino,
                motivo=dados.motivo,
                usuario_id=dados.usuario_id,
                observacao=dados.observacao,
            )

    def sugestao_saida(self, produto_id: int, quantidade: float) -> models.SugestaoSaida:
        if self.repository.obter_produto_ativo(produto_id) is None:
            raise RegistroNaoEncontrado("produto não encontrado")
        faltante = quantidade
        selecao: list[models.LoteSugerido] = []
        for lote in self.repository.lotes_fefo_disponiveis(produto_id):
            usar = min(faltante, lote["quantidade"])
            if usar > 0:
                selecao.append(
                    models.LoteSugerido(
                        lote_id=lote["id"], quantidade=usar, data_validade=lote["data_validade"]
                    )
                )
                faltante -= usar
            if faltante <= 0:
                break
        return models.SugestaoSaida(
            produto_id=produto_id,
            quantidade_solicitada=quantidade,
            lotes=selecao,
            quantidade_faltante=max(0, faltante),
        )

    def _obter_lote_ou_falhar(self, lote_id: int, para_atualizacao: bool = False):
        lote = self.repository.obter_lote(lote_id, para_atualizacao=para_atualizacao)
        if lote is None:
            raise ValueError(f"lote {lote_id} não encontrado")
        return lote

    def _validar_usuario_ativo(self, usuario_id: int) -> None:
        if self.repository.obter_usuario_ativo(usuario_id) is None:
            raise ValueError("usuário não encontrado ou inativo")

    def _validar_saldo_suficiente(self, origem, dados: schemas.MovimentacaoCreate) -> None:
        if dados.tipo in Constantes.TIPOS_QUE_EXIGEM_SAIDA and origem.quantidade < dados.quantidade:
            raise ValueError("saldo insuficiente")

    def _validar_lote_destino(self, origem, dados: schemas.MovimentacaoCreate):
        destino = self._obter_lote_ou_falhar(dados.lote_destino_id, para_atualizacao=True)
        local_destino = self.repository.obter_localizacao(destino.localizacao_id)
        produto_destino = self.repository.obter_produto(destino.produto_id)
        if (
            not local_destino
            or not produto_destino
            or produto_destino.conservacao != local_destino.tipo
        ):
            raise ValueError("lote destino com conservação incompatível")
        if dados.tipo == "TRANSFERENCIA" and origem.produto_id != destino.produto_id:
            raise ValueError("transferência requer mesmo produto")
        if dados.tipo == "TRANSFORMACAO" and not self.repository.transformacao_cadastrada(
            origem.produto_id, destino.produto_id
        ):
            raise ValueError("transformação não cadastrada entre os produtos")
        return destino

    def listar_localizacoes(self, paginacao: PaginacaoQuery) -> Pagination:
        return self.repository.listar_localizacoes(paginacao)

    def criar_localizacao(self, dados: schemas.LocalizacaoCreate) -> models.Localizacao:
        with self.repository.transacao():
            if dados.parent_id is not None:
                self._validar_localizacao_existe(dados.parent_id)
            return self.repository.inserir_localizacao(
                nome=dados.nome, tipo=dados.tipo, parent_id=dados.parent_id, foto_url=dados.foto_url
            )

    def atualizar_localizacao(
        self, loc_id: int, dados: schemas.LocalizacaoUpdate
    ) -> models.Localizacao:
        campos = dados.model_dump(exclude_unset=True)

        with self.repository.transacao():
            self._obter_localizacao_ou_falhar(loc_id)
            if "parent_id" in campos and campos["parent_id"] is not None:
                self._validar_novo_parent(loc_id, campos["parent_id"])
            if "tipo" in campos and self.repository.existe_incompatibilidade_tipo(
                loc_id, campos["tipo"]
            ):
                raise ValueError(
                    "alteração de tipo incompatível com produtos dos lotes existentes"
                )
            self.repository.atualizar_localizacao(loc_id, campos)
            return self.repository.obter_localizacao(loc_id)

    def remover_localizacao(self, loc_id: int) -> None:
        with self.repository.transacao():
            if not self.repository.remover_localizacao(loc_id):
                raise RegistroNaoEncontrado("localização não encontrada")

    def _obter_localizacao_ou_falhar(self, loc_id: int):
        localizacao = self.repository.obter_localizacao(loc_id)
        if localizacao is None:
            raise RegistroNaoEncontrado("localização não encontrada")
        return localizacao

    def _validar_localizacao_existe(self, loc_id: int) -> None:
        if self.repository.obter_localizacao(loc_id) is None:
            raise ValueError("localização pai não encontrada")

    def _validar_novo_parent(self, loc_id: int, pai: int) -> None:
        self._validar_localizacao_existe(pai)
        if pai == loc_id:
            raise ValueError("localização não pode ser pai de si mesma")
        visitados = {loc_id}
        atual = pai
        while atual is not None:
            if atual in visitados:
                raise ValueError("hierarquia de localização circular")
            visitados.add(atual)
            atual = self.repository.obter_localizacao(atual).parent_id

    def listar_lotes(
        self,
        paginacao: PaginacaoQuery,
        produto_id: Optional[int] = None,
        localizacao_id: Optional[int] = None,
    ) -> Pagination:
        pagina = self.repository.listar_lotes(paginacao, produto_id, localizacao_id)
        pagina.items = [models.LoteListado.from_row(r) for r in pagina.items]
        return pagina

    def obter_lote(self, lote_id: int) -> Optional[models.Lote]:
        return self.repository.obter_lote(lote_id)

    def criar_lote(self, dados: schemas.LoteCreate) -> models.Lote:
        with self.repository.transacao():
            produto, localizacao = self._buscar_produto_e_localizacao(
                dados.produto_id, dados.localizacao_id
            )
            self._validar_validade_obrigatoria(
                produto, dados.data_validade, "produto exige data_validade"
            )
            self._validar_conservacao_compativel(produto, localizacao)
            return self.repository.inserir_lote(
                produto_id=dados.produto_id,
                localizacao_id=dados.localizacao_id,
                data_producao=dados.data_producao.isoformat() if dados.data_producao else None,
                data_validade=dados.data_validade.isoformat() if dados.data_validade else None,
                custo_unitario=dados.custo_unitario,
            )

    def atualizar_lote(self, lote_id: int, dados: schemas.LoteUpdate) -> models.Lote:
        campos = dados.model_dump(exclude_unset=True, mode="json")

        with self.repository.transacao():
            lote = self._obter_lote_ou_404(lote_id)
            validade = campos.get("data_validade", lote.data_validade)
            producao = campos.get("data_producao", lote.data_producao)
            produto = self.repository.obter_produto(lote.produto_id)
            self._validar_validade_obrigatoria(produto, validade, "validade obrigatória")
            if producao and validade and producao > validade:
                raise ValueError("validade anterior à produção")
            self.repository.atualizar_lote(lote_id, campos)
            return self.repository.obter_lote(lote_id)

    def _buscar_produto_e_localizacao(self, produto_id: int, localizacao_id: int):
        produto = self.repository.obter_produto_ativo(produto_id)
        localizacao = self.repository.obter_localizacao(localizacao_id)
        if not produto or not localizacao:
            raise ValueError("produto ativo ou localização não encontrados")
        return produto, localizacao

    def _validar_validade_obrigatoria(self, produto, data_validade, mensagem: str) -> None:
        if produto.validade_obrigatoria and not data_validade:
            raise ValueError(mensagem)

    def _validar_conservacao_compativel(self, produto, localizacao) -> None:
        if produto.conservacao != localizacao.tipo:
            raise ValueError("conservação do produto incompatível com localização")

    def _obter_lote_ou_404(self, lote_id: int):
        lote = self.repository.obter_lote(lote_id)
        if lote is None:
            raise RegistroNaoEncontrado("lote não encontrado")
        return lote
