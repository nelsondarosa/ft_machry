NOVO = {
    "nome": "Maria Souza",
    "username": "Maria.Souza",
    "password": "Senha@1234",
    "papel": "USER",
}


def test_login_logout_e_me(client):
    resposta = client.get("/api/auth/me")
    assert resposta.status_code == 200
    assert resposta.get_json()["username"] == "dona"
    assert "senha_hash" not in resposta.get_json()

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_login_invalido(client):
    resposta = client.post("/api/auth/login", json={"username": "dona", "password": "errada"})
    assert resposta.status_code == 401


def test_crud_usuario(client):
    criado = client.post("/api/usuarios", json=NOVO)
    assert criado.status_code == 201
    corpo = criado.get_json()
    assert corpo["username"] == "maria.souza"
    assert corpo["papel"] == "USER"

    assert client.post("/api/usuarios", json=NOVO).status_code == 409

    usernames = [u["username"] for u in client.get("/api/usuarios").get_json()]
    assert "maria.souza" in usernames

    atualizado = client.put(f"/api/usuarios/{corpo['id']}", json={"papel": "ADMIN", "ativo": 0})
    assert atualizado.status_code == 200
    assert atualizado.get_json()["papel"] == "ADMIN"
    assert atualizado.get_json()["ativo"] == 0

    assert client.put("/api/usuarios/9999", json={"nome": "Alguém"}).status_code == 404


def test_nao_desativa_a_propria_conta(client):
    meu_id = client.get("/api/auth/me").get_json()["id"]
    resposta = client.put(f"/api/usuarios/{meu_id}", json={"ativo": 0})
    assert resposta.status_code == 409


def test_somente_proprietaria_gerencia_usuarios(app, client):
    client.post("/api/usuarios", json=NOVO)
    gestor = app.test_client()
    login = gestor.post("/api/auth/login", json={"username": "maria.souza", "password": NOVO["password"]})
    assert login.status_code == 200
    assert gestor.get("/api/usuarios").status_code == 403
    assert gestor.post("/api/usuarios", json=NOVO).status_code == 403
