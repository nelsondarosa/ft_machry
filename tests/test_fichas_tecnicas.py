from app.features.fichas_tecnicas.models import FaseProducao
from db.database_config import db


URL = "/api/fichas-tecnicas"


def _produto(client, nome, tipo):
    resposta = client.post(
        "/api/produtos",
        json={"nome": nome, "tipo": tipo, "unidade_medida": "g"},
    )
    assert resposta.status_code == 201
    return resposta.get_json()["id"]


def _preparar(app, client):
    with app.app_context():
        db.session.add_all(
            [FaseProducao(nome="Preparar"), FaseProducao(nome="Cozinhar")]
        )
        db.session.commit()
        fases = db.session.query(FaseProducao).order_by(FaseProducao.id).all()
        fase_ids = [fase.id for fase in fases]
    insumo = _produto(client, "Farinha", "INSUMO")
    final = _produto(client, "Pão", "FINAL")
    return insumo, final, fase_ids


def test_crud_ficha_tecnica(app, client):
    insumo, final, fases = _preparar(app, client)
    payload = {
        "produto_id": final,
        "rendimento": 10,
        "observacao": "Receita base",
        "fases": [
            {"fase_id": fases[0], "ordem": 1, "tempo_previsto_min": 5},
            {"fase_id": fases[1], "ordem": 2, "tempo_previsto_min": 30},
        ],
        "componentes": [
            {"produto_id": insumo, "quantidade": 500, "fase_ordem": 1}
        ],
    }

    criada = client.post(URL, json=payload)
    assert criada.status_code == 201, criada.get_json()
    ficha = criada.get_json()
    assert ficha["produto"] == "Pão"
    assert ficha["componentes"][0]["fase_ordem"] == 1

    payload["rendimento"] = 12
    atualizada = client.put(f"{URL}/{ficha['id']}", json=payload)
    assert atualizada.status_code == 200
    assert atualizada.get_json()["rendimento"] == 12

    assert client.delete(f"{URL}/{ficha['id']}").status_code == 204
    assert client.get(f"{URL}/{ficha['id']}").status_code == 404


def test_regras_da_ficha(app, client):
    insumo, final, fases = _preparar(app, client)
    base = {
        "produto_id": final,
        "rendimento": 1,
        "fases": [{"fase_id": fases[0], "ordem": 1, "tempo_previsto_min": 5}],
        "componentes": [{"produto_id": insumo, "quantidade": 1}],
    }
    assert client.post(URL, json={**base, "produto_id": insumo}).status_code == 400
    assert client.post(URL, json={**base, "componentes": [{"produto_id": final, "quantidade": 1}]}).status_code == 400
    assert client.post(URL, json=base).status_code == 201
    assert client.post(URL, json=base).status_code == 409
    assert client.put(f"/api/produtos/{final}", json={"tipo": "INSUMO"}).status_code == 400
