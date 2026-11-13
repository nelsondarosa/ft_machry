"""Identidade visual configurável (nome, logo, ícones e CSS custom).

A variável de ambiente BRANDING aponta para uma pasta com `brand.json`:
o nome de uma subpasta de `branding/` na raiz do projeto ou um caminho
absoluto. O padrão é `machry`; com a variável vazia, a rota devolve `{}` e o
frontend usa os textos embutidos (os mesmos da pasta `machry`).
"""
import hashlib
import json
import os

from flask import Blueprint, abort, current_app, send_from_directory

bp = Blueprint("branding", __name__)

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TEXTOS = ("nome", "subtitulo", "sigla", "titulo")
ARQUIVOS = ("logo", "favicon", "apple_touch_icon", "css")


def pasta_branding() -> str | None:
    valor = (current_app.config.get("BRANDING") or "").strip()
    if not valor:
        return None
    pasta = valor if os.path.isabs(valor) else os.path.join(ROOT_PATH, "branding", valor)
    return os.path.abspath(pasta)


def _ler_config(pasta: str) -> dict:
    caminho = os.path.join(pasta, "brand.json")
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, ValueError) as exc:
        current_app.logger.warning("BRANDING ignorado: não foi possível ler %s (%s)", caminho, exc)
        return {}
    return dados if isinstance(dados, dict) else {}


@bp.get("")
def obter():
    pasta = pasta_branding()
    if pasta is None:
        return {}
    dados = _ler_config(pasta)
    resposta = {campo: dados[campo].strip() for campo in TEXTOS if isinstance(dados.get(campo), str) and dados[campo].strip()}
    for campo in ARQUIVOS:
        nome = dados.get(campo)
        if not isinstance(nome, str) or not nome:
            continue
        caminho = os.path.abspath(os.path.join(pasta, nome))
        if not caminho.startswith(pasta + os.sep) or not os.path.isfile(caminho):
            current_app.logger.warning("BRANDING: arquivo %r de %r não encontrado", nome, campo)
            continue
        versao = hashlib.md5(open(caminho, "rb").read()).hexdigest()[:10]  # muda com o conteúdo, não com a data
        resposta[campo] = f"/api/branding/arquivos/{nome.replace(os.sep, '/')}?v={versao}"
    return resposta


@bp.get("/arquivos/<path:nome>")
def arquivo(nome: str):
    pasta = pasta_branding()
    if pasta is None:
        abort(404)
    return send_from_directory(pasta, nome, max_age=3600)
