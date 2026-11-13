import os

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import URL, event, inspect, text
from werkzeug.security import generate_password_hash


db = SQLAlchemy()


def _montar_database_uri(config: dict):
    if config.get("DATABASE_URL"):
        return config["DATABASE_URL"]

    conexao = str(config.get("DB_CONNECTION", "sqlite")).lower()
    if conexao in {"postgres", "postgresql"}:
        return URL.create(
            "postgresql+psycopg2",
            username=config["DB_USERNAME"],
            password=config["DB_PASSWORD"],
            host=config["DB_HOST"],
            port=int(config["DB_PORT"]),
            database=config["DB_DATABASE"],
        )
    if conexao != "sqlite":
        raise ValueError("DB_CONNECTION deve ser sqlite, postgres ou postgresql")

    caminho = os.path.abspath(config["DATABASE_PATH"]).replace("\\", "/")
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    return f"sqlite:///{caminho}"


def _configurar_sqlite(engine) -> None:
    @event.listens_for(engine, "connect")
    def _configurar_conexao(conexao_dbapi, _):
        conexao_dbapi.execute("PRAGMA foreign_keys = ON")
        conexao_dbapi.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin_immediate(conexao):
        conexao.exec_driver_sql("BEGIN IMMEDIATE")


def _tabelas_existem(engine) -> bool:
    return inspect(engine).has_table("usuario")


def _migrar_autenticacao() -> None:
    colunas = {coluna["name"] for coluna in inspect(db.engine).get_columns("usuario")}
    if "username" not in colunas:
        db.session.execute(text("ALTER TABLE usuario ADD COLUMN username VARCHAR(80)"))
    if "senha_hash" not in colunas:
        db.session.execute(text("ALTER TABLE usuario ADD COLUMN senha_hash VARCHAR(255)"))
    db.session.commit()



def _migrar_produto() -> None:
    colunas = {coluna["name"] for coluna in inspect(db.engine).get_columns("produto")}
    if "subdivisao" not in colunas:
        db.session.execute(text("ALTER TABLE produto ADD COLUMN subdivisao TEXT"))
    db.session.commit()


def _migrar_lote() -> None:
    colunas = {coluna["name"] for coluna in inspect(db.engine).get_columns("lote")}
    for coluna in ("fornecedor", "nota_fiscal"):
        if coluna not in colunas:
            db.session.execute(text(f"ALTER TABLE lote ADD COLUMN {coluna} TEXT"))
    db.session.commit()


def _migrar_producao() -> None:
    colunas = {
        coluna["name"]
        for coluna in inspect(db.engine).get_columns("solicitacao_producao")
    }
    if "quantidade_planejada" not in colunas:
        db.session.execute(text(
            "ALTER TABLE solicitacao_producao "
            "ADD COLUMN quantidade_planejada NUMERIC NOT NULL DEFAULT 1"
        ))
        db.session.execute(text(
            "UPDATE solicitacao_producao SET quantidade_planejada = "
            "COALESCE((SELECT rendimento FROM ficha_tecnica "
            "WHERE ficha_tecnica.id = solicitacao_producao.ficha_tecnica_id), 1)"
        ))
    if "localizacao_destino_id" not in colunas:
        db.session.execute(text(
            "ALTER TABLE solicitacao_producao "
            "ADD COLUMN localizacao_destino_id INTEGER REFERENCES localizacao(id)"
        ))
    db.session.commit()


def _provisionar_usuarios_iniciais() -> None:
    from app.features.usuarios.models import Usuario
    from flask import current_app

    configuracoes = [
        ("Proprietária", current_app.config["OWNER_USERNAME"], current_app.config["OWNER_INITIAL_PASSWORD"], "OWNER"),
        ("Gestor", current_app.config["MANAGER_USERNAME"], current_app.config["MANAGER_INITIAL_PASSWORD"], "ADMIN"),
        ("Cozinha", current_app.config["COOK_USERNAME"], current_app.config["COOK_INITIAL_PASSWORD"], "USER"),
    ]
    usuarios = db.session.execute(db.select(Usuario).order_by(Usuario.id)).scalars().all()
    por_username = {usuario.username.lower(): usuario for usuario in usuarios if usuario.username}
    por_papel = {usuario.papel: usuario for usuario in usuarios if usuario.papel}

    for nome, username, password, papel in configuracoes:
        username = username.strip().lower()
        usuario = por_username.get(username)
        if usuario is None and papel == "OWNER":
            usuario = por_papel.get("OWNER") or por_papel.get("ADMIN")
        elif usuario is None and papel == "USER":
            usuario = por_papel.get("USER")
        if usuario is None:
            usuario = Usuario(nome=nome, username=username, senha_hash=generate_password_hash(password), papel=papel)
            db.session.add(usuario)
        else:
            usuario.username = usuario.username or username
            usuario.senha_hash = usuario.senha_hash or generate_password_hash(password)
            if papel == "OWNER":
                usuario.papel = "OWNER"
        por_username[username] = usuario
    db.session.commit()

    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_username ON usuario (username)"))
    db.session.commit()


