"""Dados mínimos de demonstração, inseridos via ORM em qualquer banco suportado."""

from app.features.estoque.models import Localizacao, ProdutoTransformacao
from app.features.usuarios.models import Usuario
from app.features.fichas_tecnicas.models import (
    FaseProducao,
    FichaTecnica,
    FichaTecnicaComponente,
    FichaTecnicaFase,
)
from app.features.produtos.models import GrupoProduto, Produto
from db.database_config import db
from sqlalchemy import text


def carregar_seeds() -> None:
    fases = [
        FaseProducao(id=1, nome="Bater/Misturar"),
        FaseProducao(id=2, nome="Cozir"),
        FaseProducao(id=3, nome="Confeitar"),
        FaseProducao(id=4, nome="Fritar"),
        FaseProducao(id=5, nome="Montar"),
    ]
    grupos = [
        GrupoProduto(id=1, nome="Insumos secos"),
        GrupoProduto(id=2, nome="Laticínios"),
        GrupoProduto(id=3, nome="Semiacabados"),
        GrupoProduto(id=4, nome="Confeitaria"),
    ]
    localizacoes = [
        Localizacao(id=1, nome="Estoque Seco", tipo="SECO"),
        Localizacao(id=2, nome="Câmara Fria", tipo="RESFRIADO"),
        Localizacao(id=3, nome="Câmara Fria - Congelados", tipo="CONGELADO", parent_id=2),
        Localizacao(id=4, nome="Câmara Fria - Resfriados", tipo="RESFRIADO", parent_id=2),
        Localizacao(id=5, nome="Cozinha", tipo="SECO"),
        Localizacao(id=6, nome="Geladeira da Cozinha", tipo="RESFRIADO", parent_id=5),
        Localizacao(id=7, nome="Padaria", tipo="SECO"),
    ]
    produtos = [
        Produto(id=1, nome="Farinha de trigo", tipo="INSUMO", unidade_medida="g", grupo_id=1, conservacao="SECO", validade_obrigatoria=0, validade_padrao_dias=180),
        Produto(id=2, nome="Ovo", tipo="INSUMO", unidade_medida="un", grupo_id=2, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=20),
        Produto(id=3, nome="Leite", tipo="INSUMO", unidade_medida="ml", grupo_id=2, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=7),
        Produto(id=4, nome="Nozes", tipo="INSUMO", unidade_medida="g", grupo_id=1, conservacao="SECO", validade_obrigatoria=0, validade_padrao_dias=90),
        Produto(id=5, nome="Queijo (bloco)", tipo="INSUMO", unidade_medida="g", grupo_id=2, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=30),
        Produto(id=6, nome="Queijo ralado", tipo="INTERMEDIARIO", unidade_medida="g", grupo_id=2, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=7),
        Produto(id=7, nome="Creme de nozes", tipo="INTERMEDIARIO", unidade_medida="g", grupo_id=3, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=3),
        Produto(id=8, nome="Massa de bolo", tipo="INTERMEDIARIO", unidade_medida="g", grupo_id=3, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=2),
        Produto(id=9, nome="Chantili", tipo="INTERMEDIARIO", unidade_medida="g", grupo_id=3, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=2),
        Produto(id=10, nome="Bolo de Nozes - Médio", tipo="FINAL", unidade_medida="un", grupo_id=4, conservacao="RESFRIADO", validade_obrigatoria=1, validade_padrao_dias=4),
    ]
    db.session.add_all(fases + grupos + localizacoes)
    db.session.flush()
    db.session.add_all(produtos)
    db.session.flush()
    db.session.add(ProdutoTransformacao(produto_origem_id=5, produto_destino_id=6))

    ficha = FichaTecnica(id=1, produto_id=10, rendimento=1)
    fase_1 = FichaTecnicaFase(id=1, fase_id=1, ordem=1, tempo_previsto_min=10)
    fase_2 = FichaTecnicaFase(id=2, fase_id=2, ordem=2, tempo_previsto_min=30)
    fase_3 = FichaTecnicaFase(id=3, fase_id=3, ordem=3, tempo_previsto_min=15)
    ficha.fases.extend([fase_1, fase_2, fase_3])
    ficha.componentes.extend(
        [
            FichaTecnicaComponente(produto_id=8, quantidade=400, fase=fase_1),
            FichaTecnicaComponente(produto_id=3, quantidade=300, fase=fase_1),
            FichaTecnicaComponente(produto_id=7, quantidade=500, fase=fase_3),
            FichaTecnicaComponente(produto_id=9, quantidade=50, fase=fase_3),
            FichaTecnicaComponente(produto_id=4, quantidade=100, fase=fase_3),
        ]
    )
    db.session.add(ficha)
    db.session.flush()

    if db.engine.dialect.name == "postgresql":
        for tabela in (
            "usuario",
            "fase_producao",
            "grupo_produto",
            "localizacao",
            "produto",
            "ficha_tecnica",
            "ficha_tecnica_fase",
            "ficha_tecnica_componente",
        ):
            db.session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence(:tabela, 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {tabela}), 1), true)"
                ),
                {"tabela": tabela},
            )
    db.session.commit()
