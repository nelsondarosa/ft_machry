URL = "/api/fichas-tecnicas/lote"


def _produtos(client):
    lote = [
        {"nome": "Batata Asterix", "tipo": "INSUMO", "unidade_medida": "kg"},
        {"nome": "Leite integral", "tipo": "INSUMO", "unidade_medida": "L"},
        {"nome": "Louro", "tipo": "INSUMO", "unidade_medida": "un"},
        {"nome": "Purê de batata", "tipo": "FINAL", "unidade_medida": "kg"},
        {"nome": "Gratin", "tipo": "FINAL", "unidade_medida": "kg"},
        {"nome": "Bacalhau", "tipo": "INSUMO", "unidade_medida": "kg", "conservacao": "RESFRIADO"},
    ]
    assert client.post("/api/produtos/lote", json={"produtos": lote}).status_code == 201


def _ficha(**extra):
    return {
        "produto": "pure de batata",
        "rendimento": "0.35",
        "observacao": "Cozinhar e amassar.",
        "fases": [
            {"fase": "Cozir", "ordem": 1, "tempo_previsto_min": 25},
            {"fase": "Passar na peneira", "ordem": 2, "tempo_previsto_min": 10},
        ],
        "componentes": [
            {"produto": "Batata asterix", "quantidade": "300", "unidade": "g", "fase_ordem": 1},
            {"produto": "Leite Integral", "quantidade": "20", "unidade": "ml", "fase_ordem": 2},
            {"produto": "Louro", "quantidade": "1", "fase_ordem": 1},
            {"produto": "Sal", "quantidade": None},
        ],
        **extra,
    }


def test_importa_por_nome_converte_unidade_e_cria_fase(client):
    _produtos(client)
    r = client.post(URL, json={"fichas": [_ficha()]})
    assert r.status_code == 201, r.get_json()
    dados = r.get_json()
    assert dados["total"] == 1 and dados["fases_criadas"] == ["Cozir", "Passar na peneira"]  # banco sem seed

    r = client.post(URL, json={"fichas": [{**_ficha(), "produto": "Purê de batata 2"}]})
    assert "não encontrado" in r.get_json()["erro"]
    ficha = dados["items"][0]
    assert ficha["produto"] == "Purê de batata"
    assert ficha["observacao"] == "Cozinhar e amassar.\nA gosto (q.b.): Sal."
    quantidades = {c["produto"]: c["quantidade"] for c in ficha["componentes"]}
    assert quantidades == {"Batata asterix": 0.3, "Leite integral": 0.02, "Louro": 1.0}
    assert [f["fase"] for f in ficha["fases"]] == ["Cozir", "Passar na peneira"]


def test_lote_atomico_e_erros_com_posicao(client):
    _produtos(client)
    casos = [
        ({"produto": "Inexistente"}, "ficha 2 (Inexistente): produto 'Inexistente' não encontrado"),
        ({"componentes": [{"produto": "Leite integral", "quantidade": 1, "unidade": "g"}]}, "não pode ser convertida"),
        ({"produto": "Batata asterix"}, "um insumo não pode possuir ficha técnica"),
    ]
    for extra, erro in casos:
        outro = {**_ficha(), "produto": "Gratin", **extra}
        r = client.post(URL, json={"fichas": [_ficha(), outro]})
        assert r.status_code == 400, extra
        assert erro in r.get_json()["erro"]
    assert client.get("/api/fichas-tecnicas").get_json()["items"] == []
    fases = [f["nome"] for f in client.get("/api/fichas-tecnicas/fases").get_json()["items"]]
    assert "Passar na peneira" not in fases  # rollback inclui fases criadas


def test_produto_com_ficha_existente_e_ignorado(client):
    _produtos(client)
    assert client.post(URL, json={"fichas": [_ficha()]}).status_code == 201
    r = client.post(URL, json={"fichas": [_ficha()]})
    assert r.status_code == 201
    assert r.get_json()["total"] == 0 and r.get_json()["ignoradas"] == ["Purê de batata"]
    assert len(client.get("/api/fichas-tecnicas").get_json()["items"]) == 1


def test_ficha_repetida_no_arquivo(client):
    _produtos(client)
    r = client.post(URL, json={"fichas": [_ficha(), _ficha()]})
    assert r.status_code == 400
    assert "ficha 2 (pure de batata): ficha repetida no arquivo" in r.get_json()["erro"]
