from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

CAMINHO_SCRIPT = Path(__file__).parents[1] / "scripts" / "migrar_core_postgresql.py"
SPEC = importlib.util.spec_from_file_location("migrar_core_postgresql", CAMINHO_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULO = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULO
SPEC.loader.exec_module(MODULO)


def test_barreira_da_origem_aceita_somente_consultas() -> None:
    MODULO.proteger_comando_fonte("SELECT 1")
    MODULO.proteger_comando_fonte("  WITH dados AS (SELECT 1) SELECT * FROM dados")

    for comando in (
        "INSERT INTO dbo.teste VALUES (1)",
        "UPDATE dbo.teste SET valor = 1",
        "DELETE FROM dbo.teste",
        "DROP TABLE dbo.teste",
        "ALTER TABLE dbo.teste ADD coluna int",
        "EXEC dbo.procedure_perigosa",
    ):
        with pytest.raises(MODULO.ErroMigracao):
            MODULO.proteger_comando_fonte(comando)


def test_mapa_de_notificacoes_preserva_ids_livres_e_remapeia_colisoes() -> None:
    assert MODULO.construir_mapa_ids_notificacoes([1, 2, 13], [13, 14, 15]) == {
        13: 16,
        14: 14,
        15: 15,
    }


def test_ddl_usa_texto_longo_e_contem_integridade_referencial() -> None:
    ddl_tabelas = "\n".join(MODULO.ddl_tabelas("core"))
    ddl_fks = "\n".join(MODULO.ddl_chaves_estrangeiras("core"))
    ddl_indices = "\n".join(MODULO.ddl_indices("core"))

    assert "parametros_requisicao text" in ddl_tabelas
    assert "resposta_acao text" in ddl_tabelas
    assert "conteudo text NOT NULL" in ddl_tabelas
    assert "FOREIGN KEY (id_logacesso)" in ddl_fks
    assert "FOREIGN KEY (id_notificacao)" in ddl_fks
    assert "ON DELETE CASCADE" in ddl_fks
    assert "ix_core_logacesso_data" in ddl_indices
    assert "ux_core_publicacao_fonte_id_externo" in ddl_indices


def test_conjunto_gerenciado_tem_as_treze_tabelas() -> None:
    tabelas = MODULO.tabelas_gerenciadas()
    assert len(tabelas) == 13
    assert len(set(tabelas)) == 13
    assert "tb_sistema" in tabelas
    assert "tb_notaatualizacaoitem" in tabelas
