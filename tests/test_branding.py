import json

URL = "/api/branding"


def test_padrao_machry(app, monkeypatch):
    from app.utils.config import Config

    monkeypatch.delenv("BRANDING", raising=False)
    assert Config(_env_file=None).BRANDING == "machry"
    app.config["BRANDING"] = "machry"
    dados =app.test_client().get(URL).get_json()  # rota pública, sem login
    assert dados["nome"] == "Machry Armazém e Bistrô" and dados["sigla"] == "M"
    assert dados["logo"].startswith(f"{URL}/arquivos/logo.png?v=")
    assert dados["favicon"].startswith(f"{URL}/arquivos/favicon-32.png?v=")


def test_sem_branding_retorna_vazio(app):
    app.config["BRANDING"] = ""
    client = app.test_client()
    r = client.get(URL)  # rota pública, sem login
    assert r.status_code == 200
    assert r.get_json() == {}
    assert client.get(f"{URL}/arquivos/logo.svg").status_code == 404


def test_branding_custom(app, tmp_path):
    pasta = tmp_path / "marca"
    pasta.mkdir()
    (pasta / "logo.svg").write_text("<svg/>", encoding="utf-8")
    (pasta / "custom.css").write_text(":root{}", encoding="utf-8")
    (pasta / "brand.json").write_text(json.dumps({
        "nome": "Bistrô", "sigla": "B", "logo": "logo.svg", "css": "custom.css",
        "favicon": "inexistente.png", "apple_touch_icon": "../fora.png", "extra": 1,
    }), encoding="utf-8")
    app.config["BRANDING"] = str(pasta)
    client = app.test_client()

    dados = client.get(URL).get_json()
    assert dados["nome"] == "Bistrô" and dados["sigla"] == "B"
    assert dados["logo"].startswith(f"{URL}/arquivos/logo.svg?v=")
    assert dados["css"].startswith(f"{URL}/arquivos/custom.css?v=")
    assert "favicon" not in dados and "apple_touch_icon" not in dados and "extra" not in dados

    r = client.get(dados["logo"])
    assert r.status_code == 200 and r.data == b"<svg/>"
    assert client.get(f"{URL}/arquivos/../brand.json").status_code == 404


def test_branding_json_invalido(app, tmp_path):
    (tmp_path / "brand.json").write_text("{", encoding="utf-8")
    app.config["BRANDING"] = str(tmp_path)
    assert app.test_client().get(URL).get_json() == {}
