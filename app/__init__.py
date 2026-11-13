import os
from datetime import timedelta

from flask import Flask, send_from_directory

from app.utils.config import config as app_config
from app.features import auth, branding, estoque, fichas_tecnicas, producao, produtos, usuarios
from app.middleware import registrar_middleware_autenticacao
from db.database_config import init_app as init_db

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_PATH = os.path.join(ROOT_PATH, "docs")

def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    prefixo_api = "/api"
    
    app.config.from_object(app_config)
    if config:
        app.config.update(config)
    if not config or "PERMANENT_SESSION_LIFETIME" not in config:
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
            minutes=int(app.config["SESSION_IDLE_MINUTES"])
        )

    init_db(app)

    registrar_middleware_autenticacao(app)

    app.register_blueprint(auth.bp, url_prefix=f"{prefixo_api}/auth")
    app.register_blueprint(branding.bp, url_prefix=f"{prefixo_api}/branding")
    app.register_blueprint(usuarios.bp, url_prefix=f"{prefixo_api}/usuarios")
    app.register_blueprint(produtos.bp, url_prefix=f"{prefixo_api}/produtos")
    app.register_blueprint(
        fichas_tecnicas.bp, url_prefix=f"{prefixo_api}/fichas-tecnicas"
    )
    app.register_blueprint(estoque.bp, url_prefix=f"{prefixo_api}/estoque")
    app.register_blueprint(producao.bp, url_prefix=f"{prefixo_api}/producao")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/openapi.yaml")
    def openapi():
        return send_from_directory(DOCS_PATH, "openapi.yaml")

    @app.get("/docs")
    def docs():
        return send_from_directory(DOCS_PATH, "swagger-ui.html")

    return app
