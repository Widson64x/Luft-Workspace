"""
Conexões do Luft-Workspace, com credenciais vindas do Vault através do LuftBase.

- PostgreSQL (schema da aplicação, ex.: connectair): tabelas próprias. Leitura e escrita.
- Core do LuftBase: ObterBancoCore(), para serviços que consultam a plataforma.

Padrão Luft: estas funções existem em todos os sistemas com o mesmo nome. Conexões que só um
sistema usa (ex.: o ERP somente leitura do ConnectAir) ficam no fim, em "Particularidades".
"""

import logging
import os
import re
import threading

from sqlalchemy.orm import sessionmaker

from App.Configuracoes import ConfiguracaoAtual

_logger = logging.getLogger(f"{ConfiguracaoAtual.APP_NAME}.Conexoes")
_trava = threading.Lock()
_inicializado = False
_banco_core = None
_engine_postgres = None
_sessoes_postgres = None


def _Carregador(configuracao):
    from luftbase.infraestrutura.cofre.cliente_hvac import ClienteVaultHvac
    from luftbase.infraestrutura.cofre.credenciais import Segredo
    from luftbase.infraestrutura.cofre.criptografia import DesprotetorFernet
    from luftbase.infraestrutura.cofre.servico import CarregadorCredenciais

    token = DesprotetorFernet(configuracao.cofre.token_acesso).revelar(configuracao.cofre.token_protegido)
    return CarregadorCredenciais(ClienteVaultHvac(configuracao.cofre.endereco, Segredo(token)))


def _Caminhos(configuracao, ambiente):
    from luftbase.configuracao.caminhos_vault import resolver_caminhos_vault

    return resolver_caminhos_vault(
        ambiente=ambiente,
        sistema_id=configuracao.aplicacao.sistema_id,
        namespace=configuracao.cofre.namespace,
    )


def _CriarEnginePostgres(configuracao):
    """Engine do schema da aplicação, igual à que o LuftBase monta na inicialização."""
    from luftbase.infraestrutura.banco.conexoes import ConstrutorEngines

    caminhos = _Caminhos(configuracao, configuracao.aplicacao.ambiente)
    credencial = _Carregador(configuracao).carregar_aplicacao_postgresql(
        caminhos.postgresql,
        caminhos.postgresql_conexoes,
        sistema_id_esperado=configuracao.aplicacao.sistema_id,
    ).banco
    construtor = ConstrutorEngines()
    return construtor.para_aplicacao(construtor.criar(credencial), credencial.esquema)


def _RegistrarPostgres(engine):
    global _engine_postgres, _sessoes_postgres
    _engine_postgres = engine
    _sessoes_postgres = sessionmaker(bind=engine) if engine is not None else None


def Inicializar(estado):
    """Registra as conexões a partir do estado do LuftBase (chamado pelo CriarApp)."""
    global _inicializado, _banco_core
    aplicacao = getattr(estado.bancos, "aplicacao", None)
    with _trava:
        _banco_core = estado.bancos.core
        _RegistrarPostgres(getattr(aplicacao, "engine", None))
        _InicializarParticularidades(estado)
        _inicializado = True


def _GarantirInicializado():
    """Scripts fora da aplicação Flask resolvem as engines direto do Vault, uma única vez."""
    global _inicializado
    if _inicializado:
        return
    with _trava:
        if _inicializado:
            return
        from luftbase.configuracao.modelos import ConfiguracaoLuftBase

        from App._version import __version__

        # A versão vem de App/_version.py; o .env só a define para forçá-la.
        if not (os.environ.get("LUFT_APLICACAO_VERSAO") or "").strip():
            os.environ["LUFT_APLICACAO_VERSAO"] = __version__
        configuracao = ConfiguracaoLuftBase.de_ambiente()
        configuracao.validar_para_inicializacao()
        _RegistrarPostgres(_CriarEnginePostgres(configuracao))
        _GarantirParticularidades(configuracao)
        _inicializado = True


# --- Core do LuftBase ------------------------------------------------------------------

def ObterBancoCore():
    """Banco `core` da plataforma (usuários, sistemas, permissões). Só com a aplicação iniciada."""
    if _banco_core is None:
        raise RuntimeError("O banco core só está disponível depois de Conexoes.Inicializar(estado).")
    return _banco_core


# --- Tabelas do sistema (PostgreSQL) ---------------------------------------------------

def ObterEnginePostgres():
    """Engine do schema da aplicação no PostgreSQL."""
    _GarantirInicializado()
    if _engine_postgres is None:
        raise RuntimeError("Esta aplicação não tem schema próprio configurado no Vault.")
    return _engine_postgres


def ObterSessaoPostgres():
    """Nova sessão das tabelas do sistema; quem abre é responsável por commit/rollback/close."""
    ObterEnginePostgres()
    return _sessoes_postgres()


def EsquemaPostgres():
    """Schema real da aplicação (do segredo no Vault), já validado pelo LuftBase."""
    from luftbase.infraestrutura.banco.conexoes import ESQUEMA_LOGICO_APLICACAO

    mapa = ObterEnginePostgres().get_execution_options().get("schema_translate_map") or {}
    return mapa.get(ESQUEMA_LOGICO_APLICACAO) or ESQUEMA_LOGICO_APLICACAO


def TabelaPostgres(nome):
    """Nome qualificado para SQL cru: TabelaPostgres('tb_frete') -> "connectair"."tb_frete".

    SQL cru não passa pela tradução de schema do ORM; use este helper em vez de fixar o schema.
    """
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", nome):
        raise ValueError(f"Nome de tabela inválido: {nome!r}")
    return f'"{EsquemaPostgres()}"."{nome}"'


# ========================================================================================
# Particularidades do Luft-Workspace
# ========================================================================================

def _InicializarParticularidades(estado):
    """Com a aplicação iniciada: o Hub não tem outras conexões."""


def _GarantirParticularidades(configuracao):
    """Em scripts, sem a aplicação: o Hub não tem outras conexões."""

