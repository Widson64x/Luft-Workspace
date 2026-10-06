"""Pagina inicial do Hub e catalogo de sistemas."""

from __future__ import annotations

import os

from flask import Blueprint, current_app, render_template
from flask_login import current_user, login_required
from luftbase import PermissaoLuftBase, exigir_permissao, obter_luftbase

from App.Services.SistemasHubService import SistemasHubService

PrincipalBp = Blueprint("Principal", __name__)


@PrincipalBp.get("/")
@login_required
@exigir_permissao(PermissaoLuftBase.INICIO_VISUALIZAR)
def MenuPrincipal():  # type: ignore[no-untyped-def]
    """Renderiza o Hub usando catalogo e publicacoes do PostgreSQL."""

    estado = obter_luftbase()
    usuario = current_user._get_current_object()
    sistemas = SistemasHubService(estado.bancos.core).listar_para_usuario(usuario)
    diretorio_imagens = os.path.join(
        current_app.root_path, "Static", "Img", "Background"
    )
    extensoes = {".png", ".jpg", ".jpeg", ".webp"}
    imagens_hero = (
        [
            arquivo
            for arquivo in sorted(os.listdir(diretorio_imagens))
            if os.path.splitext(arquivo)[1].lower() in extensoes
        ]
        if os.path.isdir(diretorio_imagens)
        else []
    )
    pagina = estado.publicacoes.listar_para_usuario(
        usuario.id_usuario,
        usuario.id_grupo,
        limite=4,
    )
    total_sistemas = len(sistemas)
    total_operacionais = sum(1 for s in sistemas if not s.em_manutencao)
    total_manutencao = sum(1 for s in sistemas if s.em_manutencao)

    return render_template(
        "Pages/HomeHub.html",
        sistemas=sistemas,
        total_sistemas=total_sistemas,
        total_operacionais=total_operacionais,
        total_manutencao=total_manutencao,
        imagens_hero=imagens_hero,
        comunicados=pagina.itens,
    )
