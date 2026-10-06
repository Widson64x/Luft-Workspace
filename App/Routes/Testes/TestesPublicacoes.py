"""Rotas nao produtivas para validar publicacoes do LuftBase."""

import os

from flask import abort, request
from flask_login import current_user, login_required
from luftbase import (
    ItemNotaAtualizacao,
    NovaPublicacao,
    PermissaoLuftBase,
    TipoAudiencia,
    TipoItemAtualizacao,
    TipoPublicacao,
    exigir_permissao,
    obter_luftbase,
)
from luftbase.web.autenticacao import _validar_csrf

from App.Routes.Principal import PrincipalBp


def _dados() -> dict[str, object]:
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _permitir_teste() -> None:
    ambiente = (os.getenv("LUFT_AMBIENTE") or "desenvolvimento").casefold()
    if ambiente in {"prod", "producao", "production"}:
        abort(404)
    _validar_csrf()


@PrincipalBp.post("/api/teste-publicacoes/comunicado/global")
@login_required
@exigir_permissao(PermissaoLuftBase.TESTES_PUBLICACOES_EXECUTAR)
def testar_comunicado_global():  # type: ignore[no-untyped-def]
    """Cria e publica um comunicado geral no escopo do Workspace."""

    _permitir_teste()
    dados = _dados()
    servico = obter_luftbase().publicacoes
    identificador = servico.criar_rascunho(
        NovaPublicacao(
            titulo=str(dados.get("titulo") or "Comunicado de teste"),
            resumo=str(dados.get("resumo") or "Validacao do novo canal corporativo."),
            conteudo=str(
                dados.get("conteudo") or "Conteudo criado pelo piloto LuftBase."
            ),
            criado_por=current_user.login,
        )
    )
    servico.publicar(identificador)
    return {"id_publicacao": identificador}, 201


@PrincipalBp.post("/api/teste-publicacoes/comunicado/grupos")
@login_required
@exigir_permissao(PermissaoLuftBase.TESTES_PUBLICACOES_EXECUTAR)
def testar_comunicado_grupo():  # type: ignore[no-untyped-def]
    """Cria e publica um comunicado para o grupo atual."""

    _permitir_teste()
    if current_user.id_grupo is None:
        abort(400, description="O usuario atual nao possui grupo.")
    servico = obter_luftbase().publicacoes
    identificador = servico.criar_rascunho(
        NovaPublicacao(
            titulo="Comunicado segmentado de teste",
            conteudo="Somente o grupo atual deve visualizar este conteudo.",
            criado_por=current_user.login,
            audiencia=TipoAudiencia.GRUPOS,
            ids_grupos=(current_user.id_grupo,),
        )
    )
    servico.publicar(identificador)
    return {"id_publicacao": identificador}, 201


@PrincipalBp.post("/api/teste-publicacoes/nota-atualizacao")
@login_required
@exigir_permissao(PermissaoLuftBase.TESTES_PUBLICACOES_EXECUTAR)
def testar_nota_atualizacao():  # type: ignore[no-untyped-def]
    """Cria e publica uma nota de atualizacao completa."""

    _permitir_teste()
    dados = _dados()
    versao = str(dados.get("versao") or "0.1.0a1")
    servico = obter_luftbase().publicacoes
    identificador = servico.criar_rascunho(
        NovaPublicacao(
            titulo="Piloto LuftBase no Workspace",
            conteudo="O Hub deixou de depender do LuftCore.",
            criado_por=current_user.login,
            tipo=TipoPublicacao.ATUALIZACAO,
            versao=versao,
            itens_atualizacao=(
                ItemNotaAtualizacao(
                    titulo="Infraestrutura centralizada",
                    descricao="Vault, bancos, sessao e autorizacao agora usam LuftBase.",
                    tipo=TipoItemAtualizacao.MELHORIA,
                ),
            ),
        )
    )
    servico.publicar(identificador)
    return {"id_publicacao": identificador}, 201
