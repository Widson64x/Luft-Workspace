"""Rotas do menu principal do Hub Central.

Este modulo concentra apenas a pagina inicial do Hub, mantendo as
demais funcionalidades em blueprints especificos por dominio.
"""

from __future__ import annotations

from flask import Blueprint, current_app, render_template
from flask_login import current_user, login_required
from luftcore.extensions.seguranca_extension import require_permission

from App.Services.Admin.SistemasHubService import ServicoSistemasHub

PrincipalBp = Blueprint("Principal", __name__)


@PrincipalBp.route("/")
@login_required
@require_permission("HOME.VISUALIZAR")
def MenuPrincipal():
    """Renderiza a pagina inicial do Hub com os sistemas permitidos.

    Retorno:
    Response: HTML do dashboard principal.
    """
    security_manager = current_app.extensions["luft_security"]
    servico = ServicoSistemasHub(security_manager)
    sistemas = servico.listarSistemasVisiveisParaUsuario(current_user)
    return render_template("Pages/HomeHub.html", sistemas=sistemas)