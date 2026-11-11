"""Itens do lote: unidades com código próprio. Executar: pytest -q tests/test_itens_lote.py"""
from sqlalchemy import inspect, text

from db.database_config import db

BASE = '/api/estoque'


def _criar_lote(c, produto=1, local=1, itens=None, **extra):
    corpo = {'produto_id': produto, 'localizacao_id': local, **extra}
    if itens is not None:
        corpo |= {'itens': itens, 'usuario_id': 1}
    r = c.post(f'{BASE}/lotes', json=corpo)
    assert r.status_code == 201, r.json
    return r.json


def _itens(c, lote_id, status=None):
    url = f'{BASE}/lotes/{lote_id}/itens' + (f'?status={status}' if status else '')
    r = c.get(url)
    assert r.status_code == 200, r.json
    return r.json['items']


def _lote(c, lote_id):
    return c.get(f'{BASE}/lotes/{lote_id}').json


def _mov(c, **corpo):
    return c.post(f'{BASE}/movimentacoes', json={'usuario_id': 1, **corpo})


GRUPOS = [
    {'quantidade_unidades': 6, 'quantidade': 1000, 'fabricante': 'Tio João',
     'data_fabricacao': '2099-01-01', 'data_validade': '2099-03-10'},
    {'quantidade_unidades': 4, 'quantidade': 1000, 'fabricante': 'Camil',
     'data_fabricacao': '2099-01-05', 'data_validade': '2099-03-14'},
]


def test_criar_lote_com_itens_em_uma_chamada(seeded_client):
    c = seeded_client
    lote = _criar_lote(c, itens=GRUPOS, fornecedor=' Moinho Sul ', nota_fiscal='NF 123',
                       data_validade='2099-12-31', observacao='compra semanal')
    assert lote['quantidade'] == 10000
    assert lote['data_validade'] == '2099-03-10'
    assert lote['fornecedor'] == 'Moinho Sul' and lote['nota_fiscal'] == 'NF 123'

    itens = _itens(c, lote['id'])
    assert [i['codigo'] for i in itens[:2]] == [f"FT-{lote['id']:03d}-01", f"FT-{lote['id']:03d}-02"]
    assert len(itens) == 10 and all(i['status'] == 'DISPONIVEL' and i['saldo'] == 1000 for i in itens)
    assert itens[-1]['fabricante'] == 'Camil'

    entradas = c.get(f"{BASE}/movimentacoes?lote_id={lote['id']}").json['items']
    assert [(m['tipo'], m['quantidade'], m['observacao']) for m in entradas] == [('ENTRADA', 10000, 'compra semanal')]

    listado = next(l for l in c.get(f'{BASE}/lotes').json['items'] if l['id'] == lote['id'])
    assert (listado['itens_total'], listado['itens_disponiveis'], listado['itens_consumidos']) == (10, 10, 0)


def test_criacao_com_itens_e_atomica(seeded_client):
    c = seeded_client
    antes = c.get(f'{BASE}/lotes').json['total']
    r = c.post(f'{BASE}/lotes', json={'produto_id': 1, 'localizacao_id': 1, 'itens': GRUPOS, 'usuario_id': 999})
    assert r.status_code == 400
    assert c.get(f'{BASE}/lotes').json['total'] == antes
    assert c.post(f'{BASE}/lotes', json={'produto_id': 1, 'localizacao_id': 1, 'itens': GRUPOS}).status_code == 400
    invalido = [{'quantidade_unidades': 1, 'quantidade': 1, 'data_fabricacao': '2099-02-01', 'data_validade': '2099-01-01'}]
    assert c.post(f'{BASE}/lotes', json={'produto_id': 1, 'localizacao_id': 1, 'itens': invalido, 'usuario_id': 1}).status_code == 400


def test_saida_por_quantidade_consome_fefo_e_abre_item(seeded_client):
    c = seeded_client
    lote = _criar_lote(c, itens=GRUPOS)
    r = _mov(c, tipo='SAIDA', lote_id=lote['id'], quantidade=1500, motivo='produção')
    assert r.status_code == 201, r.json
    assert r.json['quantidade'] == 1500
    itens = _itens(c, lote['id'])
    assert (itens[0]['status'], itens[0]['saldo']) == ('CONSUMIDA', 0)
    assert (itens[1]['status'], itens[1]['saldo']) == ('EM_USO', 500)
    assert itens[1]['aberto_em']
    assert _lote(c, lote['id'])['quantidade'] == 8500

    assert _mov(c, tipo='SAIDA', lote_id=lote['id'], quantidade=500, motivo='produção').status_code == 201
    assert _itens(c, lote['id'])[1]['status'] == 'CONSUMIDA'
    assert _mov(c, tipo='SAIDA', lote_id=lote['id'], quantidade=9000, motivo='x').status_code == 400
    assert _lote(c, lote['id'])['quantidade'] == 8000


