"""Testes dos fluxos de planejamento, execução e conclusão da produção."""
from sqlalchemy import text

from app.features.fichas_tecnicas.models import FaseProducao
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


def _criar_produto(client, nome, tipo):
    resposta = client.post('/api/produtos', json={
        'nome': nome,
        'tipo': tipo,
        'unidade_medida': 'kg',
        'conservacao': 'SECO',
    })
    assert resposta.status_code == 201, resposta.get_json()
    return resposta.get_json()['id']


def _preparar_fluxo_completo(app, client):
    """Cria um cenário pequeno e independente dos dados demonstrativos."""
    with app.app_context():
        fase = FaseProducao(nome='Preparar fluxo de produção')
        db.session.add(fase)
        db.session.commit()
        fase_id = fase.id

    ingrediente_a = _criar_produto(client, 'Ingrediente produção A', 'INSUMO')
    ingrediente_b = _criar_produto(client, 'Ingrediente produção B', 'INSUMO')
    produto_final = _criar_produto(client, 'Produto final produção', 'FINAL')
    local = client.post('/api/estoque/localizacoes', json={
        'nome': 'Estoque produção', 'tipo': 'SECO',
    })
    assert local.status_code == 201, local.get_json()

    ficha = client.post('/api/fichas-tecnicas', json={
        'produto_id': produto_final,
        'rendimento': 10,
        'observacao': 'Uma solicitação representa um rendimento completo.',
        'fases': [{
            'fase_id': fase_id, 'ordem': 1, 'tempo_previsto_min': 15,
        }],
        'componentes': [
            {'produto_id': ingrediente_a, 'quantidade': 2, 'fase_ordem': 1},
            {'produto_id': ingrediente_b, 'quantidade': 3, 'fase_ordem': 1},
        ],
    })
    assert ficha.status_code == 201, ficha.get_json()
    return {
        'ficha_id': ficha.get_json()['id'],
        'produto_final': produto_final,
        'ingrediente_a': ingrediente_a,
        'ingrediente_b': ingrediente_b,
        'local_id': local.get_json()['id'],
    }


def _criar_lote_com_saldo(client, produto_id, local_id, quantidade, validade):
    lote = client.post('/api/estoque/lotes', json={
        'produto_id': produto_id,
        'localizacao_id': local_id,
        'data_validade': validade,
    })
    assert lote.status_code == 201, lote.get_json()
    lote_id = lote.get_json()['id']
    entrada = client.post('/api/estoque/movimentacoes', json={
        'tipo': 'ENTRADA',
        'lote_id': lote_id,
        'usuario_id': 1,
        'quantidade': quantidade,
    })
    assert entrada.status_code == 201, entrada.get_json()
    return lote_id


def _criar_e_iniciar(
    client, ficha_id, quantidade_planejada=None, localizacao_destino_id=None
):
    payload = {'ficha_tecnica_id': ficha_id}
    if quantidade_planejada is not None:
        payload['quantidade_planejada'] = quantidade_planejada
    if localizacao_destino_id is not None:
        payload['localizacao_destino_id'] = localizacao_destino_id
    solicitacao = client.post('/api/producao/solicitacoes', json=payload)
    assert solicitacao.status_code == 201, solicitacao.get_json()
    solicitacao_id = solicitacao.get_json()['id']
    inicio = client.put(f'/api/producao/solicitacoes/{solicitacao_id}/status', json={
        'status': 'EM_PRODUCAO',
    })
    assert inicio.status_code == 200, inicio.get_json()
    return solicitacao_id


def _concluir(client, solicitacao_id):
    return client.put(f'/api/producao/solicitacoes/{solicitacao_id}/status', json={
        'status': 'CONCLUIDA',
    })


def test_lista_vazia(client):
    r = client.get('/api/producao/solicitacoes')
    assert r.status_code == 200 and r.get_json()['items'] == []


def test_detalhe_inexistente(client):
    assert client.get('/api/producao/solicitacoes/999').status_code == 404


def test_lista_e_detalhe_com_dados(app, seeded_client):
    _criar_solicitacao_com_fase_e_componente(app)
    c = seeded_client

    lista = c.get('/api/producao/solicitacoes')
    assert lista.status_code == 200
    assert [s['id'] for s in lista.get_json()['items']] == [1]
    assert lista.get_json()['items'][0]['status'] == 'EM_PRODUCAO'

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


