"""Executar no repositório completo: pytest -q tests/test_estoque.py"""
def test_estoque_com_seeds(seeded_client):
    c = seeded_client
    loc = c.get('/api/estoque/localizacoes')
    assert loc.status_code == 200 and len(loc.json) >= 1
    novo = c.post('/api/estoque/lotes', json={'produto_id':1,'localizacao_id':1})
    assert novo.status_code == 201, novo.json
    lote = novo.json['id']
    entrada = c.post('/api/estoque/movimentacoes',json={'tipo':'ENTRADA','lote_id':lote,'usuario_id':1,'quantidade':10})
    assert entrada.status_code == 201, entrada.json
    assert c.get(f'/api/estoque/lotes/{lote}').json['quantidade'] == 10
    assert c.post('/api/estoque/movimentacoes',json={'tipo':'SAIDA','lote_id':lote,'usuario_id':1,'quantidade':11,'motivo':'consumo'}).status_code == 400
    assert c.post('/api/estoque/movimentacoes',json={'tipo':'SAIDA','lote_id':lote,'usuario_id':1,'quantidade':4,'motivo':'consumo'}).status_code == 201
    assert c.get(f'/api/estoque/lotes/{lote}').json['quantidade'] == 6
    assert c.get('/api/estoque/sugestao-saida/1?quantidade=5').json['quantidade_faltante'] == 0


def test_transformacao_e_transferencia(seeded_client):
    c = seeded_client
    def lote(produto,local,validade):
        r=c.post('/api/estoque/lotes',json={'produto_id':produto,'localizacao_id':local,'data_validade':validade})
        assert r.status_code==201,r.json
        return r.json['id']
    origem=lote(5,2,'2099-01-01')
    destino=lote(6,2,'2099-01-01')
    assert c.post('/api/estoque/movimentacoes',json={'tipo':'ENTRADA','lote_id':origem,'usuario_id':1,'quantidade':10}).status_code==201
    r=c.post('/api/estoque/movimentacoes',json={'tipo':'TRANSFORMACAO','lote_id':origem,'lote_destino_id':destino,'usuario_id':1,'quantidade':10,'quantidade_destino':9})
    assert r.status_code==201,r.json
    assert c.get(f'/api/estoque/lotes/{origem}').json['quantidade']==0
    assert c.get(f'/api/estoque/lotes/{destino}').json['quantidade']==9


def test_validacoes(client):
    assert client.post('/api/estoque/lotes',json={}).status_code==400
    assert client.post('/api/estoque/movimentacoes',json={'tipo':'ENTRADA','quantidade':-1}).status_code==400
    assert client.post('/api/estoque/localizacoes',json={'nome':'Novo','tipo':'INVALIDO'}).status_code==400


def test_localizacao_nao_pode_invalidar_lote(seeded_client):
    c = seeded_client
    lote=c.post('/api/estoque/lotes',json={'produto_id':1,'localizacao_id':1})
    assert lote.status_code==201,lote.json
    alteracao=c.put('/api/estoque/localizacoes/1',json={'tipo':'CONGELADO'})
    assert alteracao.status_code==400,alteracao.json
    assert next(l for l in c.get('/api/estoque/localizacoes').json if l['id']==1)['tipo']=='SECO'

def test_dados_invalidos_e_rollback(seeded_client):
    c = seeded_client
    lote=c.post('/api/estoque/lotes',json={'produto_id':1,'localizacao_id':1})
    assert lote.status_code==201,lote.json
    id_=lote.json['id']
    base={'tipo':'ENTRADA','lote_id':id_,'usuario_id':1,'quantidade':5}
    assert c.post('/api/estoque/movimentacoes',json={**base,'quantidade':'nan'}).status_code==400
    assert c.post('/api/estoque/movimentacoes',json={**base,'quantidade':'inf'}).status_code==400
    assert c.post('/api/estoque/movimentacoes',json=base).status_code==201
    saida={'tipo':'SAIDA','lote_id':id_,'usuario_id':1,'quantidade':5.0000000001,'motivo':'uso'}
    assert c.post('/api/estoque/movimentacoes',json=saida).status_code==400
    assert c.get(f'/api/estoque/lotes/{id_}').json['quantidade']==5
    assert c.post('/api/estoque/movimentacoes',json={**base,'quantidade':1,'usuario_id':999}).status_code==400
    assert c.get(f'/api/estoque/lotes/{id_}').json['quantidade']==5


def test_inventario(seeded_client):
    c = seeded_client
    lote = c.post('/api/estoque/lotes', json={'produto_id': 1, 'localizacao_id': 1}).get_json()['id']
    c.post('/api/estoque/movimentacoes', json={'tipo': 'ENTRADA', 'lote_id': lote, 'usuario_id': 1, 'quantidade': 10})

    todos = c.get('/api/estoque/inventario')
    assert todos.status_code == 200
    item = next(i for i in todos.get_json() if i['lote_id'] == lote)
    assert item['produto_id'] == 1 and item['quantidade'] == 10 and item['localizacao'] == 'Estoque Seco'

    filtrado = c.get('/api/estoque/inventario?produto_id=1')
    assert filtrado.status_code == 200
    assert all(i['produto_id'] == 1 for i in filtrado.get_json())

    assert c.get('/api/estoque/inventario?produto_id=abc').status_code == 400