def test_saida_por_itens_escolhidos(seeded_client):
    c = seeded_client
    lote = _criar_lote(c, itens=GRUPOS)
    ids = [i['id'] for i in _itens(c, lote['id'])]
    r = _mov(c, tipo='AJUSTE_SAIDA', lote_id=lote['id'], item_ids=ids[6:8], motivo='avaria')
    assert r.status_code == 201, r.json
    assert r.json['quantidade'] == 2000
    assert [i['status'] for i in _itens(c, lote['id'], 'CONSUMIDA')] == ['CONSUMIDA', 'CONSUMIDA']
    assert _lote(c, lote['id'])['quantidade'] == 8000

    assert _mov(c, tipo='SAIDA', lote_id=lote['id'], item_ids=[ids[6]], motivo='x').status_code == 400
    assert _mov(c, tipo='SAIDA', lote_id=lote['id'], item_ids=[ids[0], ids[0]], motivo='x').status_code == 400
    assert _mov(c, tipo='SAIDA', lote_id=lote['id'], item_ids=[ids[0]], quantidade=1, motivo='x').status_code == 400
    assert _mov(c, tipo='ENTRADA', lote_id=lote['id'], item_ids=[ids[0]]).status_code == 400
    assert _mov(c, tipo='ENTRADA', lote_id=lote['id'], quantidade=10).status_code == 400
    assert _lote(c, lote['id'])['quantidade'] == 8000


def test_transferencia_move_itens_mantendo_codigo(seeded_client):
    c = seeded_client
    origem = _criar_lote(c, itens=GRUPOS)
    destino = _criar_lote(c)
    ids = [i['id'] for i in _itens(c, origem['id'])]
    assert _mov(c, tipo='TRANSFERENCIA', lote_id=origem['id'], lote_destino_id=destino['id'], quantidade=1000).status_code == 400

    r = _mov(c, tipo='TRANSFERENCIA', lote_id=origem['id'], lote_destino_id=destino['id'], item_ids=ids[:3])
    assert r.status_code == 201, r.json
    movidos = _itens(c, destino['id'])
    assert [i['codigo'] for i in movidos] == [f"FT-{origem['id']:03d}-0{n}" for n in (1, 2, 3)]
    assert all(i['status'] == 'DISPONIVEL' for i in movidos)
    assert _lote(c, origem['id'])['quantidade'] == 7000
    assert _lote(c, destino['id'])['quantidade'] == 3000
    assert _lote(c, destino['id'])['data_validade'] == '2099-03-10'

    novos = c.post(f"{BASE}/lotes/{destino['id']}/itens", json={'usuario_id': 1, 'itens': [{'quantidade_unidades': 1, 'quantidade': 500}]})
    assert novos.status_code == 201, novos.json
    assert novos.json[0]['codigo'] == f"FT-{destino['id']:03d}-01"
    assert _lote(c, destino['id'])['quantidade'] == 3500


def test_transferencia_bloqueia_destino_com_saldo_sem_itens(seeded_client):
    c = seeded_client
    origem = _criar_lote(c, itens=GRUPOS)
    destino = _criar_lote(c)
    assert _mov(c, tipo='ENTRADA', lote_id=destino['id'], quantidade=50).status_code == 201
    item = _itens(c, origem['id'])[0]['id']
    r = _mov(c, tipo='TRANSFERENCIA', lote_id=origem['id'], lote_destino_id=destino['id'], item_ids=[item])
    assert r.status_code == 400
    assert _itens(c, origem['id'])[0]['lote_id'] == origem['id']
    r = _mov(c, tipo='TRANSFERENCIA', lote_id=destino['id'], lote_destino_id=origem['id'], quantidade=10)
    assert r.status_code == 400


