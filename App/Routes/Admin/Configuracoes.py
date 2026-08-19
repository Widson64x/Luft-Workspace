"""Rotas da area de configuracoes do Hub Central."""

from __future__ import annotations

from flask import current_app, render_template, request, url_for
from flask_login import current_user, login_required
from luftcore.extensions.flask_extension import resposta_api_erro, resposta_api_sucesso
from luftcore.extensions.seguranca_extension import require_permission

from App.Routes.Principal import PrincipalBp
from App.Services.Admin.ConfiguracoesHubService import (
    GarantirPermissoesConfiguracoesExemplo,
    ServicoConfiguracoesHub,
)
from App.Services.Admin.OrquestracaoBancoService import (
    EstruturaOrquestracaoBancoNaoConfiguradaError,
    ServicoOrquestracaoBanco,
)
from luftcore.modules.seguranca import auditar


def ResolverUsuarioOperacao() -> str:
    """Resolve identificador do usuário atual para trilha de auditoria.

    Retorno:
    str: Nome de usuário ou marcador de fallback.
    """
    usuario = current_user
    if not usuario:
        return "sistema"

    for atributo in ("nome", "username", "email", "id"):
        valor = getattr(usuario, atributo, None)
        if valor:
            return str(valor)

    return "sistema"


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


