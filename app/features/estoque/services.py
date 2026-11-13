"""Regras de negócio do estoque, orquestrando o repository."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from datetime import date

from flask_sqlalchemy.pagination import Pagination

from app.utils.constantes import Constantes
from app.utils.errors import RegistroNaoEncontrado
from app.utils.paginacao import PaginacaoQuery

from . import models, schemas
from .repository import EstoqueRepository


@dataclass
class UsoDeItem:
    """Quanto uma movimentação tira de um item do lote."""
    item: models.ItemLote
    quantidade: float


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
            
            if(not self.repository.lote_tem_itens(origem.id)
                    and _vencido(origem.data_validade)
                    and dados.tipo != "SAIDA"):
                raise ValueError("Lote vencido: Só é permitida saída")

            destino = None
            if dados.lote_destino_id is not None:
                destino = self._validar_lote_destino(origem, dados)

            if self.repository.lote_tem_itens(origem.id):
                return self._movimentar_lote_com_itens(origem, destino, dados)
            return self._movimentar_lote_sem_itens(origem, destino, dados)

    def _movimentar_lote_sem_itens(self, origem, destino, dados) -> models.MovimentacaoEstoque:
        """Lote controlado só pela quantidade total (o comportamento original)."""
        if dados.item_ids is not None:
            raise ValueError("o lote de origem não possui itens cadastrados")

        destino_tem_itens = destino is not None and self.repository.lote_tem_itens(destino.id)
        if dados.tipo == "TRANSFERENCIA" and destino_tem_itens:
            raise ValueError("o lote de destino é controlado por itens e a origem não")

        if dados.tipo in Constantes.TIPOS_QUE_EXIGEM_SAIDA and origem.quantidade < dados.quantidade:
            raise ValueError("saldo insuficiente")

        movimentacao = self._gravar_movimentacao(dados, origem, destino, dados.quantidade)

        if dados.tipo == "TRANSFORMACAO" and destino_tem_itens:
            self._registrar_resultado_como_item(destino, movimentacao, dados.quantidade_destino)
            self._recalcular_lote(destino)
        return movimentacao

    def _movimentar_lote_com_itens(self, origem, destino, dados) -> models.MovimentacaoEstoque:
        """Lote com itens: a saída sai dos itens e o saldo do lote é recalculado."""
        if dados.tipo in Constantes.TIPOS_SOMAM_NA_ORIGEM:
            raise ValueError(
                "lote controlado por itens: registre entradas em POST /api/estoque/lotes/{id}/itens"
            )

        if dados.item_ids is not None:
            usos = self._usar_itens_escolhidos(origem, dados.item_ids, dados.tipo)
        elif dados.tipo == "TRANSFERENCIA":
            raise ValueError("lote controlado por itens: informe os itens a transferir (item_ids)")
        else:
            usos = self._usar_itens_por_validade(origem, dados.quantidade)

        destino_tem_itens = destino is not None and self.repository.lote_tem_itens(destino.id)
        if dados.tipo == "TRANSFERENCIA" and not destino_tem_itens and destino.quantidade > 0:
            raise ValueError("o lote de destino tem saldo sem itens; escolha outro lote")

        quantidade = self._total_dos_usos(usos, origem)
        movimentacao = self._gravar_movimentacao(dados, origem, destino, quantidade)
        self._vincular_usos(movimentacao, usos)

        if dados.tipo == "TRANSFERENCIA":
            self._mover_itens(usos, destino)
        else:
            self._baixar_itens(usos)

        if dados.tipo == "TRANSFORMACAO" and destino_tem_itens:
            self._registrar_resultado_como_item(destino, movimentacao, dados.quantidade_destino)

        self._recalcular_lote(origem)
        if destino is not None:
            self._recalcular_lote(destino)
        return movimentacao

    def _usar_itens_escolhidos(self, origem, item_ids: list[int], tipo: str) -> list[UsoDeItem]:
        """Itens escolhidos pelo usuário saem por inteiro."""
        itens = self.repository.itens_por_ids(item_ids)
        if len(itens) != len(item_ids):
            raise ValueError("item não encontrado")

        usos = []
        for item in itens:
            if item.lote_id != origem.id:
                raise ValueError(f"o item {item.codigo} não pertence ao lote {origem.id}")
            if item.status not in Constantes.STATUS_ITEM_LIVRES:
                raise ValueError(f"o item {item.codigo} não está disponível ({item.status})")
            if _vencido(item.data_validade) and tipo != "SAIDA":
                raise ValueError(f"o item {item.codigo} está vencido: só é permitida a saída")
            usos.append(UsoDeItem(item=item, quantidade=item.saldo))
        return usos

    def _usar_itens_por_validade(self, origem, quantidade: float) -> list[UsoDeItem]:
        """Tira a quantidade dos itens abertos primeiro e depois dos que vencem antes."""
        usos = []
        falta = quantidade
        for item in self.repository.itens_fefo(origem.id):
            if falta <= 0:
                break
            usar = min(item.saldo, falta)
            usos.append(UsoDeItem(item=item, quantidade=usar))
            falta = _arredondar(falta - usar)

        if falta > 0:
            raise ValueError("saldo insuficiente nos itens disponíveis (itens vencidos só saem escolhendo-os em uma saída)")
        return usos

    def _total_dos_usos(self, usos: list[UsoDeItem], origem) -> float:
        total = _arredondar(sum(uso.quantidade for uso in usos))
        if total > origem.quantidade:
            return origem.quantidade
        return total

    def _vincular_usos(self, movimentacao, usos: list[UsoDeItem]) -> None:
        for uso in usos:
            self.repository.vincular_item(movimentacao.id, uso.item.id, uso.quantidade)

    def _mover_itens(self, usos: list[UsoDeItem], destino) -> None:
        """Na transferência o item muda de lote e mantém o código."""
        for uso in usos:
            uso.item.lote_id = destino.id

    def _baixar_itens(self, usos: list[UsoDeItem]) -> None:
        """Desconta o saldo; item zerado fica consumido, item usado em parte fica aberto."""
        for uso in usos:
            item = uso.item
            item.saldo = _arredondar(item.saldo - uso.quantidade)
            if item.saldo <= 0:
                item.saldo = 0
                item.status = "CONSUMIDA"
            else:
                item.status = "EM_USO"
                if item.aberto_em is None:
                    item.aberto_em = _agora()

    def _registrar_resultado_como_item(self, destino, movimentacao, quantidade: float) -> None:
        """O resultado da transformação entra como um item novo no lote de destino."""
        sequencia = self.repository.proxima_sequencia(destino.id)
        item = self._novo_item(destino, sequencia, quantidade=quantidade, data_validade=destino.data_validade)
        self.repository.inserir_itens([item])
        self.repository.vincular_item(movimentacao.id, item.id, item.quantidade)

    def _recalcular_lote(self, lote) -> None:
        """Em lote com itens: saldo é a soma dos itens e vencimento é a menor validade."""
        itens = self.repository.itens_ativos(lote.id)
        lote.quantidade = _arredondar(sum(item.saldo for item in itens))

        validades = [item.data_validade for item in itens if item.data_validade]
        if validades:
            lote.data_validade = min(validades)

    def _gravar_movimentacao(self, dados, origem, destino, quantidade: float):
        return self.repository.inserir_movimentacao(
            tipo=dados.tipo,
            lote_origem=origem,
            lote_destino=destino,
            quantidade=quantidade,
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
            self._validar_data_validade(dados.data_validade)
            self._validar_conservacao_compativel(produto, localizacao)
            lote = self.repository.inserir_lote(
                produto_id=dados.produto_id,
                localizacao_id=dados.localizacao_id,
                data_producao=_data_iso(dados.data_producao),
                data_validade=_data_iso(dados.data_validade),
                custo_unitario=dados.custo_unitario,
                fornecedor=dados.fornecedor,
                nota_fiscal=dados.nota_fiscal,
            )
            if dados.itens:
                self._validar_usuario_ativo(dados.usuario_id)
                self._dar_entrada_em_itens(
                    lote, produto, dados.itens, dados.usuario_id, dados.observacao
                )
            return lote

    # -- itens do lote ---------------------------------------------------------

    def adicionar_itens(self, lote_id: int, dados: schemas.ItensLoteCreate) -> list[models.ItemLote]:
        with self.repository.transacao():
            lote = self.repository.obter_lote(lote_id, para_atualizacao=True)
            if lote is None:
                raise RegistroNaoEncontrado("lote não encontrado")
            self._validar_usuario_ativo(dados.usuario_id)
            if lote.quantidade > 0 and not self.repository.lote_tem_itens(lote.id):
                raise ValueError("o lote tem saldo sem itens cadastrados; crie um novo lote")
            produto = self.repository.obter_produto(lote.produto_id)
            return self._dar_entrada_em_itens(
                lote, produto, dados.itens, dados.usuario_id, dados.observacao
            )

    def _dar_entrada_em_itens(self, lote, produto, grupos, usuario_id, observacao):
        """Cria os itens dos grupos, lança uma ENTRADA com o total e liga os dois."""
        itens = []
        sequencia = self.repository.proxima_sequencia(lote.id)
        for grupo in grupos:
            validade = self._validade_do_grupo(lote, produto, grupo)
            for _ in range(grupo.quantidade_unidades):
                itens.append(self._novo_item(
                    lote,
                    sequencia,
                    quantidade=grupo.quantidade,
                    fabricante=grupo.fabricante,
                    data_fabricacao=_data_iso(grupo.data_fabricacao),
                    data_validade=validade,
                ))
                sequencia += 1
        self.repository.inserir_itens(itens)

        total = _arredondar(sum(item.quantidade for item in itens))
        movimentacao = self.repository.inserir_movimentacao(
            tipo="ENTRADA",
            lote_origem=lote,
            lote_destino=None,
            quantidade=total,
            quantidade_destino=None,
            motivo=None,
            usuario_id=usuario_id,
            observacao=observacao,
        )
        for item in itens:
            self.repository.vincular_item(movimentacao.id, item.id, item.quantidade)
        self._recalcular_lote(lote)
        return itens

    def _validade_do_grupo(self, lote, produto, grupo: schemas.GrupoItensCreate) -> Optional[str]:
        """Sem validade própria, o grupo usa a validade do lote."""
        validade = _data_iso(grupo.data_validade) or lote.data_validade
        if produto.validade_obrigatoria and not validade:
            raise ValueError("produto exige data_validade nos itens")
        if _vencido(validade):
            raise ValueError("a validade do grupo já venceu; informe uma validade futura")
        return validade

    def _novo_item(self, lote, sequencia: int, *, quantidade, data_validade,
                   fabricante=None, data_fabricacao=None) -> models.ItemLote:
        """Monta um item do lote com o código FT-<lote>-<sequência> (ex.: FT-003-07)."""
        return models.ItemLote(
            lote_id=lote.id,
            lote_origem_id=lote.id,
            sequencia=sequencia,
            codigo=f"{Constantes.PREFIXO_CODIGO_ITEM}-{lote.id:03d}-{sequencia:02d}",
            quantidade=quantidade,
            saldo=quantidade,
            fabricante=fabricante,
            data_fabricacao=data_fabricacao,
            data_validade=data_validade,
            status="DISPONIVEL",
        )

    def listar_itens(self, lote_id: int, filtro: schemas.ItemLoteQuery) -> Pagination:
        self._obter_lote_ou_404(lote_id)
        return self.repository.listar_itens(filtro, lote_id, filtro.status)

    def obter_item(self, item_id: int) -> models.ItemLote:
        item = self.repository.obter_item(item_id)
        if item is None:
            raise RegistroNaoEncontrado("item não encontrado")
        return item

    def atualizar_item(self, item_id: int, dados: schemas.ItemLoteUpdate) -> models.ItemLote:
        campos = dados.model_dump(exclude_unset=True, mode="json")
        if "fabricante" in campos:
            campos["fabricante"] = _limpar_texto(campos["fabricante"])
        with self.repository.transacao():
            item = self.repository.obter_item(item_id, para_atualizacao=True)
            if item is None:
                raise RegistroNaoEncontrado("item não encontrado")
            lote = self.repository.obter_lote(item.lote_id, para_atualizacao=True)
            produto = self.repository.obter_produto(lote.produto_id)
            fabricacao = campos.get("data_fabricacao", item.data_fabricacao)
            validade = campos.get("data_validade", item.data_validade)
            self._validar_validade_obrigatoria(produto, validade, "produto exige data_validade")
            if "data_validade" in campos and campos["data_validade"] != item.data_validade:
                self._validar_data_validade(validade)
            if fabricacao and validade and fabricacao > validade:
                raise ValueError("validade do item anterior à fabricação")
            for campo, valor in campos.items():
                setattr(item, campo, valor)
            self._recalcular_lote(lote)
            return item

    def abrir_item(self, item_id: int) -> models.ItemLote:
        with self.repository.transacao():
            item = self.repository.obter_item(item_id, para_atualizacao=True)
            if item is None:
                raise RegistroNaoEncontrado("item não encontrado")
            if item.status != "DISPONIVEL":
                raise ValueError(f"somente itens disponíveis podem ser abertos (atual: {item.status})")
            item.status = "EM_USO"
            if _vencido(item.data_validade):
                raise ValueError("item vencido não pode ser aberto")
            item.aberto_em = _agora()
            return item

    def atualizar_lote(self, lote_id: int, dados: schemas.LoteUpdate) -> models.Lote:
        campos = dados.model_dump(exclude_unset=True, mode="json")
        for campo in ("fornecedor", "nota_fiscal"):
            if campo in campos:
                campos[campo] = _limpar_texto(campos[campo])

        with self.repository.transacao():
            lote = self._obter_lote_ou_404(lote_id)
            validade = campos.get("data_validade", lote.data_validade)
            producao = campos.get("data_producao", lote.data_producao)
            produto = self.repository.obter_produto(lote.produto_id)
            self._validar_validade_obrigatoria(produto, validade, "validade obrigatória")
            if "data_validade" in campos and campos["data_validade"] != lote.data_validade:
                self._validar_data_validade(validade)
            if producao and validade and producao > validade:
                raise ValueError("validade anterior à produção")
            if "localizacao_id" in campos:
                self._validar_nova_localizacao(produto, campos["localizacao_id"])
            self.repository.atualizar_lote(lote_id, campos)
            return self.repository.obter_lote(lote_id)

    def _validar_nova_localizacao(self, produto, localizacao_id: Optional[int]) -> None:
        """O lote inteiro (com seus itens) muda de lugar; o local precisa servir ao produto."""
        if localizacao_id is None:
            raise ValueError("localização obrigatória")
        localizacao = self.repository.obter_localizacao(localizacao_id)
        if localizacao is None:
            raise ValueError("localização não encontrada")
        self._validar_conservacao_compativel(produto, localizacao)

    def _buscar_produto_e_localizacao(self, produto_id: int, localizacao_id: int):
        produto = self.repository.obter_produto_ativo(produto_id)
        localizacao = self.repository.obter_localizacao(localizacao_id)
        if not produto or not localizacao:
            raise ValueError("produto ativo ou localização não encontrados")
        return produto, localizacao

    def _validar_validade_obrigatoria(self, produto, data_validade, mensagem: str) -> None:
        if produto.validade_obrigatoria and not data_validade:
            raise ValueError(mensagem)
        
        
    def _validar_data_validade(self, data_validade) -> None:
        if _vencido(data_validade):
            raise ValueError("Não é permitido cadastrar lote vencido.")

    def _validar_conservacao_compativel(self, produto, localizacao) -> None:
        if produto.conservacao != localizacao.tipo:
            raise ValueError("conservação do produto incompatível com localização")

    def _obter_lote_ou_404(self, lote_id: int):
        lote = self.repository.obter_lote(lote_id)
        if lote is None:
            raise RegistroNaoEncontrado("lote não encontrado")
        return lote


def _agora() -> str:
    """Data e hora no mesmo formato do CURRENT_TIMESTAMP gravado em criado_em."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _arredondar(valor: float) -> float:
    """Evita sobras como 0.30000000000000004 nas contas de saldo."""
    return round(valor, 6)


def _data_iso(data) -> Optional[str]:
    return data.isoformat() if data else None


def _limpar_texto(texto: Optional[str]) -> Optional[str]:
    """Tira espaços das pontas; texto vazio vira None."""
    if texto is None:
        return None
    return texto.strip() or None

def _como_data(valor) -> Optional[date]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])

def _vencido(valor) -> bool:
    data = _como_data(valor)
    return data is not None and data < date.today()
