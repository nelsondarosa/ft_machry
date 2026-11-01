from contextlib import contextmanager

from sqlalchemy.orm import selectinload

from app.features.produtos.models import Produto
from db.database_config import db

from .models import (
    FaseProducao,
    FichaTecnica,
    FichaTecnicaComponente,
    FichaTecnicaFase,
)


class FichaTecnicaRepository:
    @contextmanager
    def transacao(self):
        try:
            yield db.session
        except Exception:
            db.session.rollback()
            raise
        else:
            db.session.commit()

    def _consulta_completa(self):
        return db.session.query(FichaTecnica).options(
            selectinload(FichaTecnica.produto),
            selectinload(FichaTecnica.fases).selectinload(FichaTecnicaFase.fase),
            selectinload(FichaTecnica.componentes).selectinload(
                FichaTecnicaComponente.produto
            ),
            selectinload(FichaTecnica.componentes).selectinload(
                FichaTecnicaComponente.fase
            ),
        )

    def listar(self) -> list[FichaTecnica]:
        return self._consulta_completa().join(FichaTecnica.produto).order_by(Produto.nome).all()

    def obter(self, ficha_id: int) -> FichaTecnica | None:
        return self._consulta_completa().filter(FichaTecnica.id == ficha_id).first()

    def obter_produto(self, produto_id: int) -> Produto | None:
        return db.session.get(Produto, produto_id)

    def ficha_do_produto(self, produto_id: int) -> FichaTecnica | None:
        return db.session.query(FichaTecnica).filter_by(produto_id=produto_id).first()

    def fases_catalogo(self) -> list[FaseProducao]:
        return db.session.query(FaseProducao).order_by(FaseProducao.nome).all()

    def fases_catalogo_por_ids(self, ids: set[int]) -> dict[int, FaseProducao]:
        if not ids:
            return {}
        fases = db.session.query(FaseProducao).filter(FaseProducao.id.in_(ids)).all()
        return {fase.id: fase for fase in fases}

    def produtos_ativos_por_ids(self, ids: set[int]) -> dict[int, Produto]:
        produtos = (
            db.session.query(Produto)
            .filter(Produto.id.in_(ids), Produto.ativo == 1)
            .all()
        )
        return {produto.id: produto for produto in produtos}

    def inserir(self, *, produto_id, rendimento, observacao) -> FichaTecnica:
        ficha = FichaTecnica(
            produto_id=produto_id, rendimento=rendimento, observacao=observacao
        )
        db.session.add(ficha)
        db.session.flush()
        return ficha

    def substituir_conteudo(self, ficha: FichaTecnica, dados) -> None:
        ficha.produto_id = dados.produto_id
        ficha.rendimento = dados.rendimento
        ficha.observacao = dados.observacao

        ficha.componentes.clear()
        ficha.fases.clear()
        db.session.flush()

        fases_por_ordem = {}
        for dados_fase in sorted(dados.fases, key=lambda item: item.ordem):
            fase = FichaTecnicaFase(
                fase_id=dados_fase.fase_id,
                ordem=dados_fase.ordem,
                tempo_previsto_min=dados_fase.tempo_previsto_min,
            )
            ficha.fases.append(fase)
            fases_por_ordem[dados_fase.ordem] = fase

        db.session.flush()
        for dados_componente in dados.componentes:
            ficha.componentes.append(
                FichaTecnicaComponente(
                    produto_id=dados_componente.produto_id,
                    quantidade=dados_componente.quantidade,
                    fase=fases_por_ordem.get(dados_componente.fase_ordem),
                )
            )
        db.session.flush()

    def remover(self, ficha: FichaTecnica) -> None:
        db.session.delete(ficha)
        db.session.flush()

    def possui_solicitacao(self, ficha_id: int) -> bool:
        from app.features.producao.models import SolicitacaoProducao

        return (
            db.session.query(SolicitacaoProducao.id)
            .filter(SolicitacaoProducao.ficha_tecnica_id == ficha_id)
            .first()
            is not None
        )
