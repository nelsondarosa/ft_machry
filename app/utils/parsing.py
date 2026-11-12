"""Parsing de requisições HTTP (corpo JSON e query string) para schemas Pydantic.

Comum a qualquer blueprint que valide entrada com Pydantic.
"""
from flask import request


def entrada(schema_cls):
    """Valida o corpo JSON da requisição contra um schema de entrada."""
    dados = request.get_json(silent=True)
    return schema_cls.model_validate(dados if isinstance(dados, dict) else {})


def consulta(schema_cls):
    """Valida a query string da requisição contra um schema de entrada."""
    return schema_cls.model_validate(request.args.to_dict())
