from contextlib import contextmanager

from db.database_config import db


class RepositorioBase:

    @contextmanager
    def transacao(self):
        try:
            yield db.session
        except Exception:
            db.session.rollback()
            raise
        else:
            db.session.commit()
