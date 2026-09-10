"""Rotas do menu principal do Hub Central.

Este modulo concentra apenas a pagina inicial do Hub, mantendo as
demais funcionalidades em blueprints especificos por dominio.
"""

from __future__ import annotations

import os
from flask import Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user, login_required
from luftcore.extensions.seguranca_extension import require_permission

from App.Services.Admin.SistemasHubService import ServicoSistemasHub

PrincipalBp = Blueprint("Principal", __name__)


@PrincipalBp.route("/login", methods=["GET", "POST"])
def Login():
    return redirect(url_for("Autenticacao.login"))


@PrincipalBp.route("/logout")
def Logout():
    return redirect(url_for("Autenticacao.logout"))


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

    imagens_hero = []
    diretorio_imagens = os.path.join(current_app.root_path, "Static", "Img", "Background")
    if os.path.isdir(diretorio_imagens):
        extensoes_permitidas = {".png", ".jpg", ".jpeg", ".webp"}
        imagens_hero = [
            arquivo
            for arquivo in sorted(os.listdir(diretorio_imagens))
            if os.path.splitext(arquivo)[1].lower() in extensoes_permitidas
        ]

    comunicados = []
    try:
        servico_publicacoes = current_app.extensions.get("luft_publicacoes")
        if servico_publicacoes is not None:
            id_usuario = int(str(current_user.get_id()).strip())
            id_grupo = getattr(current_user, "codigo_usuariogrupo", None)
            comunicados = servico_publicacoes.listar_para_usuario(
                id_usuario=id_usuario,
                id_grupo=int(id_grupo) if id_grupo is not None else None,
                tipo_publicacao=None,
                limite=4,
            )
    except Exception as erro:
        current_app.logger.warning("Erro ao carregar avisos e comunicados do Hub: %s", str(erro))

    return render_template(
        "Pages/HomeHub.html",
        sistemas=sistemas,
        imagens_hero=imagens_hero,
        comunicados=comunicados,
    )
