"""Testes de entrada/saída dos endpoints de produção (somente leitura)."""
from sqlalchemy import text

from db.database_config import db


def _criar_solicitacao_com_fase_e_componente(app):
    # Não existe endpoint para criar solicitação de produção ainda, então o
    # fixture é montado direto no banco, usando dados já carregados pelo seed
    # (ficha_tecnica 1, usuario 1, fase 1, produto 8).
    with app.app_context():
        db.session.execute(
            text(
                "INSERT INTO solicitacao_producao "
                "(id, ficha_tecnica_id, usuario_id, status) "
                "VALUES (1, 1, 1, 'EM_PRODUCAO')"
            )
        )
        db.session.execute(
            text(
                "INSERT INTO sp_fase "
                "(id, solicitacao_producao_id, fase_id, ordem, tempo_previsto_min) "
                "VALUES (1, 1, 1, 1, 10)"
            )
        )
        db.session.execute(
            text(
                "INSERT INTO sp_componente "
                "(id, solicitacao_producao_id, produto_id, quantidade_prevista, sp_fase_id) "
                "VALUES (1, 1, 8, 400, 1)"
            )
        )
        db.session.commit()


def test_lista_vazia(client):
    r = client.get('/api/producao/solicitacoes')
    assert r.status_code == 200 and r.get_json() == []


def test_detalhe_inexistente(client):
    assert client.get('/api/producao/solicitacoes/999').status_code == 404


def test_lista_e_detalhe_com_dados(app, seeded_client):
    _criar_solicitacao_com_fase_e_componente(app)
    c = seeded_client

    lista = c.get('/api/producao/solicitacoes')
    assert lista.status_code == 200
    assert [s['id'] for s in lista.get_json()] == [1]
    assert lista.get_json()[0]['status'] == 'EM_PRODUCAO'

    detalhe = c.get('/api/producao/solicitacoes/1')
    assert detalhe.status_code == 200
    corpo = detalhe.get_json()
    assert corpo['solicitacao']['id'] == 1
    assert corpo['solicitacao']['status'] == 'EM_PRODUCAO'

    assert len(corpo['fases']) == 1
    assert corpo['fases'][0]['fase'] == 'Bater/Misturar'
    assert corpo['fases'][0]['tempo_previsto_min'] == 10

    assert len(corpo['componentes']) == 1
    assert corpo['componentes'][0]['componente'] == 'Massa de bolo'
    assert corpo['componentes'][0]['quantidade_prevista'] == 400
    assert corpo['componentes'][0]['quantidade_realizada'] == 0  # nenhum CONSUMO_PRODUCAO ainda

    assert corpo['lotes_produzidos'] == []  # nenhuma movimentação PRODUCAO ainda