def test_transformacao_consome_itens_e_cria_item_no_destino_rastreado(seeded_client):
    c = seeded_client
    origem = _criar_lote(c, produto=5, local=2, data_validade='2099-01-01',
                         itens=[{'quantidade_unidades': 3, 'quantidade': 2}])
    destino = _criar_lote(c, produto=6, local=2, data_validade='2099-02-01',
                          itens=[{'quantidade_unidades': 1, 'quantidade': 1}])
    ids = [i['id'] for i in _itens(c, origem['id'])]
    r = _mov(c, tipo='TRANSFORMACAO', lote_id=origem['id'], lote_destino_id=destino['id'],
             item_ids=ids[:2], quantidade_destino=3.5)
    assert r.status_code == 201, r.json
    assert r.json['quantidade'] == 4
    assert _lote(c, origem['id'])['quantidade'] == 2
    itens_destino = _itens(c, destino['id'])
    assert [i['quantidade'] for i in itens_destino] == [1, 3.5]
    assert itens_destino[1]['codigo'] == f"FT-{destino['id']:03d}-02"
    assert _lote(c, destino['id'])['quantidade'] == 4.5


def test_adicionar_editar_e_abrir_itens(seeded_client):
    c = seeded_client
    lote = _criar_lote(c, itens=GRUPOS)
    novos = c.post(f"{BASE}/lotes/{lote['id']}/itens", json={
        'usuario_id': 1, 'observacao': 'reposição',
        'itens': [{'quantidade_unidades': 2, 'quantidade': 250, 'data_validade': '2099-02-01'}],
    })
    assert novos.status_code == 201, novos.json
    assert [i['codigo'][-2:] for i in novos.json] == ['11', '12']
    assert _lote(c, lote['id'])['quantidade'] == 10500
    assert _lote(c, lote['id'])['data_validade'] == '2099-02-01'

    item = novos.json[0]['id']
    r = c.put(f'{BASE}/itens/{item}', json={'data_validade': '2099-04-01', 'fabricante': ' Prato Fino '})
    assert r.status_code == 200, r.json
    assert r.json['fabricante'] == 'Prato Fino'
    assert _lote(c, lote['id'])['data_validade'] == '2099-02-01'
    assert c.put(f'{BASE}/itens/{item}', json={'data_fabricacao': '2099-05-01'}).status_code == 400
    assert c.put(f'{BASE}/itens/{item}', json={'status': 'CONSUMIDA'}).status_code == 400

    aberto = c.post(f'{BASE}/itens/{item}/abrir')
    assert aberto.status_code == 200 and aberto.json['status'] == 'EM_USO'
    assert c.post(f'{BASE}/itens/{item}/abrir').status_code == 400
    assert c.get(f'{BASE}/itens/{item}').json['status'] == 'EM_USO'
    assert [i['id'] for i in _itens(c, lote['id'], 'EM_USO')] == [item]
    assert c.get(f'{BASE}/itens/99999').status_code == 404
    assert c.get(f'{BASE}/lotes/99999/itens').status_code == 404


def test_adicionar_itens_em_lote_com_saldo_solto_e_recusado(seeded_client):
    c = seeded_client
    lote = _criar_lote(c)
    assert _mov(c, tipo='ENTRADA', lote_id=lote['id'], quantidade=5).status_code == 201
    r = c.post(f"{BASE}/lotes/{lote['id']}/itens", json={'usuario_id': 1, 'itens': [{'quantidade_unidades': 1, 'quantidade': 1}]})
    assert r.status_code == 400
    assert _lote(c, lote['id'])['quantidade'] == 5


def test_init_db_migra_banco_existente(app, client):
    with app.app_context():
        db.session.execute(text('DROP TABLE movimentacao_item'))
        db.session.execute(text('DROP TABLE item_lote'))
        db.session.execute(text('ALTER TABLE lote DROP COLUMN fornecedor'))
        db.session.execute(text('ALTER TABLE lote DROP COLUMN nota_fiscal'))
        db.session.commit()
        resultado = app.test_cli_runner().invoke(args=['init-db'])
        assert resultado.exit_code == 0, resultado.output
        inspetor = inspect(db.engine)
        assert {'item_lote', 'movimentacao_item'} <= set(inspetor.get_table_names())
        assert {'fornecedor', 'nota_fiscal'} <= {col['name'] for col in inspetor.get_columns('lote')}
