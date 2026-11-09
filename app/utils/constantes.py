"""Constantes globais compartilhadas entre as features."""
from typing import Literal, get_args


class Constantes:
    # -- paginação -----------------------------------------------------------

    POR_PAGINA_PADRAO = 20
    POR_PAGINA_MAXIMO = 100

    # -- autenticação --------------------------------------------------------

    ROTAS_PUBLICAS = {"/api/auth/login"}
    ROTAS_DE_SESSAO = {"/api/auth/me", "/api/auth/logout"}

    Papel = Literal["OWNER", "ADMIN", "USER"]
    PAPEIS = get_args(Papel)

    # -- produtos / estoque --------------------------------------------------

    TipoProduto = Literal["INSUMO", "INTERMEDIARIO", "FINAL"]
    TIPOS_PRODUTO = get_args(TipoProduto)

    TipoConservacao = Literal["CONGELADO", "RESFRIADO", "SECO"]
    TIPOS_CONSERVACAO = get_args(TipoConservacao)

    # Tipos que podem ser lançados manualmente pela API de movimentações.
    TipoMovimentacaoManual = Literal[
        "ENTRADA", "SAIDA", "AJUSTE_ENTRADA", "AJUSTE_SAIDA",
        "TRANSFERENCIA", "TRANSFORMACAO",
    ]

    # Todos os tipos aceitos no banco (inclui os gerados pela produção).
    TIPOS_MOVIMENTACAO = get_args(TipoMovimentacaoManual) + ("PRODUCAO", "CONSUMO_PRODUCAO")

    TIPOS_SOMAM_NA_ORIGEM = {"ENTRADA", "PRODUCAO", "AJUSTE_ENTRADA"}
    TIPOS_SUBTRAEM_DA_ORIGEM = {"SAIDA", "CONSUMO_PRODUCAO", "TRANSFERENCIA",
                                "TRANSFORMACAO", "AJUSTE_SAIDA"}
    TIPOS_COM_DESTINO = {"TRANSFERENCIA", "TRANSFORMACAO"}
    TIPOS_QUE_EXIGEM_SAIDA = {"SAIDA", "AJUSTE_SAIDA", "TRANSFERENCIA", "TRANSFORMACAO"}

    # -- produção ------------------------------------------------------------

    StatusSolicitacao = Literal["ABERTA", "EM_SEPARACAO", "EM_PRODUCAO", "CONCLUIDA", "CANCELADA"]
    STATUS_SOLICITACAO = get_args(StatusSolicitacao)

    TRANSICOES_SOLICITACAO: dict[str, set[str]] = {
        "ABERTA": {"EM_SEPARACAO", "EM_PRODUCAO", "CANCELADA"},
        "EM_SEPARACAO": {"EM_PRODUCAO", "CANCELADA"},
        "EM_PRODUCAO": {"CONCLUIDA", "CANCELADA"},
        "CONCLUIDA": set(),
        "CANCELADA": set(),
    }

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def sql_in(coluna: str, valores: tuple[str, ...]) -> str:
        """Monta a expressão `coluna IN ('A', 'B')` usada nos CHECKs do banco."""
        return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"
