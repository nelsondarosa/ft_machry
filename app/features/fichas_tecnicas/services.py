from app.utils.errors import Conflito, RegistroNaoEncontrado

from .models import FichaTecnica
from .repository import FichaTecnicaRepository
from .schemas import FichaTecnicaInput


class FichaTecnicaService:
    def __init__(self, repository: FichaTecnicaRepository) -> None:
        self.repository = repository

    def listar(self) -> list[FichaTecnica]:
        return self.repository.listar()

    def obter(self, ficha_id: int) -> FichaTecnica:
        ficha = self.repository.obter(ficha_id)
        if ficha is None:
            raise RegistroNaoEncontrado("ficha técnica não encontrada")
        return ficha

    def listar_fases(self):
        return self.repository.fases_catalogo()

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
