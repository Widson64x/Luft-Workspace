"""Models do Luft-Workspace no PostgreSQL (schema próprio da aplicação)."""

import importlib
import pathlib

from App.Models.POSTGRES.Base import Base

# Importa todos os módulos para registrar os models na Base.
for _arquivo in sorted(pathlib.Path(__file__).parent.glob("*.py")):
    if _arquivo.stem not in ("__init__", "Base"):
        importlib.import_module(f"App.Models.POSTGRES.{_arquivo.stem}")


def ModelsPostgres():
    """Classes mapeadas, em ordem de tabela (para registro no LuftBase)."""
    return sorted((m.class_ for m in Base.registry.mappers), key=lambda c: c.__table__.name)
