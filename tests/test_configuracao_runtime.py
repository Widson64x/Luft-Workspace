"""Testes das configuracoes dependentes do sistema operacional."""

from __future__ import annotations

from unittest.mock import Mock

import pyodbc

from App import NormalizarNomesServicosWindows
from App.Db import Connections


def test_pool_nativo_pyodbc_fica_desabilitado():
    assert pyodbc.pooling is False


def test_remove_sessao_faz_rollback_de_transacao_ativa(monkeypatch):
    sessao = Mock()
    sessao.in_transaction.return_value = True
    fabrica_scoped = Mock(return_value=sessao)
    fabrica_scoped.registry.has.return_value = True
    monkeypatch.setattr(Connections, "_SESSAO_SCOPED", fabrica_scoped)

    Connections.RemoverSessaoSqlServer()

    sessao.rollback.assert_called_once_with()
    fabrica_scoped.remove.assert_called_once_with()


def test_remove_sessao_sem_transacao_apenas_remove(monkeypatch):
    sessao = Mock()
    sessao.in_transaction.return_value = False
    fabrica_scoped = Mock(return_value=sessao)
    fabrica_scoped.registry.has.return_value = True
    monkeypatch.setattr(Connections, "_SESSAO_SCOPED", fabrica_scoped)

    Connections.RemoverSessaoSqlServer()

    sessao.rollback.assert_not_called()
    fabrica_scoped.remove.assert_called_once_with()


def test_remove_sessao_nao_cria_sessao_vazia(monkeypatch):
    fabrica_scoped = Mock()
    fabrica_scoped.registry.has.return_value = False
    monkeypatch.setattr(Connections, "_SESSAO_SCOPED", fabrica_scoped)

    Connections.RemoverSessaoSqlServer()

    fabrica_scoped.assert_not_called()
    fabrica_scoped.remove.assert_not_called()


def test_normaliza_nomes_systemd_no_windows(monkeypatch):
    monkeypatch.setattr("App.platform.system", lambda: "Windows")
    monkeypatch.setenv("LUFT_WORKSPACE_SERVICE_NAME", "luft-workspace.service")
    monkeypatch.setenv("LUFT_CONTROL_SERVICE_NAME", "luft-control.service")
    monkeypatch.setenv("LUFT_CONNECTAIR_SERVICE_NAME", "luft-connectair.service")
    monkeypatch.setenv("LUFT_INTEGRADOR_SERVICE_NAME", "luft-integrador.service")
    monkeypatch.delenv("NGINX_SERVICE_NAME", raising=False)

    NormalizarNomesServicosWindows()

    assert os_environ_subset() == {
        "LUFT_WORKSPACE_SERVICE_NAME": "Luft-Workspace",
        "LUFT_CONTROL_SERVICE_NAME": "Luft-Control",
        "LUFT_CONNECTAIR_SERVICE_NAME": "Luft-ConnectAir",
        "LUFT_INTEGRADOR_SERVICE_NAME": "Luft-Integrador",
        "NGINX_SERVICE_NAME": "nginx",
    }


def test_preserva_nome_windows_personalizado(monkeypatch):
    monkeypatch.setattr("App.platform.system", lambda: "Windows")
    monkeypatch.setenv("LUFT_CONTROL_SERVICE_NAME", "Servico-Control-Customizado")

    NormalizarNomesServicosWindows()

    assert os_environ_subset()["LUFT_CONTROL_SERVICE_NAME"] == "Servico-Control-Customizado"


def test_linux_preserva_nomes_systemd(monkeypatch):
    monkeypatch.setattr("App.platform.system", lambda: "Linux")
    monkeypatch.setenv("LUFT_WORKSPACE_SERVICE_NAME", "luft-workspace.service")

    NormalizarNomesServicosWindows()

    assert os_environ_subset()["LUFT_WORKSPACE_SERVICE_NAME"] == "luft-workspace.service"


def os_environ_subset() -> dict[str, str | None]:
    import os

    chaves = (
        "LUFT_WORKSPACE_SERVICE_NAME",
        "LUFT_CONTROL_SERVICE_NAME",
        "LUFT_CONNECTAIR_SERVICE_NAME",
        "LUFT_INTEGRADOR_SERVICE_NAME",
        "NGINX_SERVICE_NAME",
    )
    return {chave: os.getenv(chave) for chave in chaves}