def test_criacao_copia_fases_e_componentes_da_ficha(app, client):
    dados = _preparar_fluxo_completo(app, client)
    criada = client.post('/api/producao/solicitacoes', json={
        'ficha_tecnica_id': dados['ficha_id'],
    })
    assert criada.status_code == 201, criada.get_json()
    assert criada.get_json()['status'] == 'ABERTA'
    assert criada.get_json()['usuario_id'] == 1

    detalhe = client.get(
        f"/api/producao/solicitacoes/{criada.get_json()['id']}"
    ).get_json()
    assert [(fase['ordem'], fase['fase']) for fase in detalhe['fases']] == [
        (1, 'Preparar fluxo de produção')
    ]
    assert {
        componente['produto_id']: componente['quantidade_prevista']
        for componente in detalhe['componentes']
    } == {dados['ingrediente_a']: 2, dados['ingrediente_b']: 3}


def test_solicitacao_exige_ficha_existente(client):
    resposta = client.post('/api/producao/solicitacoes', json={
        'ficha_tecnica_id': 999_999,
    })
    assert resposta.status_code == 404


def test_quantidade_planejada_escala_componentes_e_valida_destino(app, client):
    dados = _preparar_fluxo_completo(app, client)
    congelado = client.post('/api/estoque/localizacoes', json={
        'nome': 'Freezer produção', 'tipo': 'CONGELADO',
    }).get_json()
    incompativel = client.post('/api/producao/solicitacoes', json={
        'ficha_tecnica_id': dados['ficha_id'],
        'quantidade_planejada': 20,
        'localizacao_destino_id': congelado['id'],
    })
    assert incompativel.status_code == 400

    criada = client.post('/api/producao/solicitacoes', json={
        'ficha_tecnica_id': dados['ficha_id'],
        'quantidade_planejada': 20,
        'localizacao_destino_id': dados['local_id'],
    })
    assert criada.status_code == 201, criada.get_json()
    assert criada.get_json()['quantidade_planejada'] == 20
    assert criada.get_json()['localizacao_destino_id'] == dados['local_id']
    detalhe = client.get(
        f"/api/producao/solicitacoes/{criada.get_json()['id']}"
    ).get_json()
    assert {
        componente['produto_id']: componente['quantidade_prevista']
        for componente in detalhe['componentes']
    } == {dados['ingrediente_a']: 4, dados['ingrediente_b']: 6}


def test_transicoes_de_status_e_data_de_conclusao(app, client):
    dados = _preparar_fluxo_completo(app, client)
    _criar_lote_com_saldo(
        client, dados['ingrediente_a'], dados['local_id'], 2, '2099-01-10'
    )
    _criar_lote_com_saldo(
        client, dados['ingrediente_b'], dados['local_id'], 3, '2099-01-10'
    )
    criada = client.post('/api/producao/solicitacoes', json={
        'ficha_tecnica_id': dados['ficha_id'],
    }).get_json()
    solicitacao_id = criada['id']

    conclusao_antecipada = _concluir(client, solicitacao_id)
    assert conclusao_antecipada.status_code == 400

    inicio = client.put(f'/api/producao/solicitacoes/{solicitacao_id}/status', json={
        'status': 'EM_PRODUCAO',
    })
    assert inicio.status_code == 200
    conclusao = _concluir(client, solicitacao_id)
    assert conclusao.status_code == 200
    assert conclusao.get_json()['status'] == 'CONCLUIDA'
    assert conclusao.get_json()['concluido_em'] is not None

    repetida = _concluir(client, solicitacao_id)
    assert repetida.status_code == 400


def test_cancelamento_nao_marca_data_de_conclusao(app, client):
    dados = _preparar_fluxo_completo(app, client)
    criada = client.post('/api/producao/solicitacoes', json={
        'ficha_tecnica_id': dados['ficha_id'],
    }).get_json()
    cancelada = client.put(
        f"/api/producao/solicitacoes/{criada['id']}/status",
        json={'status': 'CANCELADA'},
    )
    assert cancelada.status_code == 200
    assert cancelada.get_json()['status'] == 'CANCELADA'
    assert cancelada.get_json()['concluido_em'] is None