@PrincipalBp.route("/configuracoes/orquestracao-banco")
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ConfiguracoesOrquestracaoBanco():
    """Renderiza o módulo de orquestração de bancos de dados."""
    servico = ServicoOrquestracaoBanco()
    diagnostico_estrutura = servico.obterDiagnosticoEstrutura()
    procedimentos = servico.listarProcedimentos() if diagnostico_estrutura["estruturaPronta"] else []
    conexoes = servico.listarConexoes() if diagnostico_estrutura["estruturaPronta"] else []

    return render_template(
        "Pages/Admin/OrquestracaoBanco.html",
        procedimentos=procedimentos,
        conexoesIntegracao=conexoes,
        diagnosticoEstrutura=diagnostico_estrutura,
        scriptEstruturaOrquestracaoBanco="App/Db/Scripts/CriarEstruturaOrquestracaoBanco.sql",
    )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/conexoes", methods=["GET"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiListarConexoesIntegracao():
    """Lista conexões reutilizáveis da central de orquestração de bancos."""
    servico = ServicoOrquestracaoBanco()
    try:
        return resposta_api_sucesso({"conexoes": servico.listarConexoes()})
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/conexoes/testar", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiTestarConexaoIntegracao():
    """Testa conexao com o banco via Vault antes de salvar."""
    payload = request.get_json(silent=True) or {}
    servico = ServicoOrquestracaoBanco()

    try:
        resultado = servico.testarConexaoPayload(payload)
        return resposta_api_sucesso(resultado, mensagem=resultado["mensagem"])
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao testar conexão de banco")
        return resposta_api_erro(
            mensagem="Falha ao testar conexão de banco.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/conexoes/salvar", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
@auditar("EDITAR", "CONEXAO")
def ApiSalvarConexaoIntegracao():
    """Cria ou atualiza conexões usadas na orquestração de banco após validar a conectividade."""
    payload = request.get_json(silent=True) or {}
    servico = ServicoOrquestracaoBanco()
    usuario_operacao = ResolverUsuarioOperacao()

    try:
        id_conexao = servico.salvarConexao(payload, usuario_operacao)
        return resposta_api_sucesso({"idConexao": id_conexao}, mensagem="Conexão salva com sucesso!")
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao salvar conexão de banco")
        
        return resposta_api_erro(
            mensagem="Falha ao salvar conexão de banco.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/conexoes/excluir", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
@auditar("EXCLUIR", "CONEXAO", severidade="ALTA")
def ApiExcluirConexaoIntegracao():
    """Exclui uma conexão cadastrada se não estiver em uso."""
    payload = request.get_json(silent=True) or {}
    id_conexao = str(payload.get("idConexao") or "").strip()
    if not id_conexao:
        return resposta_api_erro(mensagem="Informe idConexao para exclusão.", status_http=400)

    servico = ServicoOrquestracaoBanco()
    try:
        servico.excluirConexao(int(id_conexao))
        return resposta_api_sucesso(mensagem="Conexão excluída com sucesso.")
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao excluir conexão de banco")
        return resposta_api_erro(
            mensagem="Falha ao excluir conexão de banco.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/excluir", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
@auditar("EXCLUIR", "ORQUESTRACAO", severidade="ALTA")
def ApiExcluirProcedimentoIntegracao():
    """Exclui uma tarefa de orquestração e seu histórico."""
    payload = request.get_json(silent=True) or {}
    id_procedimento = str(payload.get("idProcedimento") or "").strip()
    if not id_procedimento:
        return resposta_api_erro(mensagem="Informe idProcedimento para exclusão.", status_http=400)

    servico = ServicoOrquestracaoBanco()
    try:
        servico.excluirProcedimento(int(id_procedimento))
        return resposta_api_sucesso(mensagem="Tarefa excluída com sucesso.")
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao excluir tarefa de orquestração")
        return resposta_api_erro(
            mensagem="Falha ao excluir tarefa de orquestração.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/listar", methods=["GET"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiListarProcedimentosIntegracao():
    """Lista tarefas de orquestração com status consolidado."""
    servico = ServicoOrquestracaoBanco()
    try:
        return resposta_api_sucesso({"procedimentos": servico.listarProcedimentos()})
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/detalhe", methods=["GET"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiDetalheProcedimentoIntegracao():
    """Retorna detalhe completo de uma tarefa para edição."""
    id_procedimento = (request.args.get("idProcedimento") or "").strip()
    if not id_procedimento:
        return resposta_api_erro(mensagem="Informe idProcedimento.", status_http=400)

    servico = ServicoOrquestracaoBanco()
    try:
        detalhe = servico.obterDetalheProcedimento(int(id_procedimento))
        return resposta_api_sucesso({"procedimento": detalhe})
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao obter detalhe de tarefa de orquestração")
        return resposta_api_erro(
            mensagem="Falha ao obter detalhe de tarefa de orquestração.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/historico", methods=["GET"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiHistoricoProcedimentoIntegracao():
    """Lista histórico de execução de uma tarefa de orquestração."""
    id_procedimento = (request.args.get("idProcedimento") or "").strip()
    if not id_procedimento:
        return resposta_api_erro(mensagem="Informe idProcedimento.", status_http=400)

    servico = ServicoOrquestracaoBanco()
    try:
        historico = servico.listarHistoricoExecucao(int(id_procedimento), limite=40)
        return resposta_api_sucesso({"idProcedimento": int(id_procedimento), "historico": historico})
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao listar histórico de execução")
        return resposta_api_erro(
            mensagem="Falha ao listar histórico de execução.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/salvar", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
@auditar("EDITAR", "ORQUESTRACAO")
def ApiSalvarProcedimentoIntegracao():
    """Cria ou atualiza cadastro de tarefa de orquestração."""
    payload = request.get_json(silent=True) or {}
    servico = ServicoOrquestracaoBanco()
    usuario_operacao = ResolverUsuarioOperacao()

    try:
        id_procedimento = servico.salvarProcedimento(payload, usuario_operacao)
        return resposta_api_sucesso(
            {"idProcedimento": id_procedimento},
            mensagem="Tarefa salva com sucesso.",
        )
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao salvar tarefa de orquestração")
        msg_erro = str(getattr(erro_inesperado, "orig", erro_inesperado))
        return resposta_api_erro(
            mensagem=f"Falha ao salvar tarefa: {msg_erro}",
            detalhes={"erro": msg_erro},
            status_http=400,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/testar-origem", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiTestarOrigemProcedimentoIntegracao():
    """Executa a query de origem em modo preview durante a montagem."""
    payload = request.get_json(silent=True) or {}
    servico = ServicoOrquestracaoBanco()

    try:
        retorno_preview = servico.testarOrigem(payload)
        return resposta_api_sucesso(retorno_preview, mensagem="Preview da origem executado com sucesso.")
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao testar query de origem")
        return resposta_api_erro(
            mensagem="Falha ao testar query de origem.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/testar-workflow", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
def ApiTestarWorkflowIntegracao():
    """Testa a orquestração completa em memória antes de salvar."""
    payload = request.get_json(silent=True) or {}
    servico = ServicoOrquestracaoBanco()

    try:
        retorno_teste = servico.testarWorkflow(payload)
        return resposta_api_sucesso(retorno_teste, mensagem="Teste da orquestração executado com sucesso.")
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        msg_erro = str(erro_validacao)
        return resposta_api_erro(mensagem=msg_erro, detalhes={"erro": msg_erro}, status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha ao testar orquestração de banco")
        msg_erro = str(erro_inesperado)
        if getattr(erro_inesperado, 'orig', None):
            msg_erro = str(erro_inesperado.orig)
        return resposta_api_erro(
            mensagem=f"Erro de sintaxe ou execução SQL:\n{msg_erro}",
            detalhes={"erro": msg_erro},
            status_http=400,
        )


@PrincipalBp.route("/api/configuracoes/orquestracao-banco/executar", methods=["POST"])
@login_required
@require_permission("ADMIN.CONFIGURACOES.ORQUESTRACAO_BANCO.VISUALIZAR")
@auditar("EXECUTAR", "ORQUESTRACAO", severidade="MEDIA")
def ApiExecutarProcedimentoIntegracao():
    """Executa manualmente uma tarefa de orquestração de banco."""
    payload = request.get_json(silent=True) or {}
    id_procedimento = str(payload.get("idProcedimento") or "").strip()
    if not id_procedimento:
        return resposta_api_erro(mensagem="Informe idProcedimento para execução.", status_http=400)

    servico = ServicoOrquestracaoBanco()
    usuario_operacao = ResolverUsuarioOperacao()

    try:
        retorno_execucao = servico.executarProcedimento(int(id_procedimento), usuario_operacao)
        return resposta_api_sucesso(retorno_execucao, mensagem="Tarefa executada com sucesso.")
    except EstruturaOrquestracaoBancoNaoConfiguradaError as erro_estrutura:
        return resposta_api_erro(mensagem=str(erro_estrutura), status_http=409)
    except ValueError as erro_validacao:
        return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
    except Exception as erro_inesperado:
        current_app.logger.exception("Falha na execução de tarefa de orquestração")
        
        return resposta_api_erro(
            mensagem="Falha na execução da tarefa.",
            detalhes={"erro": str(erro_inesperado)},
            status_http=500,
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
