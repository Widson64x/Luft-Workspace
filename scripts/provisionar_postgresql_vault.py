"""Provisiona credenciais PostgreSQL no Vault sem sobrescrever segredos.

O utilitario possui tres operacoes deliberadamente separadas:

* ``auditar``: somente leitura no PostgreSQL e no Vault;
* ``provisionar``: cria segredos novos com CAS 0 e define senhas nas roles;
* ``aplicar-senhas-do-vault``: recupera uma execucao interrompida depois da
  escrita no Vault e antes do commit no PostgreSQL.

Tokens e senhas sao solicitados de forma interativa e nunca sao impressos.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys
from dataclasses import dataclass
from typing import Any

import hvac
import psycopg
from hvac import exceptions as vault_exceptions
from psycopg import sql

CAMINHO_BASE = "luft/desenvolvimento/bancos/postgresql"
CONEXAO = "luft-web"
CONFIRMACAO = "PROVISIONAR-LUFT-WEB"


@dataclass(frozen=True, slots=True)
class Aplicacao:
    sistema_id: int
    identificador: str
    esquema: str
    usuario: str

    @property
    def caminho_vault(self) -> str:
        return f"{CAMINHO_BASE}/sistemas/{self.sistema_id}"


APLICACOES = (
    Aplicacao(1, "luft-connectair", "connectair", "luft_connectair_app"),
    Aplicacao(2, "luft-control", "control", "luft_control_app"),
    Aplicacao(5, "luft-docs", "docs", "luft_docs_app"),
    Aplicacao(3, "luft-integrador", "integrador", "luft_integrador_app"),
    Aplicacao(0, "luft-workspace", "workspace", "luft_workspace_app"),
)


def criar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita ou provisiona PostgreSQL + Vault para o luft_web."
    )
    parser.add_argument(
        "acao",
        nargs="?",
        choices=("auditar", "provisionar", "aplicar-senhas-do-vault"),
        default="auditar",
    )
    parser.add_argument("--vault-url", default="http://172.16.200.80:8200")
    parser.add_argument("--vault-mount", default="secret")
    parser.add_argument("--postgres-host", default="172.19.85.111")
    parser.add_argument("--postgres-porta", type=int, default=5432)
    parser.add_argument("--postgres-banco", default="luft_web")
    parser.add_argument("--postgres-admin", default="admin")
    return parser.parse_args()


def solicitar_segredo(rotulo: str) -> str:
    valor = getpass.getpass(f"{rotulo}: ")
    if not valor:
        raise RuntimeError(f"{rotulo} nao pode ficar vazio.")
    return valor


def criar_cliente_vault(url: str, token: str, mount: str) -> hvac.Client:
    cliente = hvac.Client(url=url, token=token)
    if not cliente.is_authenticated():
        raise RuntimeError("O token informado nao foi autenticado pelo Vault.")

    montagens = cliente.sys.list_mounted_secrets_engines()["data"]
    configuracao = montagens.get(f"{mount}/")
    if configuracao is None:
        raise RuntimeError(f"O mount {mount!r} nao existe no Vault.")
    if configuracao.get("type") != "kv":
        raise RuntimeError(f"O mount {mount!r} nao e do tipo KV.")
    if configuracao.get("options", {}).get("version") != "2":
        raise RuntimeError(f"O mount {mount!r} nao usa KV v2.")
    return cliente


def segredo_existe(cliente: hvac.Client, mount: str, caminho: str) -> bool:
    try:
        cliente.secrets.kv.v2.read_secret_metadata(
            path=caminho,
            mount_point=mount,
        )
    except vault_exceptions.InvalidPath:
        return False
    return True


def conectar_postgresql(args: argparse.Namespace, senha: str) -> psycopg.Connection:
    return psycopg.connect(
        host=args.postgres_host,
        port=args.postgres_porta,
        dbname=args.postgres_banco,
        user=args.postgres_admin,
        password=senha,
        sslmode="prefer",
        connect_timeout=10,
    )


def auditar_postgresql(conexao: psycopg.Connection) -> None:
    usuarios = tuple(aplicacao.usuario for aplicacao in APLICACOES)
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                rolname,
                rolcanlogin,
                rolpassword IS NOT NULL AS senha_configurada
            FROM pg_catalog.pg_authid
            WHERE rolname = ANY (%s)
            ORDER BY rolname
            """,
            (list(usuarios),),
        )
        encontrados = cursor.fetchall()

        cursor.execute(
            """
            SELECT usename, count(*)
            FROM pg_catalog.pg_stat_activity
            WHERE datname = %s
              AND usename = ANY (%s)
            GROUP BY usename
            ORDER BY usename
            """,
            (conexao.info.dbname, list(usuarios)),
        )
        conexoes_ativas = dict(cursor.fetchall())

    encontrados_por_nome = {linha[0]: linha for linha in encontrados}
    print("PostgreSQL:")
    for aplicacao in APLICACOES:
        linha = encontrados_por_nome.get(aplicacao.usuario)
        if linha is None:
            print(f"  AUSENTE  {aplicacao.usuario}")
            continue
        _, permite_login, possui_senha = linha
        print(
            f"  OK       {aplicacao.usuario}: "
            f"login={permite_login}, senha={possui_senha}, "
            f"conexoes={conexoes_ativas.get(aplicacao.usuario, 0)}"
        )


