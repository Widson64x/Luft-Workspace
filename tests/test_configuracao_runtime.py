"""Testes das configuracoes locais dependentes do sistema operacional."""

from __future__ import annotations

from App.Configuracoes import NormalizarNomesServicosWindows


def test_normaliza_nomes_systemd_no_windows(monkeypatch):
    monkeypatch.setattr("App.Configuracoes.platform.system", lambda: "Windows")
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
    monkeypatch.setattr("App.Configuracoes.platform.system", lambda: "Windows")
    monkeypatch.setenv("LUFT_CONTROL_SERVICE_NAME", "Servico-Control-Customizado")

    NormalizarNomesServicosWindows()

    assert (
        os_environ_subset()["LUFT_CONTROL_SERVICE_NAME"]
        == "Servico-Control-Customizado"
    )


def test_linux_preserva_nomes_systemd(monkeypatch):
    monkeypatch.setattr("App.Configuracoes.platform.system", lambda: "Linux")
    monkeypatch.setenv("LUFT_WORKSPACE_SERVICE_NAME", "luft-workspace.service")

    NormalizarNomesServicosWindows()

    assert (
        os_environ_subset()["LUFT_WORKSPACE_SERVICE_NAME"] == "luft-workspace.service"
    )


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