VIEWS = {
    "vw_inventario": """
        SELECT p.id AS produto_id, p.nome AS produto, p.tipo AS tipo_produto,
               p.unidade_medida, l.id AS lote_id, l.quantidade,
               l.data_validade, loc.nome AS localizacao
          FROM lote l
          JOIN produto p ON p.id = l.produto_id
          JOIN localizacao loc ON loc.id = l.localizacao_id
         WHERE l.quantidade > 0
    """,
    "vw_fifo": """
        SELECT l.* FROM lote l WHERE l.quantidade > 0
         ORDER BY l.produto_id, l.data_validade ASC, l.criado_em ASC
    """,
    "vw_sp_componente": """
        SELECT c.id AS sp_componente_id, c.solicitacao_producao_id,
               c.produto_id, p.nome AS componente, p.unidade_medida,
               sf.ordem AS fase_ordem, fp.nome AS fase,
               c.quantidade_prevista,
               COALESCE(SUM(m.quantidade), 0) AS quantidade_realizada,
               SUM(m.quantidade * l.custo_unitario) AS custo_realizado
          FROM sp_componente c
          JOIN produto p ON p.id = c.produto_id
          LEFT JOIN sp_fase sf ON sf.id = c.sp_fase_id
          LEFT JOIN fase_producao fp ON fp.id = sf.fase_id
          LEFT JOIN movimentacao_estoque m
                 ON m.sp_componente_id = c.id AND m.tipo = 'CONSUMO_PRODUCAO'
          LEFT JOIN lote l ON l.id = m.lote_id
         GROUP BY c.id, c.solicitacao_producao_id, c.produto_id, p.nome,
                  p.unidade_medida, sf.ordem, fp.nome, c.quantidade_prevista
    """,
    "vw_sp_producao": """
        SELECT m.solicitacao_producao_id, m.lote_id, m.quantidade, m.criado_em
          FROM movimentacao_estoque m WHERE m.tipo = 'PRODUCAO'
    """,
}


def _criar_views() -> None:
    for nome, consulta in VIEWS.items():
        db.session.execute(text(f"CREATE VIEW {nome} AS {consulta}"))
    db.session.commit()


@click.command("init-db")
@click.option("--seed", is_flag=True, help="Também carrega os dados de exemplo.")
def init_db_command(seed: bool):
    if _tabelas_existem(db.engine):
        db.create_all()
        _migrar_autenticacao()
        _migrar_produto()
        _migrar_lote()
        _migrar_producao()
        _provisionar_usuarios_iniciais()
        click.echo("Banco já criado e atualizado")
        return

    db.create_all()
    _criar_views()
    if seed:
        from db.seed import carregar_seeds

        carregar_seeds()
    _provisionar_usuarios_iniciais()
    click.echo("Banco inicializado." + (" (com seeds)" if seed else ""))


def _tabelas_do_catalogo() -> list:
    """Tabela `produto` e todas as que dependem dela (fichas, estoque, produção), na ordem de exclusão."""
    alvo = {"produto"}
    mudou = True
    while mudou:
        mudou = False
        for tabela in db.metadata.tables.values():
            if tabela.name not in alvo and any(fk.column.table.name in alvo for fk in tabela.foreign_keys):
                alvo.add(tabela.name)
                mudou = True
    return [t for t in reversed(db.metadata.sorted_tables) if t.name in alvo]


@click.command("limpar-catalogo")
@click.option("--sim", is_flag=True, help="Não pede confirmação.")
def limpar_catalogo_command(sim: bool):
    """Apaga produtos e fichas técnicas (e lotes, estoque e produção ligados a eles).

    Usuários, fases de produção, grupos e localizações são mantidos.
    """
    tabelas = _tabelas_do_catalogo()
    nomes = ", ".join(t.name for t in tabelas)
    if not sim:
        click.confirm(f"Apagar todos os registros de: {nomes}?", abort=True)
    for tabela in tabelas:
        db.session.execute(tabela.delete())
    db.session.commit()
    click.echo(f"Catálogo limpo: {nomes}.")


def init_app(app: Flask):
    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.config["SQLALCHEMY_DATABASE_URI"] = _montar_database_uri(app.config)
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            _configurar_sqlite(db.engine)

    app.cli.add_command(init_db_command)
    app.cli.add_command(limpar_catalogo_command)