def test_conclusao_baixa_quantidades_da_ficha(app, client):
    dados = _preparar_fluxo_completo(app, client)
    lote_a = _criar_lote_com_saldo(
        client, dados['ingrediente_a'], dados['local_id'], 8, '2099-01-10'
    )
    lote_b = _criar_lote_com_saldo(
        client, dados['ingrediente_b'], dados['local_id'], 9, '2099-01-10'
    )
    solicitacao_id = _criar_e_iniciar(client, dados['ficha_id'])

    conclusao = _concluir(client, solicitacao_id)
    assert conclusao.status_code == 200, conclusao.get_json()
    assert client.get(f'/api/estoque/lotes/{lote_a}').get_json()['quantidade'] == 6
    assert client.get(f'/api/estoque/lotes/{lote_b}').get_json()['quantidade'] == 6

    movimentos = client.get(
        '/api/estoque/movimentacoes?tipo=CONSUMO_PRODUCAO'
    ).get_json()['items']
    assert len(movimentos) == 2
    assert {movimento['solicitacao_producao_id'] for movimento in movimentos} == {
        solicitacao_id
    }


def test_conclusao_consumo_fefo(app, client):
    dados = _preparar_fluxo_completo(app, client)
    lote_primeiro = _criar_lote_com_saldo(
        client, dados['ingrediente_a'], dados['local_id'], 1, '2098-01-10'
    )
    lote_depois = _criar_lote_com_saldo(
        client, dados['ingrediente_a'], dados['local_id'], 5, '2099-01-10'
    )
    _criar_lote_com_saldo(
        client, dados['ingrediente_b'], dados['local_id'], 3, '2099-01-10'
    )
    solicitacao_id = _criar_e_iniciar(client, dados['ficha_id'])

    assert _concluir(client, solicitacao_id).status_code == 200
    assert client.get(f'/api/estoque/lotes/{lote_primeiro}').get_json()['quantidade'] == 0
    assert client.get(f'/api/estoque/lotes/{lote_depois}').get_json()['quantidade'] == 4


def test_falta_de_estoque_impede_conclusao_sem_baixa_parcial(app, client):
    dados = _preparar_fluxo_completo(app, client)
    lote_a = _criar_lote_com_saldo(
        client, dados['ingrediente_a'], dados['local_id'], 2, '2099-01-10'
    )
    # O segundo componente exige 3 kg, mas possui apenas 1 kg.
    lote_b = _criar_lote_com_saldo(
        client, dados['ingrediente_b'], dados['local_id'], 1, '2099-01-10'
    )
    solicitacao_id = _criar_e_iniciar(client, dados['ficha_id'])

    conclusao = _concluir(client, solicitacao_id)
    assert conclusao.status_code == 400
    assert client.get(f'/api/estoque/lotes/{lote_a}').get_json()['quantidade'] == 2
    assert client.get(f'/api/estoque/lotes/{lote_b}').get_json()['quantidade'] == 1
    detalhe = client.get(
        f'/api/producao/solicitacoes/{solicitacao_id}'
    ).get_json()
    assert detalhe['solicitacao']['status'] == 'EM_PRODUCAO'


def test_conclusao_cria_lote_do_produto_final(app, client):
    dados = _preparar_fluxo_completo(app, client)
    _criar_lote_com_saldo(
        client, dados['ingrediente_a'], dados['local_id'], 2, '2099-01-10'
    )
    _criar_lote_com_saldo(
        client, dados['ingrediente_b'], dados['local_id'], 3, '2099-01-10'
    )
    solicitacao_id = _criar_e_iniciar(client, dados['ficha_id'])

    assert _concluir(client, solicitacao_id).status_code == 200
    lotes = client.get(
        f"/api/estoque/lotes?produto_id={dados['produto_final']}"
    ).get_json()['items']
    assert len(lotes) == 1
    assert lotes[0]['quantidade'] == 10
    assert lotes[0]['localizacao_id'] == dados['local_id']

    detalhe = client.get(
        f'/api/producao/solicitacoes/{solicitacao_id}'
    ).get_json()
    assert detalhe['lotes_produzidos'][0]['lote_id'] == lotes[0]['id']
    assert detalhe['lotes_produzidos'][0]['quantidade'] == 10
