from app.utils.errors import registrar_tratadores_erro

from .routes import bp

registrar_tratadores_erro(bp)

__all__ = ["bp"]
