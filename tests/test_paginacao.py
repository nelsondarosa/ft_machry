import pytest

PRODUTOS = "/api/produtos"


def _criar_produtos(client, quantidade):
    for i in range(quantidade):
        r = client.post(
            PRODUTOS, json={"nome": f"p{i:02d}", "tipo": "INSUMO", "unidade_medida": "g"}
        )
        assert r.status_code == 201


def test_padrao_primeira_pagina_com_metadados(client):
    _criar_produtos(client, 25)
    corpo = client.get(PRODUTOS).get_json()
    assert corpo["page"] == 1
    assert corpo["per_page"] == 20
    assert corpo["total"] == 25
    assert corpo["pages"] == 2
    assert len(corpo["items"]) == 20


def test_consumidor_escolhe_pagina_e_tamanho(client):
    _criar_produtos(client, 7)
    corpo = client.get(f"{PRODUTOS}?page=2&per_page=3").get_json()
    assert [p["nome"] for p in corpo["items"]] == ["p03", "p04", "p05"]
    assert corpo["page"] == 2 and corpo["per_page"] == 3
    assert corpo["total"] == 7 and corpo["pages"] == 3

    ultima = client.get(f"{PRODUTOS}?page=3&per_page=3").get_json()
    assert [p["nome"] for p in ultima["items"]] == ["p06"]


def test_pagina_alem_do_fim_vem_vazia(client):
    _criar_produtos(client, 2)
    corpo = client.get(f"{PRODUTOS}?page=5").get_json()
    assert corpo["items"] == [] and corpo["total"] == 2


@pytest.mark.parametrize(
    "query", ["page=0", "page=-1", "page=abc", "per_page=0", "per_page=101", "per_page=x"]
)
def test_parametros_invalidos(client, query):
    r = client.get(f"{PRODUTOS}?{query}")
    assert r.status_code == 400
    assert "erro" in r.get_json()


def test_paginacao_em_consulta_sql_com_filtros(seeded_client):
    c = seeded_client
    lote = c.post("/api/estoque/lotes", json={"produto_id": 1, "localizacao_id": 1}).get_json()["id"]
    for _ in range(5):
        c.post(
            "/api/estoque/movimentacoes",
            json={"tipo": "ENTRADA", "lote_id": lote, "usuario_id": 1, "quantidade": 1},
        )

    primeira = c.get(f"/api/estoque/movimentacoes?lote_id={lote}&per_page=2").get_json()
    segunda = c.get(f"/api/estoque/movimentacoes?lote_id={lote}&per_page=2&page=2").get_json()
    assert primeira["total"] == 5 and primeira["pages"] == 3
    ids_1 = [m["id"] for m in primeira["items"]]
    ids_2 = [m["id"] for m in segunda["items"]]
    assert len(ids_1) == 2 and len(ids_2) == 2
    assert ids_1 + ids_2 == sorted(ids_1 + ids_2, reverse=True)


@pytest.mark.parametrize(
    "url",
    [
        "/api/usuarios",
        "/api/produtos",
        "/api/fichas-tecnicas",
        "/api/fichas-tecnicas/fases",
        "/api/estoque/inventario",
        "/api/estoque/movimentacoes",
        "/api/estoque/localizacoes",
        "/api/estoque/lotes",
        "/api/producao/solicitacoes",
    ],
)
def test_todas_as_listagens_sao_paginadas(seeded_client, url):
    r = seeded_client.get(f"{url}?page=1&per_page=1")
    assert r.status_code == 200, r.get_json()
    corpo = r.get_json()
    assert {"items", "page", "per_page", "total", "pages"} == corpo.keys()
    assert corpo["per_page"] == 1 and len(corpo["items"]) <= 1
