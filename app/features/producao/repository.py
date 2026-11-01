from __future__ import annotations

from sqlalchemy import text

from db.database_config import db

from app.features.fichas_tecnicas.models import FichaTecnica

from .models import SolicitacaoProducao, SpComponente, SpFase


class ProducaoRepository:

    def listar_solicitacoes(self) -> list[SolicitacaoProducao]:
        return db.session.query(SolicitacaoProducao).order_by(
            SolicitacaoProducao.criado_em.desc()
        ).all()

    def obter_solicitacao(self, sp_id: int):
        return db.session.get(SolicitacaoProducao, sp_id)

    def criar_solicitacao(self, ficha_id: int, usuario_id: int) -> SolicitacaoProducao:
        ficha = db.session.get(FichaTecnica, ficha_id)
        if ficha is None:
            return None
        solicitacao = SolicitacaoProducao(ficha_tecnica_id=ficha_id, usuario_id=usuario_id)
        db.session.add(solicitacao)
        db.session.flush()
        fases_por_id = {}
        for fase in ficha.fases:
            fase_solicitacao = SpFase(
                solicitacao_producao_id=solicitacao.id,
                fase_id=fase.fase_id,
                ordem=fase.ordem,
                tempo_previsto_min=fase.tempo_previsto_min,
            )
            db.session.add(fase_solicitacao)
            db.session.flush()
            fases_por_id[fase.id] = fase_solicitacao.id
        for componente in ficha.componentes:
            db.session.add(SpComponente(
                solicitacao_producao_id=solicitacao.id,
                produto_id=componente.produto_id,
                quantidade_prevista=float(componente.quantidade),
                sp_fase_id=fases_por_id.get(componente.ficha_tecnica_fase_id),
            ))
        db.session.commit()
        return solicitacao

    def atualizar_status(self, solicitacao: SolicitacaoProducao, status: str) -> SolicitacaoProducao:
        solicitacao.status = status
        if status == "CONCLUIDA":
            solicitacao.concluido_em = db.func.current_timestamp()
        elif solicitacao.concluido_em is not None:
            solicitacao.concluido_em = None
        db.session.commit()
        return solicitacao

    def listar_componentes(self, sp_id: int):
        return db.session.execute(
            text(
                """SELECT * FROM vw_sp_componente WHERE solicitacao_producao_id = :id
                   ORDER BY fase_ordem, componente"""
            ),
            {"id": sp_id},
        ).mappings().all()

    def listar_fases(self, sp_id: int):
        return db.session.execute(
            text(
                """SELECT f.ordem, fp.nome AS fase, f.tempo_previsto_min, f.tempo_realizado_min
                   FROM sp_fase f JOIN fase_producao fp ON fp.id = f.fase_id
                   WHERE f.solicitacao_producao_id = :id ORDER BY f.ordem"""
            ),
            {"id": sp_id},
        ).mappings().all()

    def listar_lotes_produzidos(self, sp_id: int):
        return db.session.execute(
            text("SELECT * FROM vw_sp_producao WHERE solicitacao_producao_id = :id"),
            {"id": sp_id},
        ).mappings().all()