def test_movimentacoes_listagem_e_filtros(seeded_client):
    c = seeded_client
    lote = c.post('/api/estoque/lotes', json={'produto_id': 1, 'localizacao_id': 1}).get_json()['id']
    c.post('/api/estoque/movimentacoes', json={'tipo': 'ENTRADA', 'lote_id': lote, 'usuario_id': 1, 'quantidade': 10})
    c.post('/api/estoque/movimentacoes',
           json={'tipo': 'SAIDA', 'lote_id': lote, 'usuario_id': 1, 'quantidade': 3, 'motivo': 'uso'})

    todas = c.get('/api/estoque/movimentacoes')
    assert todas.status_code == 200
    assert [m['tipo'] for m in todas.get_json()] == ['SAIDA', 'ENTRADA']  # mais recente primeiro

    so_entrada = c.get('/api/estoque/movimentacoes?tipo=entrada')
    assert [m['tipo'] for m in so_entrada.get_json()] == ['ENTRADA']  # tipo é comparado em maiúsculas

    assert len(c.get(f'/api/estoque/movimentacoes?lote_id={lote}').get_json()) == 2
    assert c.get('/api/estoque/movimentacoes?limite=0').status_code == 400


def test_crud_localizacao(client):
    nova = client.post('/api/estoque/localizacoes', json={'nome': 'Depósito', 'tipo': 'SECO'})
    assert nova.status_code == 201
    loc = nova.get_json()
    assert loc['nome'] == 'Depósito' and loc['tipo'] == 'SECO'
    assert loc in client.get('/api/estoque/localizacoes').get_json()

    atualizada = client.put(f"/api/estoque/localizacoes/{loc['id']}", json={'nome': 'Depósito 2'})
    assert atualizada.status_code == 200
    assert atualizada.get_json()['nome'] == 'Depósito 2'

    assert client.delete(f"/api/estoque/localizacoes/{loc['id']}").status_code == 204
    assert client.put(f"/api/estoque/localizacoes/{loc['id']}", json={'nome': 'x'}).status_code == 404
    assert client.delete(f"/api/estoque/localizacoes/{loc['id']}").status_code == 404


def test_localizacao_validacoes(client):
    assert client.post('/api/estoque/localizacoes', json={}).status_code == 400
    assert client.put('/api/estoque/localizacoes/1', json={}).status_code == 400  # corpo vazio

    pai = client.post('/api/estoque/localizacoes', json={'nome': 'Pai'}).get_json()
    filha = client.post('/api/estoque/localizacoes',
                         json={'nome': 'Filha', 'parent_id': pai['id']}).get_json()

    assert client.put(f"/api/estoque/localizacoes/{pai['id']}",
                       json={'parent_id': filha['id']}).status_code == 400  # ciclo
    assert client.put(f"/api/estoque/localizacoes/{pai['id']}",
                       json={'parent_id': pai['id']}).status_code == 400  # pai de si mesma
    assert client.put(f"/api/estoque/localizacoes/{pai['id']}",
                       json={'parent_id': 9999}).status_code == 400  # pai inexistente
    assert client.put(f"/api/estoque/localizacoes/{pai['id']}",
                       json={'campo_invalido': 1}).status_code == 400  # campo não editável


def test_lotes_listagem_e_detalhe(seeded_client):
    c = seeded_client
    lote1 = c.post('/api/estoque/lotes', json={'produto_id': 1, 'localizacao_id': 1}).get_json()['id']
    lote2 = c.post('/api/estoque/lotes', json={'produto_id': 4, 'localizacao_id': 1}).get_json()['id']

    todos = c.get('/api/estoque/lotes')
    assert todos.status_code == 200 and len(todos.get_json()) == 2
    assert {'produto', 'localizacao'} <= todos.get_json()[0].keys()

    so_produto1 = c.get('/api/estoque/lotes?produto_id=1')
    assert [l['id'] for l in so_produto1.get_json()] == [lote1]
    assert next(l for l in todos.get_json() if l['id'] == lote2)['produto'] == 'Nozes'

    # GET /lotes/<id> devolve só os campos da tabela lote, sem nomes de produto/localizacao
    assert c.get(f'/api/estoque/lotes/{lote2}').get_json()['produto_id'] == 4
    assert c.get('/api/estoque/lotes/9999').status_code == 404


def test_atualizar_lote(seeded_client):
    c = seeded_client
    lote = c.post('/api/estoque/lotes', json={'produto_id': 1, 'localizacao_id': 1}).get_json()['id']

    atualizado = c.put(f'/api/estoque/lotes/{lote}',
                        json={'custo_unitario': 2.5, 'data_validade': '2099-01-01'})
    assert atualizado.status_code == 200
    assert atualizado.get_json()['custo_unitario'] == 2.5
    assert atualizado.get_json()['data_validade'] == '2099-01-01'

    assert c.put(f'/api/estoque/lotes/{lote}', json={'quantidade': 50}).status_code == 400
    assert c.put('/api/estoque/lotes/9999', json={'custo_unitario': 1}).status_code == 404


def test_sugestao_saida_validacoes(client):
    assert client.get('/api/estoque/sugestao-saida/1').status_code == 400  # sem quantidade
    assert client.get('/api/estoque/sugestao-saida/9999?quantidade=1').status_code == 404
