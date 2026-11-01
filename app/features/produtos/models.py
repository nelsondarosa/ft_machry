from db.database_config import db


class GrupoProduto(db.Model):
    __tablename__ = "grupo_produto"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False, unique=True)


class Produto(db.Model):
    __tablename__ = "produto"
    __table_args__ = (
        db.CheckConstraint(
            "tipo IN ('INSUMO', 'INTERMEDIARIO', 'FINAL')",
            name="ck_produto_tipo",
        ),
        db.CheckConstraint(
            "conservacao IN ('CONGELADO', 'RESFRIADO', 'SECO')",
            name="ck_produto_conservacao",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Text, nullable=False)
    unidade_medida = db.Column(db.Text, nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey("grupo_produto.id"))
    conservacao = db.Column(db.Text, nullable=False, default="SECO", server_default="SECO")
    validade_obrigatoria = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    validade_padrao_dias = db.Column(db.Integer)
    foto_url = db.Column(db.Text)
    ativo = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    criado_em = db.Column(
        db.Text,
        nullable=False,
        server_default=db.text("(CAST(CURRENT_TIMESTAMP AS TEXT))"),
    )
