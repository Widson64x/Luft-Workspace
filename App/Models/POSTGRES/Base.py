"""Base dos models do Luft-Workspace no PostgreSQL (schema próprio da aplicação).

O schema lógico `luft_aplicacao` é trocado pelo LuftBase pelo schema real do segredo do sistema
no Vault (ex.: `connectair`), então o nome nunca fica fixo no código.
"""

from luftbase.infraestrutura.banco.conexoes import ESQUEMA_LOGICO_APLICACAO
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

# Mesma convenção do scripts/MigrarSqlServerParaPostgres.py, para o DDL gerado dos dois lados bater.
CONVENCAO_NOMES = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}

Base = declarative_base(
    metadata=MetaData(schema=ESQUEMA_LOGICO_APLICACAO, naming_convention=CONVENCAO_NOMES)
)
