"""Rotas nao produtivas para validar notificacoes do LuftBase."""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import abort
from flask_login import current_user, login_required
from luftbase import (
    CategoriaNotificacao,
    NovaNotificacao,
    PermissaoLuftBase,
    TipoNotificacao,
    exigir_permissao,
    obter_luftbase,
)
from luftbase.web.autenticacao import _validar_csrf

from App.Routes.Principal import PrincipalBp


def _permitir_teste() -> None:
    ambiente = (os.getenv("LUFT_AMBIENTE") or "desenvolvimento").casefold()
    if ambiente in {"prod", "producao", "production"}:
        abort(404)
    _validar_csrf()


@PrincipalBp.post("/api/teste-notificacao/usuario")
@login_required
@exigir_permissao(PermissaoLuftBase.TESTES_NOTIFICACOES_EXECUTAR)
def testar_notificacao_usuario():  # type: ignore[no-untyped-def]
    """Envia uma notificacao somente ao usuario atual."""

    _permitir_teste()
    identificador = obter_luftbase().notificacoes.criar(
        NovaNotificacao(
            titulo="Notificacao direcionada",
            mensagem="Esta notificacao foi enviada somente para voce.",
            tipo=TipoNotificacao.SUCESSO,
            categoria=CategoriaNotificacao.USUARIO,
            id_usuario_destino=current_user.id_usuario,
            criado_por=current_user.login,
        )
    )
    return {"id_notificacao": identificador}, 201


@PrincipalBp.post("/api/teste-notificacao/grupo")
@login_required
@exigir_permissao(PermissaoLuftBase.TESTES_NOTIFICACOES_EXECUTAR)
def testar_notificacao_grupo():  # type: ignore[no-untyped-def]
    """Envia uma notificacao ao grupo do usuario atual."""

    _permitir_teste()
    if current_user.id_grupo is None:
        abort(400, description="O usuario atual nao possui grupo.")
    identificador = obter_luftbase().notificacoes.criar(
        NovaNotificacao(
            titulo="Notificacao para o grupo",
            mensagem="Todos os membros do grupo podem receber este aviso.",
            id_grupo_destino=current_user.id_grupo,
            criado_por=current_user.login,
        )
    )
    return {"id_notificacao": identificador}, 201


@PrincipalBp.post("/api/teste-notificacao/agendada")
@login_required
@exigir_permissao(PermissaoLuftBase.TESTES_NOTIFICACOES_EXECUTAR)
def testar_notificacao_agendada():  # type: ignore[no-untyped-def]
    """Agenda uma notificacao para quinze segundos no futuro."""

    _permitir_teste()
    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
    identificador = obter_luftbase().notificacoes.criar(
        NovaNotificacao(
            titulo="Notificacao agendada",
            mensagem="Este aviso foi programado para aparecer depois.",
            exibir_a_partir_de=agora + timedelta(seconds=15),
            criado_por=current_user.login,
        )
    )
    return {"id_notificacao": identificador}, 201
