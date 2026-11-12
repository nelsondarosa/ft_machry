from decimal import Decimal

from flask_sqlalchemy.pagination import Pagination
from pydantic import ValidationError

from app.utils.errors import Conflito, RegistroNaoEncontrado, mensagem_validacao
from app.utils.paginacao import PaginacaoQuery
from app.utils.texto import normalizar_nome

from .models import FichaTecnica
from .repository import FichaTecnicaRepository
from .schemas import FichaLoteInput, FichaLoteItem, FichaTecnicaInput

# Fatores para a unidade base de cada grandeza (massa em g, volume em ml).
UNIDADES = {
    "mg": ("massa", Decimal("0.001")), "g": ("massa", Decimal(1)), "kg": ("massa", Decimal(1000)),
    "ml": ("volume", Decimal(1)), "l": ("volume", Decimal(1000)),
}


def converter_quantidade(quantidade: Decimal, origem: str | None, destino: str, produto: str) -> Decimal:
    """Converte a quantidade da unidade informada para a unidade do produto."""
    if not origem or origem.strip().lower() == destino.strip().lower():
        return quantidade
    de, para = UNIDADES.get(origem.strip().lower()), UNIDADES.get(destino.strip().lower())
    if de is None or para is None or de[0] != para[0]:
        raise ValueError(
            f"unidade '{origem}' não pode ser convertida para '{destino}' (unidade de {produto})"
        )
    return quantidade * de[1] / para[1]


