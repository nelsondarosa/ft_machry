from functools import wraps

from flask import g


def exigir_papeis(*papeis: str):
    def decorator(funcao):
        @wraps(funcao)
        def protegida(*args, **kwargs):
            if not getattr(g, "usuario", None):
                return {"erro": "autenticação necessária"}, 401
            if g.usuario.papel not in papeis:
                return {"erro": "você não tem permissão para esta ação"}, 403
            return funcao(*args, **kwargs)
        return protegida
    return decorator
