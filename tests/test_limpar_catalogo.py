def test_limpar_catalogo_mantem_usuarios_e_fases(app, seeded_client):
    assert seeded_client.get("/api/produtos").get_json()["items"]
    assert seeded_client.get("/api/fichas-tecnicas").get_json()["items"]

    with app.app_context():
        result = app.test_cli_runner().invoke(args=["limpar-catalogo", "--sim"])
    assert result.exit_code == 0, result.output

    assert seeded_client.get("/api/produtos").get_json()["items"] == []
    assert seeded_client.get("/api/fichas-tecnicas").get_json()["items"] == []
    assert seeded_client.get("/api/fichas-tecnicas/fases").get_json()["items"]  # fases continuam
    assert seeded_client.get("/api/auth/me").status_code == 200  # sessão e usuário continuam


def test_limpar_catalogo_pede_confirmacao(app, seeded_client):
    with app.app_context():
        result = app.test_cli_runner().invoke(args=["limpar-catalogo"], input="n\n")
    assert result.exit_code != 0
    assert seeded_client.get("/api/produtos").get_json()["items"]