class FichaTecnicaService:
    def __init__(self, repository: FichaTecnicaRepository) -> None:
        self.repository = repository

    def listar(self, paginacao: PaginacaoQuery) -> Pagination:
        return self.repository.listar(paginacao)

    def obter(self, ficha_id: int) -> FichaTecnica:
        ficha = self.repository.obter(ficha_id)
        if ficha is None:
            raise RegistroNaoEncontrado("ficha técnica não encontrada")
        return ficha

    def listar_fases(self, paginacao: PaginacaoQuery) -> Pagination:
        return self.repository.fases_catalogo(paginacao)

    def criar(self, dados: FichaTecnicaInput) -> FichaTecnica:
        with self.repository.transacao():
            self._validar(dados)
            ficha = self.repository.inserir(
                produto_id=dados.produto_id,
                rendimento=dados.rendimento,
                observacao=dados.observacao,
            )
            self.repository.substituir_conteudo(ficha, dados)
            ficha_id = ficha.id
        return self.obter(ficha_id)

    def criar_lote(self, dados: FichaLoteInput) -> tuple[list[FichaTecnica], list[str]]:
        """Cria várias fichas referenciando produtos e fases pelo nome; tudo ou nada.

        Fases ausentes do catálogo são criadas. Componentes sem quantidade ("a gosto")
        não entram na ficha e são listados na observação.
        """
        itens: list[FichaLoteItem] = []
        for posicao, bruto in enumerate(dados.fichas, start=1):
            try:
                itens.append(FichaLoteItem.model_validate(bruto))
            except ValidationError as exc:
                campo = ".".join(str(parte) for parte in exc.errors()[0]["loc"])
                raise ValueError(f"ficha {posicao}: {campo + ': ' if campo else ''}{mensagem_validacao(exc)}") from exc

        with self.repository.transacao():
            produtos: dict[str, list] = {}
            for produto in self.repository.produtos_ativos():
                produtos.setdefault(normalizar_nome(produto.nome), []).append(produto)
            fases = {normalizar_nome(fase.nome): fase for fase in self.repository.fases_todas()}
            fases_criadas: list[str] = []

            def buscar_produto(nome: str):
                encontrados = produtos.get(normalizar_nome(nome), [])
                if not encontrados:
                    raise ValueError(f"produto '{nome}' não encontrado")
                if len(encontrados) > 1:
                    raise ValueError(f"nome '{nome}' corresponde a mais de um produto; renomeie para diferenciar")
                return encontrados[0]

            fichas_ids = []
            for posicao, item in enumerate(itens, start=1):
                try:
                    produto = buscar_produto(item.produto)
                    fases_entrada = []
                    for fase in item.fases:
                        chave = normalizar_nome(fase.fase)
                        if chave not in fases:
                            fases[chave] = self.repository.criar_fase(fase.fase.strip())
                            fases_criadas.append(fases[chave].nome)
                        fases_entrada.append({"fase_id": fases[chave].id, "ordem": fase.ordem, "tempo_previsto_min": fase.tempo_previsto_min})
                    componentes, a_gosto = [], []
                    for componente in item.componentes:
                        if componente.quantidade is None:
                            a_gosto.append(componente.produto.strip())
                            continue
                        alvo = buscar_produto(componente.produto)
                        quantidade = converter_quantidade(componente.quantidade, componente.unidade, alvo.unidade_medida, alvo.nome)
                        quantidade = quantidade.quantize(Decimal("0.001"))
                        if quantidade <= 0:
                            raise ValueError(f"quantidade de '{alvo.nome}' fica zerada em {alvo.unidade_medida}")
                        componentes.append({"produto_id": alvo.id, "quantidade": quantidade, "fase_ordem": componente.fase_ordem})
                    observacao = "\n".join(filter(None, [
                        (item.observacao or "").strip(),
                        f"A gosto (q.b.): {', '.join(a_gosto)}." if a_gosto else "",
                    ])) or None
                    try:
                        entrada = FichaTecnicaInput(produto_id=produto.id, rendimento=item.rendimento, observacao=observacao, fases=fases_entrada, componentes=componentes)
                    except ValidationError as exc:
                        raise ValueError(mensagem_validacao(exc)) from exc
                    self._validar(entrada)
                    ficha = self.repository.inserir(produto_id=entrada.produto_id, rendimento=entrada.rendimento, observacao=entrada.observacao)
                    self.repository.substituir_conteudo(ficha, entrada)
                    fichas_ids.append(ficha.id)
                except (ValueError, Conflito) as exc:
                    raise type(exc)(f"ficha {posicao} ({item.produto}): {exc}") from exc
        return [self.obter(ficha_id) for ficha_id in fichas_ids], fases_criadas

    def atualizar(self, ficha_id: int, dados: FichaTecnicaInput) -> FichaTecnica:
        with self.repository.transacao():
            ficha = self.obter(ficha_id)
            self._validar(dados, ficha_id=ficha_id)
            self.repository.substituir_conteudo(ficha, dados)
        return self.obter(ficha_id)

    def remover(self, ficha_id: int) -> None:
        with self.repository.transacao():
            ficha = self.obter(ficha_id)
            if self.repository.possui_solicitacao(ficha_id):
                raise Conflito(
                    "a ficha possui solicitações de produção e não pode ser excluída"
                )
            self.repository.remover(ficha)

    def _validar(self, dados: FichaTecnicaInput, ficha_id: int | None = None) -> None:
        produto = self.repository.obter_produto(dados.produto_id)
        if produto is None or not produto.ativo:
            raise ValueError("produto final não encontrado ou inativo")
        if produto.tipo == "INSUMO":
            raise ValueError("um insumo não pode possuir ficha técnica")

        existente = self.repository.ficha_do_produto(dados.produto_id)
        if existente is not None and existente.id != ficha_id:
            raise Conflito("o produto já possui uma ficha técnica")

        componente_ids = {item.produto_id for item in dados.componentes}
        if dados.produto_id in componente_ids:
            raise ValueError("o produto final não pode ser componente da própria ficha")
        encontrados = self.repository.produtos_ativos_por_ids(componente_ids)
        ausentes = sorted(componente_ids - encontrados.keys())
        if ausentes:
            raise ValueError(
                "componentes não encontrados ou inativos: "
                + ", ".join(str(item) for item in ausentes)
            )

        fase_ids = {item.fase_id for item in dados.fases}
        fases = self.repository.fases_catalogo_por_ids(fase_ids)
        ausentes = sorted(fase_ids - fases.keys())
        if ausentes:
            raise ValueError(
                "fases de produção não encontradas: "
                + ", ".join(str(item) for item in ausentes)
            )
