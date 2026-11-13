from db.database_config import db


class FaseProducao(db.Model):
    __tablename__ = "fase_producao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False, unique=True)


class FichaTecnica(db.Model):
    __tablename__ = "ficha_tecnica"
    __table_args__ = (
        db.CheckConstraint("rendimento > 0", name="ck_ficha_rendimento"),
    )

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(
        db.Integer, db.ForeignKey("produto.id"), nullable=False, unique=True
    )
    rendimento = db.Column(db.Numeric(18, 3), nullable=False)
    observacao = db.Column(db.Text)

    produto = db.relationship("Produto")
    fases = db.relationship(
        "FichaTecnicaFase",
        back_populates="ficha",
        cascade="all, delete-orphan",
        order_by="FichaTecnicaFase.ordem",
    )
    componentes = db.relationship(
        "FichaTecnicaComponente",
        back_populates="ficha",
        cascade="all, delete-orphan",
        foreign_keys="FichaTecnicaComponente.ficha_tecnica_id",
    )


class FichaTecnicaFase(db.Model):
    __tablename__ = "ficha_tecnica_fase"
    __table_args__ = (
        db.UniqueConstraint("ficha_tecnica_id", "ordem", name="uq_ficha_fase_ordem"),
        db.CheckConstraint("tempo_previsto_min > 0", name="ck_ficha_fase_tempo"),
        db.CheckConstraint("ordem > 0", name="ck_ficha_fase_ordem"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ficha_tecnica_id = db.Column(
        db.Integer, db.ForeignKey("ficha_tecnica.id"), nullable=False
    )
    fase_id = db.Column(db.Integer, db.ForeignKey("fase_producao.id"), nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    tempo_previsto_min = db.Column(db.Integer, nullable=False)

    ficha = db.relationship("FichaTecnica", back_populates="fases")
    fase = db.relationship("FaseProducao")


class FichaTecnicaComponente(db.Model):
    __tablename__ = "ficha_tecnica_componente"
    __table_args__ = (
        db.UniqueConstraint(
            "ficha_tecnica_id", "produto_id", name="uq_ficha_componente_produto"
        ),
        db.CheckConstraint("quantidade > 0", name="ck_ficha_componente_quantidade"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ficha_tecnica_id = db.Column(
        db.Integer, db.ForeignKey("ficha_tecnica.id"), nullable=False
    )
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade = db.Column(db.Numeric(18, 3), nullable=False)
    ficha_tecnica_fase_id = db.Column(
        db.Integer, db.ForeignKey("ficha_tecnica_fase.id")
    )

    ficha = db.relationship(
        "FichaTecnica", back_populates="componentes", foreign_keys=[ficha_tecnica_id]
    )
    produto = db.relationship("Produto")
    fase = db.relationship("FichaTecnicaFase")
