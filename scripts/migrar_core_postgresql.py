"""Migra as tabelas sistemicas do SQL Server para o PostgreSQL ``luft_web``.

Origens:
    - ``luft/producao/sqlserver``: seguranca, auditoria e notificacoes.
    - ``luft/homologacao/sqlserver``: publicacoes e seus itens/vinculos.

Destino:
    - ``luft/desenvolvimento/postgresql``, schema ``core`` por padrao.

O comando padrao executa somente o diagnostico. Para gravar no PostgreSQL e
necessario informar ``--executar --confirmar MIGRAR_CORE_LOCAL``. Toda consulta
ao SQL Server passa por uma barreira que rejeita DDL e DML antes de chegar ao
driver. A criacao e a carga no PostgreSQL acontecem em uma unica transacao.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

import pyodbc
from dotenv import load_dotenv
from luftbase.infraestrutura.banco.conexoes import ConstrutorEngines
from luftbase.infraestrutura.cofre.cliente_hvac import ClienteVaultHvac
from luftbase.infraestrutura.cofre.credenciais import Segredo, TipoBanco
from luftbase.infraestrutura.cofre.criptografia import DesprotetorFernet
from luftbase.infraestrutura.cofre.servico import CarregadorCredenciais
from sqlalchemy import event, text
from sqlalchemy.engine import Connection, Engine, Row

CAMINHO_SQLSERVER_PRD = "luft/producao/sqlserver"
CAMINHO_SQLSERVER_HML = "luft/homologacao/sqlserver"
CAMINHO_POSTGRESQL = "luft/desenvolvimento/postgresql"
BANCO_DESTINO_ESPERADO = "luft_web"
SCHEMA_DESTINO = "core"
CONFIRMACAO_EXECUCAO = "MIGRAR_CORE_LOCAL"
CONFIRMACAO_SUBSTITUICAO = "SUBSTITUIR_TABELAS_CORE"

IDENTIFICADOR_SEGURO = re.compile(r"^[a-z_][a-z0-9_]*$")
COMANDO_FONTE_PERMITIDO = re.compile(r"^\s*(?:SELECT|WITH)\b", re.IGNORECASE)

# O pool nativo do pyodbc pode manter conexoes abertas depois do dispose da
# engine. Desabilita-lo reduz o tempo de vida das conexoes com producao.
pyodbc.pooling = False


class ErroMigracao(RuntimeError):
    """Falha controlada que deve cancelar integralmente a migracao."""


@dataclass(frozen=True)
class EspecificacaoTabela:
    origem: str
    destino: str
    colunas: tuple[tuple[str, str], ...]
    chave_ordenacao: tuple[str, ...]
    coluna_identidade: str | None = None

    @property
    def colunas_origem(self) -> tuple[str, ...]:
        return tuple(origem for origem, _ in self.colunas)

    @property
    def colunas_destino(self) -> tuple[str, ...]:
        return tuple(destino for _, destino in self.colunas)


TABELAS_PRD: tuple[EspecificacaoTabela, ...] = (
    EspecificacaoTabela(
        "Tb_Sistema",
        "tb_sistema",
        (
            ("Id_Sistema", "id_sistema"),
            ("Nome_Sistema", "nome_sistema"),
            ("Descricao_Sistema", "descricao_sistema"),
            ("Ativo", "ativo"),
            ("Em_Manutencao", "em_manutencao"),
            ("Icone", "icone"),
            ("Link", "link"),
            ("Id_Permissao_Base", "id_permissao_base"),
        ),
        ("Id_Sistema",),
        "id_sistema",
    ),
    EspecificacaoTabela(
        "Tb_Permissao",
        "tb_permissao",
        (
            ("Id_Permissao", "id_permissao"),
            ("Chave_Permissao", "chave_permissao"),
            ("Descricao_Permissao", "descricao_permissao"),
            ("Categoria_Permissao", "categoria_permissao"),
            ("Id_Sistema", "id_sistema"),
        ),
        ("Id_Permissao",),
        "id_permissao",
    ),
    EspecificacaoTabela(
        "Tb_PermissaoGrupo",
        "tb_permissaogrupo",
        (
            ("Id_Vinculo", "id_vinculo"),
            ("Codigo_UsuarioGrupo", "codigo_usuariogrupo"),
            ("Id_Permissao", "id_permissao"),
        ),
        ("Id_Vinculo",),
        "id_vinculo",
    ),
    EspecificacaoTabela(
        "Tb_PermissaoUsuario",
        "tb_permissaousuario",
        (
            ("Id_Vinculo", "id_vinculo"),
            ("Codigo_Usuario", "codigo_usuario"),
            ("Id_Permissao", "id_permissao"),
            ("Conceder", "conceder"),
        ),
        ("Id_Vinculo",),
        "id_vinculo",
    ),
    EspecificacaoTabela(
        "Tb_LogAcesso",
        "tb_logacesso",
        (
            ("Id_Log", "id_log"),
            ("Id_Usuario", "id_usuario"),
            ("Nome_Usuario", "nome_usuario"),
            ("Rota_Acessada", "rota_acessada"),
            ("Metodo_Http", "metodo_http"),
            ("Ip_Origem", "ip_origem"),
            ("Permissao_Exigida", "permissao_exigida"),
            ("Acesso_Permitido", "acesso_permitido"),
            ("Data_Hora", "data_hora"),
            ("Id_Sistema", "id_sistema"),
            ("Parametros_Requisicao", "parametros_requisicao"),
            ("Resposta_Acao", "resposta_acao"),
        ),
        ("Id_Log",),
        "id_log",
    ),
    EspecificacaoTabela(
        "Tb_LogDetalhe",
        "tb_logdetalhe",
        (
            ("Id_LogDetalhe", "id_logdetalhe"),
            ("Id_Sistema", "id_sistema"),
            ("Id_LogAcesso", "id_logacesso"),
            ("Id_Usuario", "id_usuario"),
            ("Nome_Usuario", "nome_usuario"),
            ("Acao", "acao"),
            ("Recurso", "recurso"),
            ("Id_Recurso", "id_recurso"),
            ("Descricao", "descricao"),
            ("Dados_Anteriores_Json", "dados_anteriores_json"),
            ("Dados_Novos_Json", "dados_novos_json"),
            ("Ip_Origem", "ip_origem"),
            ("User_Agent", "user_agent"),
            ("Data_Hora", "data_hora"),
            ("Severidade", "severidade"),
            ("Traceback", "traceback"),
        ),
        ("Id_LogDetalhe",),
        "id_logdetalhe",
    ),
    EspecificacaoTabela(
        "Tb_Notificacao",
        "tb_notificacao",
        (
            ("Id_Notificacao", "id_notificacao"),
            ("Id_Sistema", "id_sistema"),
            ("Id_Usuario_Destino", "id_usuario_destino"),
            ("Tipo", "tipo"),
            ("Categoria", "categoria"),
            ("Titulo", "titulo"),
            ("Mensagem", "mensagem"),
            ("Icone", "icone"),
            ("Lida", "lida"),
            ("Data_Criacao", "data_criacao"),
            ("Data_Leitura", "data_leitura"),
            ("Criado_Por", "criado_por"),
            ("Metadados_Json", "metadados_json"),
            ("Expira_Em", "expira_em"),
            ("Id_Grupo_Destino", "id_grupo_destino"),
            ("Exibir_A_Partir_De", "exibir_a_partir_de"),
        ),
        ("Id_Notificacao",),
        "id_notificacao",
    ),
    EspecificacaoTabela(
        "Tb_Notificacao_Leitura",
        "tb_notificacao_leitura",
        (
            ("Id_Notificacao", "id_notificacao"),
            ("Id_Usuario", "id_usuario"),
            ("Data_Leitura", "data_leitura"),
        ),
        ("Id_Notificacao", "Id_Usuario"),
    ),
)

TABELAS_HML: tuple[EspecificacaoTabela, ...] = (
    EspecificacaoTabela(
        "Tb_Publicacao",
        "tb_publicacao",
        (
            ("Id_Publicacao", "id_publicacao"),
            ("Id_Sistema", "id_sistema"),
            ("Tipo_Publicacao", "tipo_publicacao"),
            ("Status_Publicacao", "status_publicacao"),
            ("Tipo_Audiencia", "tipo_audiencia"),
            ("Titulo", "titulo"),
            ("Resumo", "resumo"),
            ("Conteudo", "conteudo"),
            ("Prioridade", "prioridade"),
            ("Versao", "versao"),
            ("Notificar", "notificar"),
            ("Fixado", "fixado"),
            ("Exibir_A_Partir_De", "exibir_a_partir_de"),
            ("Expira_Em", "expira_em"),
            ("Data_Publicacao", "data_publicacao"),
            ("Data_Criacao", "data_criacao"),
            ("Data_Atualizacao", "data_atualizacao"),
            ("Criado_Por_Id", "criado_por_id"),
            ("Criado_Por", "criado_por"),
            ("Atualizado_Por_Id", "atualizado_por_id"),
            ("Atualizado_Por", "atualizado_por"),
            ("Fonte", "fonte"),
            ("Id_Externo", "id_externo"),
            ("Thread_Externo", "thread_externo"),
            ("Remetente_Externo", "remetente_externo"),
            ("Url_Externa", "url_externa"),
            ("Metadados_Json", "metadados_json"),
        ),
        ("Id_Publicacao",),
        "id_publicacao",
    ),
    EspecificacaoTabela(
        "Tb_PublicacaoGrupo",
        "tb_publicacaogrupo",
        (("Id_Publicacao", "id_publicacao"), ("Id_Grupo", "id_grupo")),
        ("Id_Publicacao", "Id_Grupo"),
    ),
    EspecificacaoTabela(
        "Tb_PublicacaoLeitura",
        "tb_publicacaoleitura",
        (
            ("Id_Publicacao", "id_publicacao"),
            ("Id_Usuario", "id_usuario"),
            ("Data_Leitura", "data_leitura"),
        ),
        ("Id_Publicacao", "Id_Usuario"),
    ),
    EspecificacaoTabela(
        "Tb_PublicacaoNotificacao",
        "tb_publicacaonotificacao",
        (
            ("Id_Vinculo", "id_vinculo"),
            ("Id_Publicacao", "id_publicacao"),
            ("Id_Notificacao", "id_notificacao"),
            ("Data_Criacao", "data_criacao"),
        ),
        ("Id_Vinculo",),
        "id_vinculo",
    ),
    EspecificacaoTabela(
        "Tb_NotaAtualizacaoItem",
        "tb_notaatualizacaoitem",
        (
            ("Id_Item", "id_item"),
            ("Id_Publicacao", "id_publicacao"),
            ("Tipo_Item", "tipo_item"),
            ("Titulo", "titulo"),
            ("Descricao", "descricao"),
            ("Ordem", "ordem"),
        ),
        ("Id_Item",),
        "id_item",
    ),
)

ESPECIFICACAO_NOTIFICACAO = next(
    tabela for tabela in TABELAS_PRD if tabela.origem == "Tb_Notificacao"
)


def proteger_comando_fonte(comando: str) -> None:
    """Rejeita qualquer comando de origem que nao seja SELECT/CTE."""
    if not COMANDO_FONTE_PERMITIDO.match(comando):
        primeiro_token = (
            comando.strip().split(maxsplit=1)[0] if comando.strip() else "vazio"
        )
        raise ErroMigracao(
            f"Comando '{primeiro_token}' bloqueado: SQL Server aceita somente leitura."
        )


def instalar_barreira_somente_leitura(engine: Engine, nome: str) -> None:
    """Instala uma segunda linha de defesa diretamente na engine SQL Server."""

    @event.listens_for(engine, "before_cursor_execute")
    def _validar_comando(
        _conn: Connection,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        try:
            proteger_comando_fonte(statement)
        except ErroMigracao as erro:
            raise ErroMigracao(f"[{nome}] {erro}") from erro


def executar_fonte(
    conexao: Connection, comando: str, parametros: dict[str, Any] | None = None
):
    proteger_comando_fonte(comando)
    return conexao.execute(text(comando), parametros or {})


def criar_engine_vault(
    caminho: str,
    tipo_banco: str,
    driver: str,
    somente_leitura: bool = False,
) -> Engine:
    endereco = _variavel_ambiente("LUFT_VAULT_ENDERECO", "VAULT_ADDR")
    token_protegido = _variavel_ambiente("LUFT_VAULT_TOKEN", "VAULT_TOKEN")
    token_acesso = _variavel_ambiente("LUFT_TOKEN_ACESSO", "TOKEN_ACESSO")
    token_vault = DesprotetorFernet(token_acesso).revelar(token_protegido)
    credenciais = CarregadorCredenciais(
        ClienteVaultHvac(endereco, Segredo(token_vault))
    )
    tipo = TipoBanco.SQLSERVER if tipo_banco == "mssql" else TipoBanco.POSTGRESQL
    credencial = credenciais.carregar_banco(
        caminho,
        tipo,
        permitir_usuario_administrativo=True,
    )
    if tipo is TipoBanco.SQLSERVER and not credencial.driver:
        credencial = replace(credencial, driver=driver)
    engine = ConstrutorEngines().criar(credencial)
    if somente_leitura:
        instalar_barreira_somente_leitura(engine, caminho)
    return engine


def _variavel_ambiente(nome: str, alias: str) -> str:
    valor = (os.getenv(nome) or os.getenv(alias) or "").strip()
    if not valor:
        raise ErroMigracao(f"Variavel obrigatoria ausente: {nome}")
    return valor


def validar_variaveis_ambiente() -> None:
    ausentes = [
        nome
        for nome, alias in (
            ("LUFT_VAULT_ENDERECO", "VAULT_ADDR"),
            ("LUFT_VAULT_TOKEN", "VAULT_TOKEN"),
            ("LUFT_TOKEN_ACESSO", "TOKEN_ACESSO"),
        )
        if not (os.getenv(nome) or os.getenv(alias) or "").strip()
    ]
    if ausentes:
        raise ErroMigracao(
            "Variaveis obrigatorias ausentes: " + ", ".join(sorted(ausentes))
        )


def citar_identificador(nome: str) -> str:
    if not IDENTIFICADOR_SEGURO.fullmatch(nome):
        raise ErroMigracao(f"Identificador PostgreSQL invalido: {nome!r}")
    return f'"{nome}"'


def nome_qualificado(schema: str, tabela: str) -> str:
    return f"{citar_identificador(schema)}.{citar_identificador(tabela)}"


def sql_selecao(
    tabela: EspecificacaoTabela,
    *,
    filtro: str | None = None,
) -> str:
    colunas = ", ".join(f"src.[{coluna}]" for coluna in tabela.colunas_origem)
    ordem = ", ".join(f"src.[{coluna}]" for coluna in tabela.chave_ordenacao)
    clausula_filtro = f" WHERE {filtro}" if filtro else ""
    return (
        f"SELECT {colunas} FROM intec.dbo.[{tabela.origem}] AS src"
        f"{clausula_filtro} ORDER BY {ordem}"
    )


def sql_insert(schema: str, tabela: EspecificacaoTabela) -> str:
    colunas = ", ".join(citar_identificador(nome) for nome in tabela.colunas_destino)
    valores = ", ".join(f":{nome}" for nome in tabela.colunas_destino)
    return f"INSERT INTO {nome_qualificado(schema, tabela.destino)} ({colunas}) VALUES ({valores})"


def iterar_lotes(
    conexao: Connection,
    tabela: EspecificacaoTabela,
    tamanho_lote: int,
    *,
    filtro: str | None = None,
) -> Iterator[list[dict[str, Any]]]:
    resultado = executar_fonte(
        conexao.execution_options(stream_results=True),
        sql_selecao(tabela, filtro=filtro),
    )
    while True:
        linhas: Sequence[Row[Any]] = resultado.fetchmany(tamanho_lote)
        if not linhas:
            break
        yield [
            dict(zip(tabela.colunas_destino, linha, strict=True)) for linha in linhas
        ]


Transformacao = Callable[[dict[str, Any]], dict[str, Any]]


def carregar_tabela(
    origem: Connection,
    destino: Connection,
    schema: str,
    tabela: EspecificacaoTabela,
    tamanho_lote: int,
    *,
    filtro: str | None = None,
    transformar: Transformacao | None = None,
) -> int:
    comando_insert = text(sql_insert(schema, tabela))
    quantidade = 0
    for lote in iterar_lotes(origem, tabela, tamanho_lote, filtro=filtro):
        if transformar:
            lote = [transformar(linha) for linha in lote]
        destino.execute(comando_insert, lote)
        quantidade += len(lote)
        print(f"  {tabela.destino}: {quantidade} registros", end="\r", flush=True)
    print(f"  {tabela.destino}: {quantidade} registros")
    return quantidade


def obter_tabelas_existentes(conexao: Connection, schema: str) -> set[str]:
    resultado = conexao.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_type = 'BASE TABLE'"
        ),
        {"schema": schema},
    )
    return set(resultado.scalars())


def obter_identidade_fonte(conexao: Connection) -> tuple[str, str]:
    linha = executar_fonte(
        conexao,
        "SELECT CAST(@@SERVERNAME AS varchar(255)), CAST(DB_NAME() AS varchar(255))",
    ).one()
    return str(linha[0]), str(linha[1])


def obter_identidade_destino(conexao: Connection) -> tuple[str, str, str]:
    linha = conexao.execute(
        text(
            "SELECT COALESCE(inet_server_addr()::text, 'local'), "
            "current_database(), current_user"
        )
    ).one()
    return str(linha[0]), str(linha[1]), str(linha[2])


def validar_tabelas_fonte(
    conexao: Connection,
    tabelas: Iterable[str],
    ambiente: str,
) -> None:
    esperadas = set(tabelas)
    resultado = executar_fonte(
        conexao,
        "SELECT t.name FROM intec.sys.tables AS t "
        "JOIN intec.sys.schemas AS s ON s.schema_id = t.schema_id "
        "WHERE s.name = 'dbo'",
    )
    existentes = set(resultado.scalars())
    ausentes = sorted(esperadas - existentes)
    if ausentes:
        raise ErroMigracao(
            f"Tabelas ausentes no SQL Server {ambiente}: {', '.join(ausentes)}"
        )


def validar_colunas_fonte(
    conexao: Connection,
    tabelas: Iterable[EspecificacaoTabela],
    ambiente: str,
) -> None:
    esperadas = {tabela.origem: set(tabela.colunas_origem) for tabela in tabelas}
    nomes = sorted(esperadas)
    parametros = {f"tabela_{indice}": nome for indice, nome in enumerate(nomes)}
    marcadores = ", ".join(f":tabela_{indice}" for indice in range(len(nomes)))
    resultado = executar_fonte(
        conexao,
        "SELECT t.name, c.name FROM intec.sys.tables AS t "
        "JOIN intec.sys.schemas AS s ON s.schema_id = t.schema_id "
        "JOIN intec.sys.columns AS c ON c.object_id = t.object_id "
        f"WHERE s.name = 'dbo' AND t.name IN ({marcadores})",
        parametros,
    )
    existentes: dict[str, set[str]] = {nome: set() for nome in nomes}
    for tabela, coluna in resultado:
        existentes[str(tabela)].add(str(coluna))

    divergencias: list[str] = []
    for tabela, colunas_esperadas in esperadas.items():
        ausentes = sorted(colunas_esperadas - existentes.get(tabela, set()))
        if ausentes:
            divergencias.append(f"{tabela}({', '.join(ausentes)})")
    if divergencias:
        raise ErroMigracao(
            f"Colunas ausentes no SQL Server {ambiente}: " + "; ".join(divergencias)
        )


def contar_fonte(conexao: Connection, tabela: str, filtro: str | None = None) -> int:
    clausula = f" WHERE {filtro}" if filtro else ""
    comando = f"SELECT COUNT_BIG(*) FROM intec.dbo.[{tabela}] AS src{clausula}"
    return int(executar_fonte(conexao, comando).scalar_one())


def obter_maior_id(conexao: Connection, tabela: str, coluna: str) -> int | None:
    comando = f"SELECT MAX([{coluna}]) FROM intec.dbo.[{tabela}]"
    valor = executar_fonte(conexao, comando).scalar_one()
    return int(valor) if valor is not None else None


def validar_orfaos_prd(conexao: Connection) -> None:
    consultas = {
        "tb_sistema.id_permissao_base": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_Sistema c
            LEFT JOIN intec.dbo.Tb_Permissao p ON p.Id_Permissao = c.Id_Permissao_Base
            WHERE c.Id_Permissao_Base IS NOT NULL AND p.Id_Permissao IS NULL
        """,
        "tb_permissao.id_sistema": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_Permissao c
            LEFT JOIN intec.dbo.Tb_Sistema p ON p.Id_Sistema = c.Id_Sistema
            WHERE p.Id_Sistema IS NULL
        """,
        "tb_permissaogrupo.id_permissao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_PermissaoGrupo c
            LEFT JOIN intec.dbo.Tb_Permissao p ON p.Id_Permissao = c.Id_Permissao
            WHERE p.Id_Permissao IS NULL
        """,
        "tb_permissaousuario.id_permissao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_PermissaoUsuario c
            LEFT JOIN intec.dbo.Tb_Permissao p ON p.Id_Permissao = c.Id_Permissao
            WHERE p.Id_Permissao IS NULL
        """,
        "tb_logacesso.id_sistema": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_LogAcesso c
            LEFT JOIN intec.dbo.Tb_Sistema p ON p.Id_Sistema = c.Id_Sistema
            WHERE c.Id_Sistema IS NOT NULL AND p.Id_Sistema IS NULL
        """,
        "tb_logdetalhe.id_sistema": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_LogDetalhe c
            LEFT JOIN intec.dbo.Tb_Sistema p ON p.Id_Sistema = c.Id_Sistema
            WHERE p.Id_Sistema IS NULL
        """,
        "tb_logdetalhe.id_logacesso": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_LogDetalhe c
            LEFT JOIN intec.dbo.Tb_LogAcesso p ON p.Id_Log = c.Id_LogAcesso
            WHERE c.Id_LogAcesso IS NOT NULL AND p.Id_Log IS NULL
        """,
        "tb_notificacao.id_sistema": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_Notificacao c
            LEFT JOIN intec.dbo.Tb_Sistema p ON p.Id_Sistema = c.Id_Sistema
            WHERE c.Id_Sistema IS NOT NULL AND p.Id_Sistema IS NULL
        """,
        "tb_notificacao_leitura.id_notificacao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_Notificacao_Leitura c
            LEFT JOIN intec.dbo.Tb_Notificacao p ON p.Id_Notificacao = c.Id_Notificacao
            WHERE p.Id_Notificacao IS NULL
        """,
    }
    inconsistencias = {
        nome: int(executar_fonte(conexao, comando).scalar_one())
        for nome, comando in consultas.items()
    }
    inconsistencias = {nome: qtd for nome, qtd in inconsistencias.items() if qtd}
    if inconsistencias:
        detalhe = ", ".join(f"{nome}={qtd}" for nome, qtd in inconsistencias.items())
        raise ErroMigracao(f"Vinculos orfaos encontrados em PRD: {detalhe}")

    severidades_invalidas = int(
        executar_fonte(
            conexao,
            "SELECT COUNT_BIG(*) FROM intec.dbo.Tb_LogDetalhe "
            "WHERE Severidade NOT IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA')",
        ).scalar_one()
    )
    if severidades_invalidas:
        raise ErroMigracao(
            f"Tb_LogDetalhe possui {severidades_invalidas} severidades invalidas para o destino."
        )


