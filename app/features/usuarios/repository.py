from contextlib import contextmanager

from db.database_config import db

from .models import Usuario


class UsuarioRepository:
    @contextmanager
    def transacao(self):
        try:
            yield db.session
        except Exception:
            db.session.rollback()
            raise
        else:
            db.session.commit()

    def listar(self) -> list[Usuario]:
        return list(db.session.execute(db.select(Usuario).order_by(Usuario.nome)).scalars())

    def obter(self, usuario_id: int) -> Usuario | None:
        return db.session.get(Usuario, usuario_id)

    def obter_por_username(self, username: str) -> Usuario | None:
        return db.session.execute(
            db.select(Usuario).where(db.func.lower(Usuario.username) == username.lower())
        ).scalar_one_or_none()

    def inserir(self, dados: dict) -> Usuario:
        usuario = Usuario(**dados)
        db.session.add(usuario)
        db.session.flush()
        return usuario
