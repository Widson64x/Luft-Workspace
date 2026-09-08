"""Camada de conexao com SQL Server utilizando LuftCore.

Este modulo centraliza a resolucao de configuracoes de ambiente,
construcao da extensao SQLAlchemy do LuftCore e exposicao de funcoes
utilitarias para obter sessao e engine.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from luftcore.extensions.sqlalchemy_extension import SqlAlchemyExtension
from sqlalchemy.orm import scoped_session

load_dotenv()


def ResolverBooleano(valor: object, padrao: bool = False) -> bool:
    """Resolve valores textuais em booleanos de forma tolerante.

    Parametros:
    valor: Valor bruto vindo de variavel de ambiente.
    padrao: Valor padrao quando nao for possivel inferir.

    Retorno:
    bool: Valor booleano normalizado.
    """
    if valor is None:
        return padrao
    if isinstance(valor, bool):
        return valor

    valor_normalizado = str(valor).strip().lower()
    if valor_normalizado in {"1", "true", "sim", "yes", "on"}:
        return True
    if valor_normalizado in {"0", "false", "nao", "não", "no", "off"}:
        return False
    return padrao


def NormalizarAmbienteVault(valor: str | None) -> str:
    """Normaliza aliases de ambiente para os caminhos do Vault."""
    aliases = {
        "prod": "producao",
        "producao": "producao",
        "produção": "producao",
        "production": "producao",
        "homolog": "homologacao",
        "homologacao": "homologacao",
        "homologação": "homologacao",
        "homologation": "homologacao",
        "dev": "desenvolvimento",
        "desenvolvimento": "desenvolvimento",
        "development": "desenvolvimento",
    }
    chave = (valor or "desenvolvimento").strip().lower()
    return aliases.get(chave, chave)


def ResolverCaminhoSqlServer() -> str:
    """Resolve o caminho do segredo SQL Server no Vault a partir de APP_ENV."""
    namespace = (os.getenv("VAULT_NAMESPACE") or "luft").strip().strip("/")
    ambiente = NormalizarAmbienteVault(
        os.getenv("APP_ENV") or os.getenv("AMBIENTE_ATUAL") or os.getenv("AMBIENTE_APP")
    )
    return f"{namespace}/{ambiente}/sqlserver"


@lru_cache(maxsize=1)
def ObterExtensaoSqlAlchemy() -> SqlAlchemyExtension:
    """Cria e cacheia a extensao SQLAlchemy do LuftCore para SQL Server.

    Retorno:
    SqlAlchemyExtension: Instancia pronta para abrir engine e sessoes.
    """
    caminho_sqlserver = ResolverCaminhoSqlServer()

    return SqlAlchemyExtension(
        vault_addr=os.getenv("VAULT_ADDR"),
        vault_token_criptografado=os.getenv("VAULT_TOKEN"),
        token_acesso=os.getenv("TOKEN_ACESSO"),
        caminho_segredo=caminho_sqlserver,
        tipo_banco="mssql",
        driver_banco=os.getenv("DB_DRIVER") or os.getenv("SQLDB_DRIVER") or "ODBC Driver 17 for SQL Server",
        parametros_conexao={
            "TrustServerCertificate": os.getenv("SQLDB_TRUST_SERVER_CERTIFICATE", "yes"),
        },
    )


def ObterUriSqlServer(ocultarSenha: bool = True) -> str:
    """Retorna a URI efetiva do SQL Server resolvida pelo LuftCore."""
    return ObterExtensaoSqlAlchemy().obter_uri_conexao(ocultar_senha=ocultarSenha)


_SESSAO_SCOPED: scoped_session | None = None


def GetSqlServerSession():
    """Retorna uma sessao scoped do SQLAlchemy para SQL Server vinculada ao contexto da thread.

    Retorno:
    Session: Sessao SQLAlchemy ativa no contexto atual.
    """
    global _SESSAO_SCOPED
    if _SESSAO_SCOPED is None:
        extensao = ObterExtensaoSqlAlchemy()
        _SESSAO_SCOPED = scoped_session(extensao.conector._session_factory)
    return _SESSAO_SCOPED()


def RemoverSessaoSqlServer() -> None:
    """Encerra e remove a sessao do contexto atual, liberando conexoes com o SQL Server."""
    global _SESSAO_SCOPED
    if _SESSAO_SCOPED is not None:
        _SESSAO_SCOPED.remove()


def GetSqlServerEngine():
    """Retorna a engine SQLAlchemy do SQL Server."""
    return ObterExtensaoSqlAlchemy().obter_engine()
