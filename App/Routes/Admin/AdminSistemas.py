"""Rotas da area administrativa de sistemas do Hub Central."""

from __future__ import annotations

from flask import current_app, render_template, request
from flask_login import login_required
from luftcore.extensions.flask_extension import resposta_api_erro, resposta_api_sucesso
from luftcore.extensions.seguranca_extension import require_permission
from luftcore.modules.seguranca import Tb_Sistema
from sqlalchemy.exc import IntegrityError

from App.Routes.Principal import PrincipalBp
from App.Services.Admin.SistemasHubService import ServicoSistemasHub


@PrincipalBp.route("/admin/sistemas")
@login_required
@require_permission("ADMIN.PAINEL.VISUALIZAR")
def PainelSistemas():
	"""Renderiza a tela administrativa para cadastro e edicao de sistemas."""
	security_manager = current_app.extensions["luft_security"]
	servico = ServicoSistemasHub(security_manager)
	sistemas = servico.listarSistemasParaAdministracao()

	sessao = security_manager.session_factory()
	try:
		permissoes = (
			sessao.query(security_manager.permissao_model)
			.order_by(
				security_manager.permissao_model.Id_Sistema.asc(),
				security_manager.permissao_model.Categoria_Permissao.asc(),
				security_manager.permissao_model.Chave_Permissao.asc(),
			)
			.all()
		)

		sistemas_cadastrados = sessao.query(Tb_Sistema).order_by(Tb_Sistema.Nome_Sistema.asc()).all()
		nome_sistema_por_id = {int(item.Id_Sistema): item.Nome_Sistema for item in sistemas_cadastrados}

		permissoes_por_sistema_mapa = {}
		for permissao in permissoes:
			id_sistema_permissao = int(permissao.Id_Sistema)
			if id_sistema_permissao not in permissoes_por_sistema_mapa:
				permissoes_por_sistema_mapa[id_sistema_permissao] = {
					"idSistema": id_sistema_permissao,
					"nomeSistema": nome_sistema_por_id.get(id_sistema_permissao, f"Sistema {id_sistema_permissao}"),
					"permissoes": [],
				}
			permissoes_por_sistema_mapa[id_sistema_permissao]["permissoes"].append(permissao)

		permissoes_por_sistema = sorted(
			permissoes_por_sistema_mapa.values(),
			key=lambda item: (item["nomeSistema"] or "").lower(),
		)
	finally:
		sessao.close()

	return render_template(
		"Pages/Admin/AdminSistemas.html",
		sistemas=sistemas,
		permissoes=permissoes,
		permissoesPorSistema=permissoes_por_sistema,
	)


@PrincipalBp.route("/api/admin/sistemas/salvar", methods=["POST"])
@login_required
@require_permission("ADMIN.PAINEL.EDITAR")
def ApiSalvarSistema():
	"""Endpoint de persistencia de cadastro de sistemas do Hub."""
	security_manager = current_app.extensions["luft_security"]
	servico = ServicoSistemasHub(security_manager)

	payload = request.get_json(silent=True) or {}
	try:
		sistema = servico.salvarSistema(payload)
		return resposta_api_sucesso(
			{
				"idSistema": sistema.Id_Sistema,
				"nomeSistema": sistema.Nome_Sistema,
			},
			mensagem="Sistema salvo com sucesso.",
		)
	except ValueError as erro_validacao:
		return resposta_api_erro(
			mensagem=str(erro_validacao),
			status_http=400,
		)
	except IntegrityError as erro_integridade:
		current_app.logger.warning("Erro de integridade ao salvar sistema: %s", str(erro_integridade))
		return resposta_api_erro(
			mensagem="Não foi possível salvar: já existe um sistema com esse nome ou há conflito de chave.",
			detalhes={"erro": str(erro_integridade)},
			status_http=409,
		)
	except Exception as erro_inesperado:
		current_app.logger.exception("Erro inesperado ao salvar sistema")
		return resposta_api_erro(
			mensagem="Falha ao salvar sistema.",
			detalhes={"erro": str(erro_inesperado)},
			status_http=500,
		)
