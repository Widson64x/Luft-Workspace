"""Rotas da area de configuracoes do Hub Central."""

from __future__ import annotations

from flask import current_app, render_template, url_for
from flask_login import current_user, login_required
from luftcore.extensions.seguranca_extension import require_permission

from App.Routes.Principal import PrincipalBp
from App.Services.Admin.ConfiguracoesHubService import (
    GarantirPermissoesConfiguracoesExemplo,
    ServicoConfiguracoesHub,
)


@PrincipalBp.route("/configuracoes")
@login_required
@require_permission("HOME.VISUALIZAR")
def ConfiguracoesHub():
    """Renderiza o painel central de configuracoes do Hub.

    Retorno:
    Response: HTML do painel de configuracoes.
    """
    security_manager = current_app.extensions["luft_security"]

    try:
        GarantirPermissoesConfiguracoesExemplo(security_manager)
    except Exception as erro_permissoes:
        current_app.logger.warning(
            "Falha ao garantir permissões de configuração de exemplo: %s",
            str(erro_permissoes),
        )

    servico = ServicoConfiguracoesHub(security_manager)
    modulos_permitidos = servico.listarModulosPermitidos(current_user)

    for modulo in modulos_permitidos:
        modulo["href"] = url_for(modulo["endpoint"])

    return render_template(
        "Pages/Admin/ConfiguracoesHub.html",
        modulosPermitidos=modulos_permitidos,
    )


@PrincipalBp.route("/configuracoes/apis")
@login_required
@require_permission("ADMIN.CONFIGURACOES.APIS.VISUALIZAR")
def ConfiguracoesApis():
    """Rota placeholder do módulo de controle de APIs."""
    return render_template(
        "Pages/Admin/ConfiguracaoPlaceholder.html",
        tituloModulo="Controle de APIs",
        descricaoModulo="Módulo de exemplo. Estrutura de rota e permissão já provisionada para futura implementação.",
    )


@PrincipalBp.route("/configuracoes/rotas")
@login_required
@require_permission("ADMIN.CONFIGURACOES.ROTAS.VISUALIZAR")
def ConfiguracoesRotas():
    """Rota placeholder do módulo de gestão de rotas."""
    return render_template(
        "Pages/Admin/ConfiguracaoPlaceholder.html",
        tituloModulo="Gestão de Rotas",
        descricaoModulo="Módulo de exemplo. Estrutura de rota e permissão já provisionada para futura implementação.",
    )


@PrincipalBp.route("/configuracoes/procedures")
@login_required
@require_permission("ADMIN.CONFIGURACOES.PROCEDURES.VISUALIZAR")
def ConfiguracoesProcedures():
    """Rota placeholder do módulo de procedures."""
    return render_template(
        "Pages/Admin/ConfiguracaoPlaceholder.html",
        tituloModulo="Central de Procedures",
        descricaoModulo="Módulo de exemplo. Estrutura de rota e permissão já provisionada para futura implementação.",
    )


@PrincipalBp.route("/configuracoes/observabilidade")
@login_required
@require_permission("ADMIN.CONFIGURACOES.OBSERVABILIDADE.VISUALIZAR")
def ConfiguracoesObservabilidade():
    """Rota placeholder do módulo de observabilidade operacional."""
    return render_template(
        "Pages/Admin/ConfiguracaoPlaceholder.html",
        tituloModulo="Observabilidade Operacional",
        descricaoModulo="Módulo de exemplo. Estrutura de rota e permissão já provisionada para futura implementação.",
    )


@PrincipalBp.route("/configuracoes/politicas-seguranca")
@login_required
@require_permission("ADMIN.CONFIGURACOES.POLITICAS_SEGURANCA.VISUALIZAR")
def ConfiguracoesPoliticasSeguranca():
    """Rota placeholder do módulo de políticas de segurança."""
    return render_template(
        "Pages/Admin/ConfiguracaoPlaceholder.html",
        tituloModulo="Políticas de Segurança",
        descricaoModulo="Módulo de exemplo. Estrutura de rota e permissão já provisionada para futura implementação.",
    )
