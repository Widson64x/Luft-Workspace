# ruff: noqa: N999
"""Rotas controladas para validar comunicados e notas de atualizacao."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from flask import current_app, request, url_for
from flask_login import current_user, login_required
from luftcore.extensions.seguranca_extension import require_permission
from luftcore.modules.publicacoes.services import ErroValidacaoPublicacao
from luftcore.utils import agora_brasilia

from App.Routes.Principal import PrincipalBp


def _ambiente_permite_testes() -> bool:
    ambiente = (os.getenv("APP_ENV") or "desenvolvimento").strip().lower()
    return ambiente not in {"prod", "producao", "produção", "production"}


def _identidade_usuario() -> tuple[int | None, str]:
    try:
        id_usuario = int(str(current_user.get_id()).strip())
    except (AttributeError, TypeError, ValueError):
        id_usuario = None
    nome = (
        getattr(current_user, "nome_completo", None)
        or getattr(current_user, "nome", None)
        or "ADMIN TESTE"
    )
    return id_usuario, str(nome)


def _inteiro(dados: dict[str, Any], campo: str, padrao: int) -> int:
    try:
        return int(dados.get(campo, padrao))
    except (TypeError, ValueError) as erro:
        raise ErroValidacaoPublicacao(f"O campo {campo} deve ser inteiro.") from erro


def _booleano(dados: dict[str, Any], campo: str, padrao: bool) -> bool:
    valor = dados.get(campo, padrao)
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in {"1", "true", "sim", "yes", "on"}


def _datas_teste(
    dados: dict[str, Any],
    expirar_em_horas_padrao: int = 0,
) -> tuple[datetime | None, datetime | None]:
    agora = agora_brasilia()
    segundos = max(0, _inteiro(dados, "agendar_em_segundos", 0))
    horas = max(0, _inteiro(dados, "expirar_em_horas", expirar_em_horas_padrao))
    exibir_em = agora + timedelta(seconds=segundos) if segundos else None
    expirar_em = agora + timedelta(hours=horas) if horas else None
    return exibir_em, expirar_em


def _links_publicacao(id_publicacao: int) -> dict[str, str]:
    return {
        "detalhe": url_for(
            "LuftPublicacoes.visualizar_publicacao",
            id_publicacao=id_publicacao,
        ),
        "feed_comunicados": url_for("LuftPublicacoes.listar_comunicados"),
        "feed_atualizacoes": url_for("LuftPublicacoes.listar_atualizacoes"),
    }


def _executar_publicacao(
    montar_payload: Callable[[dict[str, Any]], dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    if not _ambiente_permite_testes():
        return {
            "status": "erro",
            "mensagem": "Rotas de teste de publicacoes sao bloqueadas em producao.",
        }, 403

    servico = current_app.extensions.get("luft_publicacoes")
    if servico is None:
        return {
            "status": "erro",
            "mensagem": "Servico de publicacoes nao configurado.",
        }, 503

    dados = request.get_json(silent=True) or {}
    id_usuario, nome_usuario = _identidade_usuario()
    criada: dict[str, Any] | None = None
    try:
        payload = montar_payload(dados)
        criada = servico.criar(
            criado_por=nome_usuario,
            criado_por_id=id_usuario,
            **payload,
        )
        resultado = criada
        if _booleano(dados, "publicar", True):
            resultado = servico.publicar(
                criada["id"],
                publicado_por=nome_usuario,
                publicado_por_id=id_usuario,
                url_detalhe=url_for(
                    "LuftPublicacoes.visualizar_publicacao",
                    id_publicacao=criada["id"],
                ),
            )

        return {
            "status": "sucesso",
            "mensagem": (
                "Publicacao criada e publicada com notificacoes."
                if resultado["status"] in {"PUBLICADO", "AGENDADO"}
                else "Rascunho criado com sucesso."
            ),
            "dados": resultado,
            "links": _links_publicacao(resultado["id"]),
        }, 201
    except ErroValidacaoPublicacao as erro:
        return {"status": "erro", "mensagem": str(erro)}, 400
    except Exception:
        current_app.logger.exception("Erro na rota de teste de publicacoes")
        resposta: dict[str, Any] = {
            "status": "erro",
            "mensagem": "Nao foi possivel concluir a publicacao de teste.",
        }
        if criada:
            resposta["rascunho_id"] = criada["id"]
        return resposta, 500


def _payload_comunicado_global(dados: dict[str, Any]) -> dict[str, Any]:
    exibir_em, expirar_em = _datas_teste(dados, expirar_em_horas_padrao=168)
    return {
        "tipo_publicacao": "COMUNICADO",
        "id_sistema": _inteiro(dados, "id_sistema", 0),
        "tipo_audiencia": "GERAL",
        "titulo": dados.get(
            "titulo",
            "Operação integrada: uma nova experiência de comunicação Luft",
        ),
        "resumo": dados.get(
            "resumo",
            "O Hub passa a reunir avisos importantes em um único lugar, com acesso rápido, seguro e contextualizado.",
        ),
        "conteudo": dados.get(
            "conteudo",
            "Olá, time!\n\nA partir de hoje, nossos comunicados corporativos passam a fazer parte de uma experiência integrada no Luft Workspace. A novidade foi criada para que informações importantes cheguem com mais clareza, no momento certo e para as pessoas certas.\n\nVocê encontrará os avisos diretamente no Hub e também na central de notificações. Comunicados globais serão exibidos em todo o ecossistema Luft, enquanto conteúdos direcionados respeitarão o sistema e o grupo de cada usuário.\n\nEsta evolução reduz ruídos, fortalece a transparência e mantém nossas equipes conectadas ao que realmente importa. Conte com o novo canal e acompanhe as próximas novidades!",
        ),
        "prioridade": dados.get("prioridade", "ALTA"),
        "notificar": _booleano(dados, "notificar", True),
        "fixado": _booleano(dados, "fixado", True),
        "exibir_a_partir_de": exibir_em,
        "expira_em": expirar_em,
        "metadados": {
            "origem": "POSTMAN_TESTE",
            "cenario": "COMUNICADO_GLOBAL",
            "destaque": "HUB_E_NOTIFICACOES",
        },
    }


def _payload_comunicado_grupos(dados: dict[str, Any]) -> dict[str, Any]:
    exibir_em, expirar_em = _datas_teste(dados, expirar_em_horas_padrao=72)
    grupos = dados.get("ids_grupos") or [
        int(getattr(current_user, "codigo_usuariogrupo", 6) or 6)
    ]
    return {
        "tipo_publicacao": "COMUNICADO",
        "id_sistema": _inteiro(dados, "id_sistema", 0),
        "tipo_audiencia": "GRUPOS",
        "ids_grupos": grupos,
        "titulo": dados.get(
            "titulo",
            "Atenção, equipe: validação assistida do novo Hub",
        ),
        "resumo": dados.get(
            "resumo",
            "Seu grupo foi selecionado para acompanhar a nova jornada de comunicados e contribuir com a validação.",
        ),
        "conteudo": dados.get(
            "conteudo",
            "Olá, equipe!\n\nEstamos iniciando uma etapa de validação assistida das novas experiências do Luft Workspace. Durante este período, seu grupo receberá comunicados direcionados com orientações, marcos da implantação e pontos que merecem atenção.\n\nAo navegar pelo Hub, confirme se o aviso aparece no card “Avisos e comunicados”, se a notificação foi recebida e se o conteúdo completo pode ser aberto normalmente.\n\nA participação de vocês é essencial para entregarmos uma experiência consistente a toda a operação. Obrigado pela parceria!",
        ),
        "prioridade": dados.get("prioridade", "NORMAL"),
        "notificar": _booleano(dados, "notificar", True),
        "fixado": _booleano(dados, "fixado", False),
        "exibir_a_partir_de": exibir_em,
        "expira_em": expirar_em,
        "metadados": {
            "origem": "POSTMAN_TESTE",
            "cenario": "COMUNICADO_POR_GRUPOS",
            "grupos_solicitados": grupos,
        },
    }


def _payload_nota_atualizacao(dados: dict[str, Any]) -> dict[str, Any]:
    exibir_em, expirar_em = _datas_teste(dados)
    itens = dados.get("itens_atualizacao") or [
        {
            "tipo": "NOVO",
            "titulo": "Central inteligente de comunicados",
            "descricao": "Novo fluxo completo para criar, segmentar, publicar e acompanhar comunicados diretamente pelo Painel de Controle.",
        },
        {
            "tipo": "MELHORIA",
            "titulo": "Hub atualizado em tempo quase real",
            "descricao": "Os avisos mais recentes agora aparecem automaticamente no Hub, sem necessidade de recarregar a página.",
        },
        {
            "tipo": "CORRECAO",
            "titulo": "Publicação e notificação na mesma transação",
            "descricao": "Reforçamos a consistência entre o comunicado publicado e suas notificações vinculadas.",
        },
        {
            "tipo": "SEGURANCA",
            "titulo": "Audiência protegida por sistema e grupo",
            "descricao": "A visibilidade é calculada no servidor para impedir acesso a conteúdos destinados a outros grupos ou sistemas.",
        },
        {
            "tipo": "TECNICO",
            "titulo": "API de feed reutilizável no LuftCore",
            "descricao": "Todos os produtos Luft podem consumir a mesma regra de comunicados globais e locais por meio do núcleo compartilhado.",
        },
    ]
    tipo_audiencia = str(dados.get("tipo_audiencia", "GERAL")).upper()
    grupos = dados.get("ids_grupos") or []
    return {
        "tipo_publicacao": "ATUALIZACAO",
        "id_sistema": _inteiro(dados, "id_sistema", 0),
        "tipo_audiencia": tipo_audiencia,
        "ids_grupos": grupos,
        "titulo": dados.get(
            "titulo",
            "Luft Workspace 0.4.0 — informação certa, no momento certo",
        ),
        "resumo": dados.get(
            "resumo",
            "Uma atualização focada em comunicação integrada, segmentação segura e uma experiência mais fluida em todo o ecossistema Luft.",
        ),
        "conteudo": dados.get(
            "conteudo",
            "Esta versão inaugura uma nova camada de comunicação no LuftCore. Comunicados corporativos, notificações e notas de atualização agora trabalham de forma coordenada, preservando o contexto de cada sistema e a audiência de cada mensagem.\n\nO resultado é uma experiência mais clara para quem publica, mais relevante para quem recebe e pronta para evoluir com futuras integrações externas, incluindo o Gmail.",
        ),
        "versao": dados.get("versao", "0.4.0"),
        "prioridade": dados.get("prioridade", "ALTA"),
        "notificar": _booleano(dados, "notificar", True),
        "fixado": _booleano(dados, "fixado", True),
        "exibir_a_partir_de": exibir_em,
        "expira_em": expirar_em,
        "itens_atualizacao": itens,
        "metadados": {
            "origem": "POSTMAN_TESTE",
            "cenario": "CHANGELOG_COMPLETO",
            "release": dados.get("versao", "0.4.0"),
            "componentes": ["PUBLICACOES", "NOTIFICACOES", "HUB", "RBAC"],
        },
    }


@PrincipalBp.route("/api/teste-publicacoes/comunicado/global", methods=["POST"])
@login_required
@require_permission("ADMIN.COMUNICADOS.CRIAR")
@require_permission("ADMIN.COMUNICADOS.PUBLICAR")
def ApiTesteComunicadoGlobal():
    """Cria e publica um comunicado geral e global completo."""
    return _executar_publicacao(_payload_comunicado_global)


@PrincipalBp.route("/api/teste-publicacoes/comunicado/grupos", methods=["POST"])
@login_required
@require_permission("ADMIN.COMUNICADOS.CRIAR")
@require_permission("ADMIN.COMUNICADOS.PUBLICAR")
def ApiTesteComunicadoGrupos():
    """Cria e publica um comunicado segmentado para um ou mais grupos."""
    return _executar_publicacao(_payload_comunicado_grupos)


@PrincipalBp.route("/api/teste-publicacoes/nota-atualizacao", methods=["POST"])
@login_required
@require_permission("ADMIN.ATUALIZACOES.CRIAR")
@require_permission("ADMIN.ATUALIZACOES.PUBLICAR")
def ApiTesteNotaAtualizacao():
    """Cria e publica uma nota completa, com todas as categorias de item."""
    return _executar_publicacao(_payload_nota_atualizacao)