def auditar_vault(cliente: hvac.Client, mount: str) -> None:
    caminhos = [f"{CAMINHO_BASE}/conexoes/{CONEXAO}"]
    caminhos.extend(aplicacao.caminho_vault for aplicacao in APLICACOES)
    print("Vault (somente metadados):")
    for caminho in caminhos:
        estado = "EXISTE" if segredo_existe(cliente, mount, caminho) else "AUSENTE"
        print(f"  {estado:<7}  {caminho}")


def validar_roles_para_provisionamento(conexao: psycopg.Connection) -> None:
    usuarios = [aplicacao.usuario for aplicacao in APLICACOES]
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT rolname, rolcanlogin, rolpassword IS NOT NULL
            FROM pg_catalog.pg_authid
            WHERE rolname = ANY (%s)
            """,
            (usuarios,),
        )
        roles = {nome: (login, senha) for nome, login, senha in cursor.fetchall()}
        cursor.execute(
            """
            SELECT DISTINCT usename
            FROM pg_catalog.pg_stat_activity
            WHERE datname = %s
              AND usename = ANY (%s)
              AND pid <> pg_backend_pid()
            """,
            (conexao.info.dbname, usuarios),
        )
        ativas = {linha[0] for linha in cursor.fetchall()}

    ausentes = sorted(set(usuarios) - roles.keys())
    sem_login = sorted(nome for nome, estado in roles.items() if not estado[0])
    com_senha = sorted(nome for nome, estado in roles.items() if estado[1])
    if ausentes:
        raise RuntimeError(f"Roles ausentes: {', '.join(ausentes)}")
    if sem_login:
        raise RuntimeError(f"Roles sem LOGIN: {', '.join(sem_login)}")
    if com_senha:
        raise RuntimeError(
            "As seguintes roles ja possuem senha e nao serao rotacionadas: "
            + ", ".join(com_senha)
        )
    if ativas:
        raise RuntimeError(
            "Existem conexoes ativas das roles alvo: " + ", ".join(sorted(ativas))
        )


def validar_caminhos_novos(cliente: hvac.Client, mount: str) -> None:
    caminhos = [f"{CAMINHO_BASE}/conexoes/{CONEXAO}"]
    caminhos.extend(aplicacao.caminho_vault for aplicacao in APLICACOES)
    existentes = [
        caminho for caminho in caminhos if segredo_existe(cliente, mount, caminho)
    ]
    if existentes:
        raise RuntimeError(
            "O provisionamento nao sobrescreve caminhos existentes: "
            + ", ".join(existentes)
        )


def gerar_senhas() -> dict[str, str]:
    return {aplicacao.usuario: secrets.token_urlsafe(32) for aplicacao in APLICACOES}


def criar_segredos(
    cliente: hvac.Client,
    mount: str,
    args: argparse.Namespace,
    senhas: dict[str, str],
) -> None:
    cliente.secrets.kv.v2.create_or_update_secret(
        path=f"{CAMINHO_BASE}/conexoes/{CONEXAO}",
        mount_point=mount,
        cas=0,
        secret={
            "tipo_banco": "postgresql",
            "host": args.postgres_host,
            "porta": str(args.postgres_porta),
            "nome_banco": args.postgres_banco,
            "sslmode": "prefer",
        },
    )
    for aplicacao in APLICACOES:
        cliente.secrets.kv.v2.create_or_update_secret(
            path=aplicacao.caminho_vault,
            mount_point=mount,
            cas=0,
            secret={
                "conexao": CONEXAO,
                "esquema": aplicacao.esquema,
                "identificador": aplicacao.identificador,
                "sistema_id": aplicacao.sistema_id,
                "usuario": aplicacao.usuario,
                "senha": senhas[aplicacao.usuario],
            },
        )


def carregar_senhas(
    cliente: hvac.Client,
    mount: str,
) -> dict[str, str]:
    senhas: dict[str, str] = {}
    for aplicacao in APLICACOES:
        resposta = cliente.secrets.kv.v2.read_secret_version(
            path=aplicacao.caminho_vault,
            mount_point=mount,
            raise_on_deleted_version=True,
        )
        dados: dict[str, Any] = resposta["data"]["data"]
        if dados.get("conexao") != CONEXAO:
            raise RuntimeError(f"Conexao invalida em {aplicacao.caminho_vault}.")
        if dados.get("esquema") != aplicacao.esquema:
            raise RuntimeError(f"Esquema invalido em {aplicacao.caminho_vault}.")
        if dados.get("usuario") != aplicacao.usuario:
            raise RuntimeError(f"Usuario invalido em {aplicacao.caminho_vault}.")
        if dados.get("identificador") != aplicacao.identificador:
            raise RuntimeError(f"Identificador invalido em {aplicacao.caminho_vault}.")
        if int(dados.get("sistema_id", -1)) != aplicacao.sistema_id:
            raise RuntimeError(f"Sistema invalido em {aplicacao.caminho_vault}.")
        senha = dados.get("senha")
        if not isinstance(senha, str) or not senha:
            raise RuntimeError(f"Senha ausente em {aplicacao.caminho_vault}.")
        senhas[aplicacao.usuario] = senha
    return senhas


def aplicar_senhas(
    conexao: psycopg.Connection,
    senhas: dict[str, str],
) -> None:
    with conexao.transaction(), conexao.cursor() as cursor:
        for aplicacao in APLICACOES:
            senha = senhas[aplicacao.usuario]
            verificador = conexao.pgconn.encrypt_password(
                senha.encode(),
                aplicacao.usuario.encode(),
                b"scram-sha-256",
            ).decode()
            cursor.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(aplicacao.usuario),
                    sql.Literal(verificador),
                )
            )


def confirmar() -> None:
    print("Esta operacao escrevera novos segredos e definira senhas de roles.")
    recebido = input(f"Digite {CONFIRMACAO} para continuar: ").strip()
    if recebido != CONFIRMACAO:
        raise RuntimeError("Confirmacao recusada; nenhuma alteracao foi realizada.")


def executar() -> int:
    args = criar_argumentos()
    token_vault = solicitar_segredo("Token de operador do Vault")
    senha_admin = solicitar_segredo(
        f"Senha PostgreSQL do usuario {args.postgres_admin}"
    )

    cliente_vault = criar_cliente_vault(
        args.vault_url,
        token_vault,
        args.vault_mount,
    )
    with conectar_postgresql(args, senha_admin) as conexao:
        if args.acao == "auditar":
            auditar_postgresql(conexao)
            auditar_vault(cliente_vault, args.vault_mount)
            print("Auditoria concluida sem alteracoes.")
            return 0

        confirmar()
        if args.acao == "provisionar":
            validar_roles_para_provisionamento(conexao)
            validar_caminhos_novos(cliente_vault, args.vault_mount)
            senhas = gerar_senhas()
            criar_segredos(cliente_vault, args.vault_mount, args, senhas)
            print("Segredos criados no Vault com CAS 0.")
        else:
            senhas = carregar_senhas(cliente_vault, args.vault_mount)
            print("Segredos existentes validados; nenhum valor foi exibido.")

        try:
            aplicar_senhas(conexao, senhas)
        except Exception:
            print(
                "Falha ao aplicar as senhas no PostgreSQL. Os segredos nao foram "
                "apagados. Corrija a causa e use 'aplicar-senhas-do-vault'.",
                file=sys.stderr,
            )
            raise

    print("Credenciais provisionadas sem exibir valores secretos.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(executar())
    except (RuntimeError, psycopg.Error, vault_exceptions.VaultError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        raise SystemExit(1) from None
