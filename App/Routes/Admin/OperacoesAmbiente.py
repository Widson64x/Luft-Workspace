"""Rotas da area de operacoes de ambiente do Hub Central."""

from __future__ import annotations

from flask import current_app, render_template, request
from flask_login import login_required
from luftcore.extensions.flask_extension import resposta_api_erro, resposta_api_sucesso
from luftcore.extensions.seguranca_extension import require_permission

from App.Routes.Principal import PrincipalBp
from App.Services.Admin.OperacoesAmbienteService import ServicoOperacoesAmbiente


@PrincipalBp.route("/configuracoes/operacoes-ambiente")
@login_required
@require_permission("ADMIN.SEGURANCA.VISUALIZAR")
def ConfiguracoesOperacoesAmbiente():
	"""Renderiza a tela de operações de ambiente e serviços."""
	servico = ServicoOperacoesAmbiente()
	projetos = servico.listarProjetos()
	servicos = servico.listarServicos()
	return render_template(
		"Pages/Admin/OperacoesAmbiente.html",
		projetosOperacao=projetos,
		servicosOperacao=servicos,
	)


@PrincipalBp.route("/api/configuracoes/operacoes-ambiente/projetos", methods=["GET"])
@login_required
@require_permission("ADMIN.SEGURANCA.VISUALIZAR")
def ApiListarProjetosOperacoesAmbiente():
	"""Lista projetos monitorados pelo módulo de operações de ambiente."""
	servico = ServicoOperacoesAmbiente()
	return resposta_api_sucesso({"projetos": servico.listarProjetos()})


@PrincipalBp.route("/api/configuracoes/operacoes-ambiente/variaveis", methods=["GET"])
@login_required
@require_permission("ADMIN.SEGURANCA.VISUALIZAR")
def ApiListarVariaveisProjetoOperacoesAmbiente():
	"""Lista variáveis permitidas para um projeto específico."""
	id_projeto = (request.args.get("idProjeto") or "").strip()
	if not id_projeto:
		return resposta_api_erro(mensagem="Informe o identificador do projeto.", status_http=400)

	servico = ServicoOperacoesAmbiente()
	try:
		variaveis = servico.listarVariaveisProjeto(id_projeto)
		return resposta_api_sucesso({"idProjeto": id_projeto, "variaveis": variaveis})
	except ValueError as erro_validacao:
		return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
	except Exception as erro_inesperado:
		current_app.logger.exception("Falha ao listar variáveis do projeto")
		return resposta_api_erro(
			mensagem="Falha ao listar variáveis do projeto.",
			detalhes={"erro": str(erro_inesperado)},
			status_http=500,
		)


@PrincipalBp.route("/api/configuracoes/operacoes-ambiente/variaveis/salvar", methods=["POST"])
@login_required
@require_permission("ADMIN.SEGURANCA.VISUALIZAR")
def ApiSalvarVariavelProjetoOperacoesAmbiente():
	"""Atualiza uma variável permitida de um projeto monitorado."""
	payload = request.get_json(silent=True) or {}
	id_projeto = str(payload.get("idProjeto") or "").strip()
	chave = str(payload.get("chave") or "").strip()
	valor = str(payload.get("valor") or "")

	if not id_projeto or not chave:
		return resposta_api_erro(mensagem="Informe idProjeto e chave para salvar.", status_http=400)

	servico = ServicoOperacoesAmbiente()
	try:
		servico.atualizarVariavelProjeto(id_projeto, chave, valor)
		return resposta_api_sucesso(
			{
				"idProjeto": id_projeto,
				"chave": chave,
			},
			mensagem="Variável atualizada com sucesso.",
		)
	except ValueError as erro_validacao:
		return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
	except Exception as erro_inesperado:
		current_app.logger.exception("Falha ao atualizar variável de ambiente")
		return resposta_api_erro(
			mensagem="Falha ao atualizar variável de ambiente.",
			detalhes={"erro": str(erro_inesperado)},
			status_http=500,
		)


@PrincipalBp.route("/api/configuracoes/operacoes-ambiente/servicos", methods=["GET"])
@login_required
@require_permission("ADMIN.SEGURANCA.VISUALIZAR")
def ApiListarServicosOperacoesAmbiente():
	"""Lista serviços controláveis e seus status atuais."""
	servico = ServicoOperacoesAmbiente()
	return resposta_api_sucesso({"servicos": servico.listarServicos()})


@PrincipalBp.route("/api/configuracoes/operacoes-ambiente/servicos/acao", methods=["POST"])
@login_required
@require_permission("ADMIN.SEGURANCA.VISUALIZAR")
def ApiExecutarAcaoServicoOperacoesAmbiente():
	"""Executa ação operacional de serviço (iniciar/parar/reiniciar)."""
	payload = request.get_json(silent=True) or {}
	id_servico = str(payload.get("idServico") or "").strip()
	acao = str(payload.get("acao") or "").strip()

	if not id_servico or not acao:
		return resposta_api_erro(mensagem="Informe idServico e acao.", status_http=400)

	servico = ServicoOperacoesAmbiente()
	try:
		retorno = servico.executarAcaoServico(id_servico, acao)
		return resposta_api_sucesso(retorno, mensagem="Ação executada com sucesso.")
	except ValueError as erro_validacao:
		return resposta_api_erro(mensagem=str(erro_validacao), status_http=400)
	except Exception as erro_inesperado:
		current_app.logger.exception("Falha ao executar acao de servico")
		return resposta_api_erro(
			mensagem="Falha ao executar ação de serviço.",
			detalhes={"erro": str(erro_inesperado)},
			status_http=500,
		)