def validar_orfaos_hml(conexao: Connection) -> None:
    consultas = {
        "tb_publicacao.id_sistema": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_Publicacao c
            LEFT JOIN intec.dbo.Tb_Sistema p ON p.Id_Sistema = c.Id_Sistema
            WHERE p.Id_Sistema IS NULL
        """,
        "tb_publicacaogrupo.id_publicacao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_PublicacaoGrupo c
            LEFT JOIN intec.dbo.Tb_Publicacao p ON p.Id_Publicacao = c.Id_Publicacao
            WHERE p.Id_Publicacao IS NULL
        """,
        "tb_publicacaoleitura.id_publicacao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_PublicacaoLeitura c
            LEFT JOIN intec.dbo.Tb_Publicacao p ON p.Id_Publicacao = c.Id_Publicacao
            WHERE p.Id_Publicacao IS NULL
        """,
        "tb_publicacaonotificacao.id_publicacao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_PublicacaoNotificacao c
            LEFT JOIN intec.dbo.Tb_Publicacao p ON p.Id_Publicacao = c.Id_Publicacao
            WHERE p.Id_Publicacao IS NULL
        """,
        "tb_publicacaonotificacao.id_notificacao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_PublicacaoNotificacao c
            LEFT JOIN intec.dbo.Tb_Notificacao p ON p.Id_Notificacao = c.Id_Notificacao
            WHERE p.Id_Notificacao IS NULL
        """,
        "tb_notaatualizacaoitem.id_publicacao": """
            SELECT COUNT_BIG(*) FROM intec.dbo.Tb_NotaAtualizacaoItem c
            LEFT JOIN intec.dbo.Tb_Publicacao p ON p.Id_Publicacao = c.Id_Publicacao
            WHERE p.Id_Publicacao IS NULL
        """,
    }
    inconsistencias = {
        nome: int(executar_fonte(conexao, comando).scalar_one())
        for nome, comando in consultas.items()
    }
    inconsistencias = {nome: qtd for nome, qtd in inconsistencias.items() if qtd}
    if inconsistencias:
        detalhe = ", ".join(f"{nome}={qtd}" for nome, qtd in inconsistencias.items())
        raise ErroMigracao(f"Vinculos orfaos encontrados em HML: {detalhe}")


def obter_sistemas(conexao: Connection) -> dict[int, str]:
    resultado = executar_fonte(
        conexao,
        "SELECT Id_Sistema, Nome_Sistema FROM intec.dbo.Tb_Sistema ORDER BY Id_Sistema",
    )
    return {int(id_sistema): str(nome) for id_sistema, nome in resultado}


def construir_mapa_sistemas(
    sistemas_prd: dict[int, str],
    sistemas_hml: dict[int, str],
) -> dict[int, int]:
    ids_prd_por_nome = {
        nome.strip().casefold(): id_sistema for id_sistema, nome in sistemas_prd.items()
    }
    mapa: dict[int, int] = {}
    for id_hml, nome_hml in sistemas_hml.items():
        id_prd = ids_prd_por_nome.get(nome_hml.strip().casefold())
        if id_prd is not None:
            mapa[id_hml] = id_prd
    return mapa


def obter_ids_notificacoes(
    conexao: Connection, somente_publicacoes: bool = False
) -> list[int]:
    filtro = ""
    if somente_publicacoes:
        filtro = (
            " WHERE EXISTS (SELECT 1 FROM intec.dbo.Tb_PublicacaoNotificacao pn "
            "WHERE pn.Id_Notificacao = n.Id_Notificacao)"
        )
    resultado = executar_fonte(
        conexao,
        "SELECT n.Id_Notificacao FROM intec.dbo.Tb_Notificacao n"
        f"{filtro} ORDER BY n.Id_Notificacao",
    )
    return [int(valor) for valor in resultado.scalars()]


def construir_mapa_ids_notificacoes(
    ids_prd: Iterable[int],
    ids_hml: Iterable[int],
) -> dict[int, int]:
    usados = set(ids_prd)
    ids_hml_ordenados = sorted(set(ids_hml))
    proximo = max(usados | set(ids_hml_ordenados) | {0}) + 1
    mapa: dict[int, int] = {}
    for id_hml in ids_hml_ordenados:
        if id_hml not in usados:
            novo_id = id_hml
        else:
            while proximo in usados:
                proximo += 1
            novo_id = proximo
            proximo += 1
        mapa[id_hml] = novo_id
        usados.add(novo_id)
    return mapa


def validar_sistemas_referenciados_hml(
    hml: Connection,
    mapa_sistemas: dict[int, int],
) -> None:
    resultado = executar_fonte(
        hml,
        """
        SELECT DISTINCT Id_Sistema
        FROM (
            SELECT Id_Sistema FROM intec.dbo.Tb_Publicacao
            UNION ALL
            SELECT n.Id_Sistema
            FROM intec.dbo.Tb_Notificacao n
            WHERE EXISTS (
                SELECT 1 FROM intec.dbo.Tb_PublicacaoNotificacao pn
                WHERE pn.Id_Notificacao = n.Id_Notificacao
            )
        ) referencias
        WHERE Id_Sistema IS NOT NULL
        """,
    )
    ausentes = sorted(
        int(id_sistema)
        for id_sistema in resultado.scalars()
        if int(id_sistema) not in mapa_sistemas
    )
    if ausentes:
        raise ErroMigracao(
            "Sistemas usados por HML nao existem por nome em PRD: "
            + ", ".join(map(str, ausentes))
        )


def ddl_tabelas(schema: str) -> tuple[str, ...]:
    s = citar_identificador(schema)
    agora = "(CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')"
    return (
        f"""CREATE TABLE {s}.tb_sistema (
            id_sistema integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            nome_sistema varchar(100) NOT NULL,
            descricao_sistema varchar(255),
            ativo boolean DEFAULT TRUE,
            em_manutencao boolean NOT NULL DEFAULT FALSE,
            icone varchar(255),
            link varchar(255),
            id_permissao_base integer,
            CONSTRAINT uq_core_sistema_nome UNIQUE (nome_sistema)
        )""",
        f"""CREATE TABLE {s}.tb_permissao (
            id_permissao integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            chave_permissao varchar(100) NOT NULL,
            descricao_permissao varchar(255),
            categoria_permissao varchar(50),
            id_sistema integer NOT NULL,
            CONSTRAINT uq_core_permissao_chave_sistema UNIQUE (chave_permissao, id_sistema)
        )""",
        f"""CREATE TABLE {s}.tb_permissaogrupo (
            id_vinculo integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            codigo_usuariogrupo integer NOT NULL,
            id_permissao integer NOT NULL,
            CONSTRAINT uq_core_permissaogrupo UNIQUE (codigo_usuariogrupo, id_permissao)
        )""",
        f"""CREATE TABLE {s}.tb_permissaousuario (
            id_vinculo integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            codigo_usuario integer NOT NULL,
            id_permissao integer NOT NULL,
            conceder boolean DEFAULT TRUE,
            CONSTRAINT uq_core_permissaousuario UNIQUE (codigo_usuario, id_permissao)
        )""",
        f"""CREATE TABLE {s}.tb_logacesso (
            id_log integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            id_usuario integer,
            nome_usuario varchar(150),
            rota_acessada varchar(200),
            metodo_http varchar(10),
            ip_origem varchar(50),
            permissao_exigida varchar(100),
            acesso_permitido boolean,
            data_hora timestamp(3) without time zone DEFAULT {agora},
            id_sistema integer,
            parametros_requisicao text,
            resposta_acao text
        )""",
        f"""CREATE TABLE {s}.tb_logdetalhe (
            id_logdetalhe bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            id_sistema integer NOT NULL,
            id_logacesso integer,
            id_usuario integer,
            nome_usuario varchar(255),
            acao varchar(50),
            recurso varchar(100),
            id_recurso varchar(100),
            descricao varchar(500) NOT NULL,
            dados_anteriores_json text,
            dados_novos_json text,
            ip_origem varchar(50),
            user_agent varchar(500),
            data_hora timestamp(3) without time zone NOT NULL DEFAULT {agora},
            severidade varchar(20) NOT NULL DEFAULT 'BAIXA',
            traceback text,
            CONSTRAINT ck_core_logdetalhe_severidade
                CHECK (severidade IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA'))
        )""",
        f"""CREATE TABLE {s}.tb_notificacao (
            id_notificacao bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            id_sistema integer,
            id_usuario_destino integer,
            tipo varchar(20) NOT NULL DEFAULT 'INFO',
            categoria varchar(50) NOT NULL DEFAULT 'GERAL',
            titulo varchar(200) NOT NULL,
            mensagem text NOT NULL,
            icone varchar(100),
            lida boolean NOT NULL DEFAULT FALSE,
            data_criacao timestamp(3) without time zone NOT NULL DEFAULT {agora},
            data_leitura timestamp(3) without time zone,
            criado_por varchar(150) NOT NULL DEFAULT 'SISTEMA',
            metadados_json text,
            expira_em timestamp(3) without time zone,
            id_grupo_destino integer,
            exibir_a_partir_de timestamp(3) without time zone,
            CONSTRAINT ck_core_notificacao_tipo
                CHECK (tipo IN ('SISTEMA', 'ALERTA', 'INFO', 'SUCESSO', 'ERRO')),
            CONSTRAINT ck_core_notificacao_categoria
                CHECK (categoria IN (
                    'ETL', 'SEGURANCA', 'BANCO', 'SERVICO', 'GERAL', 'USUARIO',
                    'CONFIGURACAO', 'INTEGRACAO', 'COMUNICADO', 'ATUALIZACAO'
                ))
        )""",
        f"""CREATE TABLE {s}.tb_notificacao_leitura (
            id_notificacao bigint NOT NULL,
            id_usuario integer NOT NULL,
            data_leitura timestamp(3) without time zone NOT NULL DEFAULT {agora},
            CONSTRAINT pk_core_notificacao_leitura PRIMARY KEY (id_notificacao, id_usuario)
        )""",
        f"""CREATE TABLE {s}.tb_publicacao (
            id_publicacao bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            id_sistema integer NOT NULL DEFAULT 0,
            tipo_publicacao varchar(20) NOT NULL,
            status_publicacao varchar(20) NOT NULL DEFAULT 'RASCUNHO',
            tipo_audiencia varchar(10) NOT NULL DEFAULT 'GERAL',
            titulo varchar(200) NOT NULL,
            resumo varchar(500),
            conteudo text NOT NULL,
            prioridade varchar(20) NOT NULL DEFAULT 'NORMAL',
            versao varchar(50),
            notificar boolean NOT NULL DEFAULT TRUE,
            fixado boolean NOT NULL DEFAULT FALSE,
            exibir_a_partir_de timestamp(3) without time zone,
            expira_em timestamp(3) without time zone,
            data_publicacao timestamp(3) without time zone,
            data_criacao timestamp(3) without time zone NOT NULL DEFAULT {agora},
            data_atualizacao timestamp(3) without time zone NOT NULL DEFAULT {agora},
            criado_por_id integer,
            criado_por varchar(150) NOT NULL,
            atualizado_por_id integer,
            atualizado_por varchar(150),
            fonte varchar(20) NOT NULL DEFAULT 'INTERNO',
            id_externo varchar(255),
            thread_externo varchar(255),
            remetente_externo varchar(255),
            url_externa varchar(500),
            metadados_json text,
            CONSTRAINT ck_core_publicacao_tipo
                CHECK (tipo_publicacao IN ('COMUNICADO', 'ATUALIZACAO')),
            CONSTRAINT ck_core_publicacao_status
                CHECK (status_publicacao IN ('RASCUNHO', 'AGENDADO', 'PUBLICADO', 'ARQUIVADO')),
            CONSTRAINT ck_core_publicacao_audiencia
                CHECK (tipo_audiencia IN ('GERAL', 'GRUPOS')),
            CONSTRAINT ck_core_publicacao_prioridade
                CHECK (prioridade IN ('BAIXA', 'NORMAL', 'ALTA', 'CRITICA')),
            CONSTRAINT ck_core_publicacao_fonte
                CHECK (fonte IN ('INTERNO', 'GMAIL', 'API')),
            CONSTRAINT ck_core_publicacao_versao
                CHECK (tipo_publicacao <> 'ATUALIZACAO' OR NULLIF(BTRIM(versao), '') IS NOT NULL),
            CONSTRAINT ck_core_publicacao_vigencia
                CHECK (expira_em IS NULL OR exibir_a_partir_de IS NULL OR expira_em > exibir_a_partir_de),
            CONSTRAINT ck_core_publicacao_metadados_json
                CHECK (metadados_json IS NULL OR metadados_json::jsonb IS NOT NULL)
        )""",
        f"""CREATE TABLE {s}.tb_publicacaogrupo (
            id_publicacao bigint NOT NULL,
            id_grupo integer NOT NULL,
            CONSTRAINT pk_core_publicacaogrupo PRIMARY KEY (id_publicacao, id_grupo)
        )""",
        f"""CREATE TABLE {s}.tb_publicacaoleitura (
            id_publicacao bigint NOT NULL,
            id_usuario integer NOT NULL,
            data_leitura timestamp(3) without time zone NOT NULL DEFAULT {agora},
            CONSTRAINT pk_core_publicacaoleitura PRIMARY KEY (id_publicacao, id_usuario)
        )""",
        f"""CREATE TABLE {s}.tb_publicacaonotificacao (
            id_vinculo bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            id_publicacao bigint NOT NULL,
            id_notificacao bigint NOT NULL,
            data_criacao timestamp(3) without time zone NOT NULL DEFAULT {agora},
            CONSTRAINT uq_core_publicacaonotificacao UNIQUE (id_publicacao, id_notificacao)
        )""",
        f"""CREATE TABLE {s}.tb_notaatualizacaoitem (
            id_item bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            id_publicacao bigint NOT NULL,
            tipo_item varchar(20) NOT NULL DEFAULT 'MELHORIA',
            titulo varchar(200) NOT NULL,
            descricao text,
            ordem integer NOT NULL DEFAULT 0,
            CONSTRAINT ck_core_nota_item_tipo
                CHECK (tipo_item IN ('NOVO', 'MELHORIA', 'CORRECAO', 'SEGURANCA', 'TECNICO'))
        )""",
    )


def ddl_chaves_estrangeiras(schema: str) -> tuple[str, ...]:
    s = citar_identificador(schema)
    return (
        f"""ALTER TABLE {s}.tb_sistema ADD CONSTRAINT fk_core_sistema_permissao_base
            FOREIGN KEY (id_permissao_base) REFERENCES {s}.tb_permissao (id_permissao)
            ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED""",
        f"""ALTER TABLE {s}.tb_permissao ADD CONSTRAINT fk_core_permissao_sistema
            FOREIGN KEY (id_sistema) REFERENCES {s}.tb_sistema (id_sistema)
            DEFERRABLE INITIALLY DEFERRED""",
        f"""ALTER TABLE {s}.tb_permissaogrupo ADD CONSTRAINT fk_core_permissaogrupo_permissao
            FOREIGN KEY (id_permissao) REFERENCES {s}.tb_permissao (id_permissao)""",
        f"""ALTER TABLE {s}.tb_permissaousuario ADD CONSTRAINT fk_core_permissaousuario_permissao
            FOREIGN KEY (id_permissao) REFERENCES {s}.tb_permissao (id_permissao)""",
        f"""ALTER TABLE {s}.tb_logacesso ADD CONSTRAINT fk_core_logacesso_sistema
            FOREIGN KEY (id_sistema) REFERENCES {s}.tb_sistema (id_sistema)""",
        f"""ALTER TABLE {s}.tb_logdetalhe ADD CONSTRAINT fk_core_logdetalhe_sistema
            FOREIGN KEY (id_sistema) REFERENCES {s}.tb_sistema (id_sistema)""",
        f"""ALTER TABLE {s}.tb_logdetalhe ADD CONSTRAINT fk_core_logdetalhe_logacesso
            FOREIGN KEY (id_logacesso) REFERENCES {s}.tb_logacesso (id_log) ON DELETE SET NULL""",
        f"""ALTER TABLE {s}.tb_notificacao ADD CONSTRAINT fk_core_notificacao_sistema
            FOREIGN KEY (id_sistema) REFERENCES {s}.tb_sistema (id_sistema)""",
        f"""ALTER TABLE {s}.tb_notificacao_leitura ADD CONSTRAINT fk_core_notificacao_leitura_notificacao
            FOREIGN KEY (id_notificacao) REFERENCES {s}.tb_notificacao (id_notificacao) ON DELETE CASCADE""",
        f"""ALTER TABLE {s}.tb_publicacao ADD CONSTRAINT fk_core_publicacao_sistema
            FOREIGN KEY (id_sistema) REFERENCES {s}.tb_sistema (id_sistema)""",
        f"""ALTER TABLE {s}.tb_publicacaogrupo ADD CONSTRAINT fk_core_publicacaogrupo_publicacao
            FOREIGN KEY (id_publicacao) REFERENCES {s}.tb_publicacao (id_publicacao) ON DELETE CASCADE""",
        f"""ALTER TABLE {s}.tb_publicacaoleitura ADD CONSTRAINT fk_core_publicacaoleitura_publicacao
            FOREIGN KEY (id_publicacao) REFERENCES {s}.tb_publicacao (id_publicacao) ON DELETE CASCADE""",
        f"""ALTER TABLE {s}.tb_publicacaonotificacao ADD CONSTRAINT fk_core_publicacaonotificacao_publicacao
            FOREIGN KEY (id_publicacao) REFERENCES {s}.tb_publicacao (id_publicacao) ON DELETE CASCADE""",
        f"""ALTER TABLE {s}.tb_publicacaonotificacao ADD CONSTRAINT fk_core_publicacaonotificacao_notificacao
            FOREIGN KEY (id_notificacao) REFERENCES {s}.tb_notificacao (id_notificacao) ON DELETE CASCADE""",
        f"""ALTER TABLE {s}.tb_notaatualizacaoitem ADD CONSTRAINT fk_core_nota_item_publicacao
            FOREIGN KEY (id_publicacao) REFERENCES {s}.tb_publicacao (id_publicacao) ON DELETE CASCADE""",
    )


def ddl_indices(schema: str) -> tuple[str, ...]:
    s = citar_identificador(schema)
    return (
        f"CREATE INDEX ix_core_permissao_sistema ON {s}.tb_permissao (id_sistema)",
        f"CREATE INDEX ix_core_permissaogrupo_permissao ON {s}.tb_permissaogrupo (id_permissao)",
        f"CREATE INDEX ix_core_permissaousuario_permissao ON {s}.tb_permissaousuario (id_permissao)",
        f"CREATE INDEX ix_core_permissaousuario_usuario ON {s}.tb_permissaousuario (codigo_usuario)",
        f"CREATE INDEX ix_core_logacesso_data ON {s}.tb_logacesso (data_hora DESC)",
        f"CREATE INDEX ix_core_logacesso_sistema_data ON {s}.tb_logacesso (id_sistema, data_hora DESC)",
        f"CREATE INDEX ix_core_logacesso_usuario_data ON {s}.tb_logacesso (id_usuario, data_hora DESC)",
        f"CREATE INDEX ix_core_logdetalhe_logacesso ON {s}.tb_logdetalhe (id_logacesso)",
        f"CREATE INDEX ix_core_logdetalhe_sistema_data ON {s}.tb_logdetalhe (id_sistema, data_hora DESC)",
        f"CREATE INDEX ix_core_logdetalhe_usuario_data ON {s}.tb_logdetalhe (id_usuario, data_hora DESC)",
        f"CREATE INDEX ix_core_logdetalhe_recurso ON {s}.tb_logdetalhe (recurso, id_recurso, data_hora DESC)",
        f"CREATE INDEX ix_core_notificacao_expiracao ON {s}.tb_notificacao (expira_em) WHERE expira_em IS NOT NULL",
        f"CREATE INDEX ix_core_notificacao_sistema_data ON {s}.tb_notificacao (id_sistema, data_criacao DESC)",
        f"""CREATE INDEX ix_core_notificacao_usuario_lida_data
            ON {s}.tb_notificacao (id_usuario_destino, lida, data_criacao DESC)
            INCLUDE (tipo, categoria, titulo, icone)""",
        f"CREATE INDEX ix_core_notificacao_grupo_sistema_data ON {s}.tb_notificacao (id_grupo_destino, id_sistema, data_criacao DESC)",
        f"CREATE INDEX ix_core_notificacao_leitura_usuario ON {s}.tb_notificacao_leitura (id_usuario, data_leitura DESC)",
        f"""CREATE INDEX ix_core_publicacao_escopo_tipo_status_data
            ON {s}.tb_publicacao (id_sistema, tipo_publicacao, status_publicacao, data_publicacao DESC)
            INCLUDE (titulo, resumo, prioridade, tipo_audiencia, fixado, exibir_a_partir_de, expira_em)""",
        f"""CREATE UNIQUE INDEX ux_core_publicacao_fonte_id_externo
            ON {s}.tb_publicacao (fonte, id_externo) WHERE id_externo IS NOT NULL""",
        f"CREATE INDEX ix_core_publicacaogrupo_grupo_publicacao ON {s}.tb_publicacaogrupo (id_grupo, id_publicacao)",
        f"CREATE INDEX ix_core_publicacaoleitura_usuario ON {s}.tb_publicacaoleitura (id_usuario, data_leitura DESC)",
        f"CREATE INDEX ix_core_publicacaonotificacao_notificacao ON {s}.tb_publicacaonotificacao (id_notificacao)",
        f"CREATE INDEX ix_core_nota_item_publicacao_ordem ON {s}.tb_notaatualizacaoitem (id_publicacao, ordem, id_item)",
    )


def ddl_comentarios(schema: str) -> tuple[str, ...]:
    s = citar_identificador(schema)
    return (
        f"COMMENT ON SCHEMA {s} IS 'Dados sistemicos compartilhados pelas aplicacoes web Luft'",
        f"COMMENT ON COLUMN {s}.tb_permissaogrupo.codigo_usuariogrupo IS 'Referencia logica a Luftinforma.dbo.usuariogrupo; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_permissaousuario.codigo_usuario IS 'Referencia logica a Luftinforma.dbo.usuario; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_notificacao.id_usuario_destino IS 'Referencia logica a Luftinforma.dbo.usuario; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_notificacao.id_grupo_destino IS 'Referencia logica a Luftinforma.dbo.usuariogrupo; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_notificacao_leitura.id_usuario IS 'Referencia logica a Luftinforma.dbo.usuario; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_publicacaogrupo.id_grupo IS 'Referencia logica a Luftinforma.dbo.usuariogrupo; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_publicacaoleitura.id_usuario IS 'Referencia logica a Luftinforma.dbo.usuario; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_publicacao.criado_por_id IS 'Referencia logica a Luftinforma.dbo.usuario; sem FK entre bancos'",
        f"COMMENT ON COLUMN {s}.tb_publicacao.atualizado_por_id IS 'Referencia logica a Luftinforma.dbo.usuario; sem FK entre bancos'",
    )


def tabelas_gerenciadas() -> tuple[str, ...]:
    return tuple(tabela.destino for tabela in (*TABELAS_PRD, *TABELAS_HML))


def criar_backup_e_remover_existentes(
    conexao: Connection,
    schema: str,
    existentes: set[str],
) -> str:
    gerenciadas_existentes = sorted(existentes.intersection(tabelas_gerenciadas()))
    if not gerenciadas_existentes:
        return ""

    sufixo = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    schema_backup = f"{schema}_backup_{sufixo}"
    citar_identificador(schema_backup)
    conexao.exec_driver_sql(f"CREATE SCHEMA {citar_identificador(schema_backup)}")
    for tabela in gerenciadas_existentes:
        conexao.exec_driver_sql(
            f"CREATE TABLE {nome_qualificado(schema_backup, tabela)} AS "
            f"TABLE {nome_qualificado(schema, tabela)}"
        )

    alvos = ", ".join(
        nome_qualificado(schema, tabela) for tabela in gerenciadas_existentes
    )
    # Todas as tabelas gerenciadas sao removidas na mesma instrucao. Assim as
    # dependencias internas podem cair sem CASCADE, enquanto dependencias
    # externas fazem a operacao falhar de forma segura.
    conexao.exec_driver_sql(f"DROP TABLE {alvos}")
    return schema_backup


def criar_estrutura(conexao: Connection, schema: str) -> None:
    conexao.exec_driver_sql(
        f"CREATE SCHEMA IF NOT EXISTS {citar_identificador(schema)}"
    )
    for comando in ddl_tabelas(schema):
        conexao.exec_driver_sql(comando)


def criar_integridade_e_indices(conexao: Connection, schema: str) -> None:
    for comando in ddl_chaves_estrangeiras(schema):
        conexao.exec_driver_sql(comando)
    for comando in ddl_indices(schema):
        conexao.exec_driver_sql(comando)
    for comando in ddl_comentarios(schema):
        conexao.exec_driver_sql(comando)


def sincronizar_identidades(conexao: Connection, schema: str) -> None:
    for tabela in (*TABELAS_PRD, *TABELAS_HML):
        if not tabela.coluna_identidade:
            continue
        relacao = f"{schema}.{tabela.destino}"
        coluna = citar_identificador(tabela.coluna_identidade)
        qualificada = nome_qualificado(schema, tabela.destino)
        conexao.execute(
            text(
                "SELECT setval(pg_get_serial_sequence(:relacao, :coluna), "
                f"GREATEST(COALESCE(MAX({coluna}), 0), 1), COUNT(*) > 0) "
                f"FROM {qualificada}"
            ),
            {"relacao": relacao, "coluna": tabela.coluna_identidade},
        )


def contar_destino(conexao: Connection, schema: str, tabela: str) -> int:
    return int(
        conexao.execute(
            text(f"SELECT COUNT(*) FROM {nome_qualificado(schema, tabela)}")
        ).scalar_one()
    )


def validar_contagens_destino(
    conexao: Connection,
    schema: str,
    esperadas: dict[str, int],
) -> None:
    divergencias: list[str] = []
    for tabela, esperado in esperadas.items():
        encontrado = contar_destino(conexao, schema, tabela)
        if encontrado != esperado:
            divergencias.append(
                f"{tabela}: esperado={esperado}, encontrado={encontrado}"
            )
    if divergencias:
        raise ErroMigracao("Divergencia de contagem: " + "; ".join(divergencias))


def preparar_diagnostico(
    prd: Connection,
    hml: Connection,
) -> tuple[dict[str, int], dict[int, int], dict[int, int]]:
    validar_tabelas_fonte(prd, (t.origem for t in TABELAS_PRD), "PRD")
    validar_tabelas_fonte(
        hml,
        [*(t.origem for t in TABELAS_HML), "Tb_Notificacao", "Tb_Sistema"],
        "HML",
    )
    validar_colunas_fonte(prd, TABELAS_PRD, "PRD")
    validar_colunas_fonte(hml, TABELAS_HML, "HML")
    validar_colunas_fonte(hml, (ESPECIFICACAO_NOTIFICACAO,), "HML")
    validar_orfaos_prd(prd)
    validar_orfaos_hml(hml)

    sistemas_prd = obter_sistemas(prd)
    sistemas_hml = obter_sistemas(hml)
    mapa_sistemas = construir_mapa_sistemas(sistemas_prd, sistemas_hml)
    validar_sistemas_referenciados_hml(hml, mapa_sistemas)

    ids_notificacao_prd = obter_ids_notificacoes(prd)
    ids_notificacao_hml = obter_ids_notificacoes(hml, somente_publicacoes=True)
    mapa_notificacoes = construir_mapa_ids_notificacoes(
        ids_notificacao_prd,
        ids_notificacao_hml,
    )

    contagens: dict[str, int] = {}
    for tabela in TABELAS_PRD:
        contagens[tabela.destino] = contar_fonte(prd, tabela.origem)
    for tabela in TABELAS_HML:
        contagens[tabela.destino] = contar_fonte(hml, tabela.origem)
    contagens["notificacoes_hml_dependentes"] = len(ids_notificacao_hml)
    return contagens, mapa_sistemas, mapa_notificacoes


def exibir_diagnostico(
    contagens: dict[str, int],
    mapa_notificacoes: dict[int, int],
    existentes: set[str],
    schema: str,
) -> None:
    print("\nPlano de carga:")
    for tabela in TABELAS_PRD:
        print(f"  PRD -> {schema}.{tabela.destino}: {contagens[tabela.destino]}")
    print(
        f"  HML -> {schema}.tb_notificacao (dependencias de publicacao): "
        f"{contagens['notificacoes_hml_dependentes']}"
    )
    for tabela in TABELAS_HML:
        print(f"  HML -> {schema}.{tabela.destino}: {contagens[tabela.destino]}")

    remapeados = {
        antigo: novo for antigo, novo in mapa_notificacoes.items() if antigo != novo
    }
    if remapeados:
        detalhe = ", ".join(f"{antigo}->{novo}" for antigo, novo in remapeados.items())
        print(f"  IDs de notificacao HML remapeados por colisao: {detalhe}")

    gerenciadas_existentes = sorted(existentes.intersection(tabelas_gerenciadas()))
    if gerenciadas_existentes:
        print("\nTabelas de destino ja existentes:")
        for tabela in gerenciadas_existentes:
            print(f"  {schema}.{tabela}")
    else:
        print("\nDestino livre: nenhuma tabela gerenciada existe no schema informado.")


def transformar_sistema_hml(
    linha: dict[str, Any],
    mapa_sistemas: dict[int, int],
) -> dict[str, Any]:
    id_sistema = linha.get("id_sistema")
    if id_sistema is not None:
        linha["id_sistema"] = mapa_sistemas[int(id_sistema)]
    return linha


def executar_migracao(
    prd: Connection,
    hml: Connection,
    destino: Connection,
    schema: str,
    tamanho_lote: int,
    mapa_sistemas: dict[int, int],
    mapa_notificacoes: dict[int, int],
) -> dict[str, int]:
    contagens_carregadas: dict[str, int] = {}

    # Logs continuam sendo gravados pelas aplicacoes durante a migracao. Estes
    # limites produzem um recorte consistente sem bloquear ou alterar PRD.
    limite_logacesso = obter_maior_id(prd, "Tb_LogAcesso", "Id_Log")
    limite_logdetalhe = obter_maior_id(prd, "Tb_LogDetalhe", "Id_LogDetalhe")
    print(
        "\nRecorte imutavel dos logs: "
        f"Id_Log <= {limite_logacesso}, Id_LogDetalhe <= {limite_logdetalhe}"
    )

    print("\nCarregando tabelas de PRD...")
    for tabela in TABELAS_PRD:
        filtro: str | None = None
        if tabela.origem == "Tb_LogAcesso":
            filtro = (
                f"src.[Id_Log] <= {limite_logacesso}"
                if limite_logacesso is not None
                else "1 = 0"
            )
        elif tabela.origem == "Tb_LogDetalhe":
            if limite_logdetalhe is None:
                filtro = "1 = 0"
            elif limite_logacesso is None:
                filtro = (
                    f"src.[Id_LogDetalhe] <= {limite_logdetalhe} "
                    "AND src.[Id_LogAcesso] IS NULL"
                )
            else:
                filtro = (
                    f"src.[Id_LogDetalhe] <= {limite_logdetalhe} "
                    f"AND (src.[Id_LogAcesso] IS NULL OR src.[Id_LogAcesso] <= {limite_logacesso})"
                )
        contagens_carregadas[tabela.destino] = carregar_tabela(
            prd,
            destino,
            schema,
            tabela,
            tamanho_lote,
            filtro=filtro,
        )

    print("\nCarregando notificacoes de HML exigidas pelas publicacoes...")
    filtro_notificacoes = (
        "EXISTS (SELECT 1 FROM intec.dbo.Tb_PublicacaoNotificacao pn "
        "WHERE pn.Id_Notificacao = src.Id_Notificacao)"
    )

    def transformar_notificacao(linha: dict[str, Any]) -> dict[str, Any]:
        id_antigo = int(linha["id_notificacao"])
        linha["id_notificacao"] = mapa_notificacoes[id_antigo]
        return transformar_sistema_hml(linha, mapa_sistemas)

    quantidade_hml_notificacoes = carregar_tabela(
        hml,
        destino,
        schema,
        ESPECIFICACAO_NOTIFICACAO,
        tamanho_lote,
        filtro=filtro_notificacoes,
        transformar=transformar_notificacao,
    )
    contagens_carregadas["tb_notificacao"] += quantidade_hml_notificacoes

    print("\nCarregando tabelas de publicacao de HML...")
    for tabela in TABELAS_HML:
        transformacao: Transformacao | None = None
        if tabela.origem == "Tb_Publicacao":
            transformacao = lambda linha: transformar_sistema_hml(linha, mapa_sistemas)
        elif tabela.origem == "Tb_PublicacaoNotificacao":

            def transformar_vinculo(linha: dict[str, Any]) -> dict[str, Any]:
                linha["id_notificacao"] = mapa_notificacoes[
                    int(linha["id_notificacao"])
                ]
                return linha

            transformacao = transformar_vinculo

        contagens_carregadas[tabela.destino] = carregar_tabela(
            hml,
            destino,
            schema,
            tabela,
            tamanho_lote,
            transformar=transformacao,
        )
    return contagens_carregadas


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migra tabelas sistemicas PRD/HML do SQL Server para o PostgreSQL local.",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Executa a escrita no PostgreSQL. Sem esta opcao, roda somente o diagnostico.",
    )
    parser.add_argument(
        "--confirmar",
        default="",
        help=f"Frase obrigatoria para executar: {CONFIRMACAO_EXECUCAO}",
    )
    parser.add_argument(
        "--substituir",
        action="store_true",
        help="Substitui somente as 13 tabelas gerenciadas que ja existirem no destino.",
    )
    parser.add_argument(
        "--confirmar-substituicao",
        default="",
        help=f"Frase adicional obrigatoria: {CONFIRMACAO_SUBSTITUICAO}",
    )
    parser.add_argument("--schema", default=SCHEMA_DESTINO)
    parser.add_argument("--lote", type=int, default=1000)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--banco-destino-esperado", default=BANCO_DESTINO_ESPERADO)
    return parser


def validar_argumentos(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    if not IDENTIFICADOR_SEGURO.fullmatch(args.schema):
        parser.error(
            "--schema deve conter somente letras minusculas, numeros e underscore."
        )
    if args.lote < 1 or args.lote > 10_000:
        parser.error("--lote deve estar entre 1 e 10000.")
    if args.executar and args.confirmar != CONFIRMACAO_EXECUCAO:
        parser.error(f"Para executar, informe --confirmar {CONFIRMACAO_EXECUCAO}")
    if args.substituir and not args.executar:
        parser.error("--substituir exige --executar.")
    if args.substituir and args.confirmar_substituicao != CONFIRMACAO_SUBSTITUICAO:
        parser.error(
            "Para substituir tabelas, informe "
            f"--confirmar-substituicao {CONFIRMACAO_SUBSTITUICAO}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = criar_parser()
    args = parser.parse_args(argv)
    validar_argumentos(args, parser)

    load_dotenv(args.env_file)
    validar_variaveis_ambiente()

    engines: list[Engine] = []
    try:
        print("Conectando aos bancos pelo Vault (nenhuma credencial sera exibida)...")
        engine_prd = criar_engine_vault(
            CAMINHO_SQLSERVER_PRD,
            "mssql",
            os.getenv("DB_DRIVER") or "ODBC Driver 17 for SQL Server",
            somente_leitura=True,
        )
        engines.append(engine_prd)
        engine_hml = criar_engine_vault(
            CAMINHO_SQLSERVER_HML,
            "mssql",
            os.getenv("DB_DRIVER") or "ODBC Driver 17 for SQL Server",
            somente_leitura=True,
        )
        engines.append(engine_hml)
        engine_destino = criar_engine_vault(
            CAMINHO_POSTGRESQL,
            "postgresql",
            "psycopg",
        )
        engines.append(engine_destino)

        if engine_prd.dialect.name != "mssql" or engine_hml.dialect.name != "mssql":
            raise ErroMigracao("As duas origens precisam usar o dialeto mssql.")
        if engine_destino.dialect.name != "postgresql":
            raise ErroMigracao("O destino precisa usar o dialeto postgresql.")

        with (
            engine_prd.connect() as prd,
            engine_hml.connect() as hml,
            engine_destino.connect() as alvo,
        ):
            servidor_prd, banco_prd = obter_identidade_fonte(prd)
            servidor_hml, banco_hml = obter_identidade_fonte(hml)
            host_destino, banco_destino, usuario_destino = obter_identidade_destino(
                alvo
            )

            print(
                f"Origem PRD: servidor={servidor_prd}, banco_consultado=intec (conexao={banco_prd})"
            )
            print(
                f"Origem HML: servidor={servidor_hml}, banco_consultado=intec (conexao={banco_hml})"
            )
            print(
                f"Destino: host={host_destino}, banco={banco_destino}, "
                f"usuario={usuario_destino}, schema={args.schema}"
            )
            print(
                "Protecao SQL Server: somente SELECT/CTE habilitado nas duas engines."
            )

            if banco_destino != args.banco_destino_esperado:
                raise ErroMigracao(
                    f"Banco destino inesperado: {banco_destino!r}; "
                    f"esperado={args.banco_destino_esperado!r}."
                )

            contagens, mapa_sistemas, mapa_notificacoes = preparar_diagnostico(prd, hml)
            existentes = obter_tabelas_existentes(alvo, args.schema)
            exibir_diagnostico(contagens, mapa_notificacoes, existentes, args.schema)

        if not args.executar:
            print(
                "\nDIAGNOSTICO CONCLUIDO: nenhuma alteracao foi feita em nenhum banco."
            )
            print(
                f"Para executar: python scripts/migrar_core_postgresql.py --executar "
                f"--confirmar {CONFIRMACAO_EXECUCAO}"
            )
            return 0

        gerenciadas_existentes = existentes.intersection(tabelas_gerenciadas())
        if gerenciadas_existentes and not args.substituir:
            raise ErroMigracao(
                "O destino ja possui tabelas gerenciadas. A operacao foi recusada. "
                "Revise o diagnostico ou use --substituir com a confirmacao adicional."
            )

        # Reabre as origens para que o diagnostico e a carga nao compartilhem
        # cursores antigos. As engines de origem continuam protegidas pelo evento.
        with (
            engine_prd.connect() as prd,
            engine_hml.connect() as hml,
            engine_destino.begin() as alvo,
        ):
            alvo.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:chave))"),
                {"chave": f"migracao:{banco_destino}:{args.schema}:core"},
            )
            existentes_agora = obter_tabelas_existentes(alvo, args.schema)
            gerenciadas_agora = existentes_agora.intersection(tabelas_gerenciadas())
            if gerenciadas_agora and not args.substituir:
                raise ErroMigracao(
                    "Tabelas surgiram no destino depois do diagnostico; abortando."
                )

            schema_backup = ""
            if gerenciadas_agora:
                schema_backup = criar_backup_e_remover_existentes(
                    alvo,
                    args.schema,
                    existentes_agora,
                )
                print(f"Backup transacional criado no schema: {schema_backup}")

            criar_estrutura(alvo, args.schema)
            carregadas = executar_migracao(
                prd,
                hml,
                alvo,
                args.schema,
                args.lote,
                mapa_sistemas,
                mapa_notificacoes,
            )
            criar_integridade_e_indices(alvo, args.schema)
            sincronizar_identidades(alvo, args.schema)
            validar_contagens_destino(alvo, args.schema, carregadas)
            alvo.exec_driver_sql("SET CONSTRAINTS ALL IMMEDIATE")
            for tabela in tabelas_gerenciadas():
                alvo.exec_driver_sql(f"ANALYZE {nome_qualificado(args.schema, tabela)}")

        print("\nMIGRACAO CONCLUIDA: transacao confirmada no PostgreSQL.")
        print("SQL Server PRD/HML recebeu somente consultas SELECT.")
        return 0
    # Fronteira do utilitario: qualquer falha precisa produzir rollback e uma
    # mensagem curta, sem despejar URIs ou credenciais do Vault no terminal.
    except Exception as erro:  # noqa: BLE001
        print(f"\nMIGRACAO CANCELADA: {erro}", file=sys.stderr)
        if args.executar:
            print(
                "A transacao do PostgreSQL foi revertida; nenhuma carga parcial foi confirmada.",
                file=sys.stderr,
            )
        return 1
    finally:
        for engine in reversed(engines):
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
