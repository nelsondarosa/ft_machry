"""Tratamento de erro comum a qualquer blueprint da API.

Cada feature chama `registrar_tratadores_erro(bp)` uma vez (no seu
`__init__.py`) para converter exceções de validação/negócio em respostas HTTP,
em vez de repetir try/except em cada view.
"""
from flask import Blueprint
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


class RegistroNaoEncontrado(Exception):
    """A entidade identificada pela URL (path) não existe."""


class Conflito(Exception):
    """A operação conflita com outro registro ou com o histórico."""


def _resposta(msg, status=400):
    return {"erro": str(msg)}, status


def _mensagem_validacao(exc: ValidationError) -> str:
    msg = exc.errors()[0]["msg"]
    prefixo = "Value error, "
    return msg[len(prefixo):] if msg.startswith(prefixo) else msg


def registrar_tratadores_erro(bp: Blueprint) -> None:
    @bp.errorhandler(ValidationError)
    def _tratar_validacao(exc):
        return _resposta(_mensagem_validacao(exc))

    @bp.errorhandler(RegistroNaoEncontrado)
    def _tratar_nao_encontrado(exc):
        return _resposta(str(exc), 404)

    @bp.errorhandler(Conflito)
    def _tratar_conflito(exc):
        return _resposta(str(exc), 409)

    @bp.errorhandler(ValueError)
    def _tratar_valor_invalido(exc):
        return _resposta(str(exc))

    @bp.errorhandler(IntegrityError)
    def _tratar_integridade(exc):
        return _resposta("operação incompatível com registros existentes", 409)
