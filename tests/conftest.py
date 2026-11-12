import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE_PATH": str(tmp_path / "test.db"),
        "SECRET_KEY": "test-secret",
        "OWNER_INITIAL_PASSWORD": "Teste@123",
    })


@pytest.fixture
def client(app):
    # test_cli_runner não empurra app context como o comando `flask` faz.
    with app.app_context():
        result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    client = app.test_client()
    resposta = client.post(
        "/api/auth/login", json={"username": "dona", "password": "Teste@123"}
    )
    assert resposta.status_code == 200
    return client


@pytest.fixture
def seeded_client(app):
    """Cliente autenticado com o catálogo de demonstração carregado."""
    with app.app_context():
        result = app.test_cli_runner().invoke(args=["init-db", "--seed"])
    assert result.exit_code == 0, result.output

    client = app.test_client()
    resposta = client.post(
        "/api/auth/login", json={"username": "dona", "password": "Teste@123"}
    )
    assert resposta.status_code == 200
    return client
