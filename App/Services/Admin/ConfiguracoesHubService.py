"""Servicos do painel central de configuracoes.

Este modulo centraliza o catalogo de modulos de configuracao, a
garantia de permissoes de exemplo e a filtragem de acesso do usuario.
"""

from __future__ import annotations

from typing import Any

from luftcore.modules.seguranca.services import LuftPermissionService


MODULOS_CONFIGURACAO = [
	{
		"id": "aplicacoes",
		"nome": "Configurar Aplicações",
		"descricao": "Gerencie sistemas, links, permissões base e status de manutenção no catálogo central.",
		"icone": "ph-bold ph-app-window",
		"permissao": "ADMIN.PAINEL.VISUALIZAR",
		"endpoint": "Principal.PainelSistemas",
		"status": "Disponível",
		"acao": "Acessar módulo",
	},
	{
		"id": "seguranca",
		"nome": "Segurança & Permissões",
		"descricao": "Gerencie usuários, grupos e permissões com a mecânica nativa do LuftCore.",
		"icone": "ph-bold ph-shield-check",
		"permissao": "ADMIN.SEGURANCA.VISUALIZAR",
		"endpoint": "Seguranca.visualizar_gerenciador",
		"status": "Disponível",
		"acao": "Abrir segurança",
	},
	{
		"id": "operacoes-ambiente",
		"nome": "Operações de Ambiente",
		"descricao": "Visualize variáveis permitidas e execute ações de serviço com governança operacional.",
		"icone": "ph-bold ph-terminal-window",
		"permissao": "ADMIN.SEGURANCA.VISUALIZAR",
		"endpoint": "Principal.ConfiguracoesOperacoesAmbiente",
		"status": "Disponível",
		"acao": "Abrir operações",
	},
	{
		"id": "apis",
		"nome": "Controle de APIs",
		"descricao": "Registro, status, monitoramento e governança dos endpoints internos e externos.",
		"icone": "ph-bold ph-plugs-connected",
		"permissao": "ADMIN.CONFIGURACOES.APIS.VISUALIZAR",
		"endpoint": "Principal.ConfiguracoesApis",
		"status": "Em breve",
		"acao": "Abrir módulo",
	},
	{
		"id": "rotas",
		"nome": "Gestão de Rotas",
		"descricao": "Inventário centralizado de rotas críticas, políticas e validações de acesso.",
		"icone": "ph-bold ph-path",
		"permissao": "ADMIN.CONFIGURACOES.ROTAS.VISUALIZAR",
		"endpoint": "Principal.ConfiguracoesRotas",
		"status": "Em breve",
		"acao": "Abrir módulo",
	},
	{
		"id": "procedures",
		"nome": "Central de Procedures",
		"descricao": "Ferramenta para organização de procedures, rotinas de OpenQuery e análises operacionais.",
		"icone": "ph-bold ph-database",
		"permissao": "ADMIN.CONFIGURACOES.PROCEDURES.VISUALIZAR",
		"endpoint": "Principal.ConfiguracoesProcedures",
		"status": "Em breve",
		"acao": "Abrir módulo",
	},
	{
		"id": "observabilidade",
		"nome": "Observabilidade Operacional",
		"descricao": "Painéis de integridade, desempenho e alertas de processos críticos do ecossistema.",
		"icone": "ph-bold ph-chart-line-up",
		"permissao": "ADMIN.CONFIGURACOES.OBSERVABILIDADE.VISUALIZAR",
		"endpoint": "Principal.ConfiguracoesObservabilidade",
		"status": "Em breve",
		"acao": "Abrir módulo",
	},
	{
		"id": "politicas-seguranca",
		"nome": "Políticas de Segurança",
		"descricao": "Controles avançados de autorização, trilha de auditoria e políticas por contexto.",
		"icone": "ph-bold ph-shield-check",
		"permissao": "ADMIN.CONFIGURACOES.POLITICAS_SEGURANCA.VISUALIZAR",
		"endpoint": "Principal.ConfiguracoesPoliticasSeguranca",
		"status": "Em breve",
		"acao": "Abrir módulo",
	},
]


def GarantirPermissoesConfiguracoesExemplo(securityManager: Any) -> None:
	"""Garante permissões de exemplo dos módulos de configurações no sistema atual.

	Parametros:
	securityManager: Instancia ativa de seguranca da aplicacao.

	Retorno:
	None
	"""
	modelo_permissao = securityManager.permissao_model
	sistema_id = int(securityManager.sistema_id)
	chaves = [item["permissao"] for item in MODULOS_CONFIGURACAO if item["permissao"].startswith("ADMIN.CONFIGURACOES.")]

	if not chaves:
		return

	sessao = securityManager.session_factory()
	try:
		existentes = (
			sessao.query(modelo_permissao.Chave_Permissao)
			.filter(
				modelo_permissao.Id_Sistema == sistema_id,
				modelo_permissao.Chave_Permissao.in_(chaves),
			)
			.all()
		)
		mapa_existentes = {item.Chave_Permissao for item in existentes}

		for definicao in MODULOS_CONFIGURACAO:
			chave = definicao["permissao"]
			if chave in mapa_existentes or not chave.startswith("ADMIN.CONFIGURACOES."):
				continue

			sessao.add(
				modelo_permissao(
					Id_Sistema=sistema_id,
					Chave_Permissao=chave,
					Descricao_Permissao=f"Permite visualizar o módulo '{definicao['nome']}'",
					Categoria_Permissao="CONFIGURACOES",
				)
			)

		sessao.commit()
	except Exception:
		sessao.rollback()
		raise
	finally:
		sessao.close()


class ServicoConfiguracoesHub:
	"""Servico de aplicacao para montagem dos modulos de configuracao."""

	def __init__(self, securityManager: Any):
		"""Inicializa o servico com a instancia de seguranca.

		Parametros:
		securityManager: Instancia ativa de seguranca.

		Retorno:
		None
		"""
		self._securityManager = securityManager

	def listarModulosPermitidos(self, usuarioAtual: Any) -> list[dict[str, Any]]:
		"""Lista os modulos de configuracao autorizados para o usuario.

		Parametros:
		usuarioAtual: Usuario autenticado no contexto do Flask-Login.

		Retorno:
		list[dict[str, Any]]: Modulos liberados com metadados de exibicao.
		"""
		permission_service = LuftPermissionService(self._securityManager)

		modulos_permitidos: list[dict[str, Any]] = []
		for indice, definicao in enumerate(MODULOS_CONFIGURACAO):
			possui_permissao = bool(permission_service.verificar_permissao(usuarioAtual, definicao["permissao"]))
			if not possui_permissao:
				continue

			modulo = dict(definicao)
			modulo["badgeClasse"] = "hub-badge-ok" if definicao["status"] == "Disponível" else "hub-badge-alerta"
			modulo["delayMs"] = indice * 45
			modulos_permitidos.append(modulo)

		return modulos_permitidos
