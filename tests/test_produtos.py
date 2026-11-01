URL = "/api/produtos"
FARINHA = {"nome": "Farinha", "tipo": "INSUMO", "unidade_medida": "g"}


def criar(client, **extra):
    return client.post(URL, json={**FARINHA, **extra})


def test_crud_completo(client):
    r = criar(client, validade_padrao_dias=180)
    assert r.status_code == 201
    p = r.get_json()
    assert p["nome"] == "Farinha"
    assert p["conservacao"] == "SECO"  # default do schema
    assert p["validade_padrao_dias"] == 180
    assert p["ativo"] == 1

    assert client.get(f"{URL}/{p['id']}").get_json() == p
    assert client.get(URL).get_json() == [p]

    r = client.put(f"{URL}/{p['id']}", json={"conservacao": "RESFRIADO"})
    assert r.status_code == 200
    assert r.get_json()["conservacao"] == "RESFRIADO"
    assert r.get_json()["nome"] == "Farinha"

    assert client.delete(f"{URL}/{p['id']}").status_code == 204
    assert client.get(f"{URL}/{p['id']}").status_code == 404
    assert client.get(URL).get_json() == []
    assert client.delete(f"{URL}/{p['id']}").status_code == 404


def test_lista_ordenada_por_nome(client):
    criar(client, nome="b")
    criar(client, nome="a")
    assert [p["nome"] for p in client.get(URL).get_json()] == ["a", "b"]


def test_validacao(client):
    assert client.post(URL, data="x", content_type="text/plain").status_code == 400
    assert client.post(URL, json={}).status_code == 400
    assert client.post(URL, json={"nome": "x"}).status_code == 400  # tipo/unidade NOT NULL
    assert criar(client, nome=" ").status_code == 400
    assert criar(client, tipo="OUTRO").status_code == 400  # CHECK
    assert criar(client, conservacao="QUENTE").status_code == 400  # CHECK
    assert criar(client, grupo_id=999).status_code == 400  # FOREIGN KEY

    pid = criar(client).get_json()["id"]
    assert client.put(f"{URL}/{pid}", json={}).status_code == 400
    assert client.put(f"{URL}/{pid}", json={"tipo": "OUTRO"}).status_code == 400
    assert client.put(f"{URL}/{pid}", json={"unidade_medida": None}).status_code == 400


def test_inexistente(client):
    assert client.get(f"{URL}/999").status_code == 404
    assert client.put(f"{URL}/999", json={"nome": "x"}).status_code == 404
    assert client.delete(f"{URL}/999").status_code == 404


def test_seeds(app):
    with app.app_context():
        result = app.test_cli_runner().invoke(args=["init-db", "--seed"])
    assert result.exit_code == 0, result.output
    client = app.test_client()
    assert client.post(
        "/api/auth/login", json={"username": "dona", "password": "Teste@123"}
    ).status_code == 200
    assert len(client.get(URL).get_json()) == 10
    assert client.get(f"{URL}/10").get_json()["nome"] == "Bolo de Nozes - Médio"


def test_docs(client):
    r = client.get("/openapi.yaml")
    assert r.status_code == 200 and b"/api/produtos" in r.data
    assert b"swagger-ui" in client.get("/docs").data
