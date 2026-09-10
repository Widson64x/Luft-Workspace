"""Testes do espelhamento usado pelo deploy Windows."""

from __future__ import annotations

import pytest

from Utils.DeployMirror import sincronizar_espelho


def test_espelho_atualiza_e_preserva_dados_locais(tmp_path):
    origem = tmp_path / "checkout"
    destino = tmp_path / "aplicacao"
    (origem / "App").mkdir(parents=True)
    (destino / "App").mkdir(parents=True)
    (destino / ".venv").mkdir()
    (destino / "Logs").mkdir()

    (origem / "App.py").write_text("versao = 2\n", encoding="utf-8")
    (origem / "App" / "Main.py").write_text("ATIVO = True\n", encoding="utf-8")
    (destino / "App.py").write_text("versao = 1\n", encoding="utf-8")
    (destino / "obsoleto.py").write_text("remover = True\n", encoding="utf-8")
    (destino / ".env").write_text("SEGREDO=preservado\n", encoding="utf-8")
    (destino / ".venv" / "python.exe").write_text("local", encoding="utf-8")
    (destino / "Logs" / "app.log").write_text("local", encoding="utf-8")

    sincronizar_espelho(str(origem), str(destino))

    assert (destino / "App.py").read_text(encoding="utf-8") == "versao = 2\n"
    assert (destino / "App" / "Main.py").exists()
    assert not (destino / "obsoleto.py").exists()
    assert (destino / ".env").read_text(encoding="utf-8") == "SEGREDO=preservado\n"
    assert (destino / ".venv" / "python.exe").read_text(encoding="utf-8") == "local"
    assert (destino / "Logs" / "app.log").read_text(encoding="utf-8") == "local"


def test_espelho_recusa_destino_dentro_do_checkout(tmp_path):
    origem = tmp_path / "checkout"
    origem.mkdir()

    with pytest.raises(ValueError, match="dentro do checkout"):
        sincronizar_espelho(str(origem), str(origem / "deploy"))
