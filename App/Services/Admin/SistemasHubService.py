"""Servicos de dominio do Hub Central.

Este modulo concentra as regras para carregar sistemas visiveis no painel
principal e para administrar o catalogo de sistemas da plataforma.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from luftcore.modules.seguranca import Tb_PermissaoGrupo, Tb_PermissaoUsuario, Tb_Sistema


@dataclass
class SistemaHubDto:
	"""Representa um sistema exibido no Hub.

	Atributos:
	idSistema: Identificador unico do sistema.
	nomeSistema: Nome exibido no card.
	descricaoSistema: Descricao funcional do sistema.
	ativo: Indica se o sistema esta ativo no catalogo.
	emManutencao: Indica se o sistema esta em janela de manutencao.
	icone: Classe de icone para a interface.
	link: URL de abertura do sistema.
	idPermissaoBase: Permissao base usada para liberar acesso.
	podeAcessar: Resultado da avaliacao de acesso do usuario atual.
	"""

	idSistema: int
	nomeSistema: str
	descricaoSistema: str | None
	ativo: bool
	emManutencao: bool
	icone: str | None
	link: str | None
	idPermissaoBase: int | None
	podeAcessar: bool


class ServicoSistemasHub:
	"""Servico de aplicacao para leitura e administracao de sistemas do Hub."""

	def __init__(self, securityManager: Any):
		"""Inicializa o servico com a instancia ativa de seguranca.

		Parametros:
		securityManager: Instancia de LuftSecurity registrada na aplicacao.
		"""
		self._securityManager = securityManager

	def _usuarioEhAdminMaster(self, usuarioAtual: Any) -> bool:
		"""Verifica se o usuario pertence ao grupo administrativo mestre."""
		nome_grupo = (getattr(usuarioAtual, "nome_grupo", "") or "").strip().upper()
		return nome_grupo == "ADM_SISTEMA"

	def _carregarPermissoesGrupo(self, sessao, idGrupo: int | None) -> set[int]:
		"""Carrega IDs de permissao concedidos ao grupo do usuario."""
		if not idGrupo:
			return set()

		registros = (
			sessao.query(Tb_PermissaoGrupo.Id_Permissao)
			.filter(Tb_PermissaoGrupo.Codigo_UsuarioGrupo == idGrupo)
			.all()
		)
		return {int(item.Id_Permissao) for item in registros}

	def _carregarOverridesUsuario(self, sessao, idUsuario: int | None) -> dict[int, bool]:
		"""Carrega overrides de permissao por usuario."""
		if not idUsuario:
			return {}

		registros = (
			sessao.query(Tb_PermissaoUsuario.Id_Permissao, Tb_PermissaoUsuario.Conceder)
			.filter(Tb_PermissaoUsuario.Codigo_Usuario == idUsuario)
			.all()
		)
		return {int(item.Id_Permissao): bool(item.Conceder) for item in registros}

	def _avaliarAcessoSistema(
		self,
		idPermissaoBase: int | None,
		permissoesGrupo: set[int],
		overridesUsuario: dict[int, bool],
		usuarioEhAdmin: bool,
	) -> bool:
		"""Aplica a regra de decisao de acesso para um sistema do catalogo."""
		if usuarioEhAdmin:
			return True

		if idPermissaoBase is None:
			return True

		if idPermissaoBase in overridesUsuario:
			return overridesUsuario[idPermissaoBase]

		return idPermissaoBase in permissoesGrupo

	def listarSistemasVisiveisParaUsuario(self, usuarioAtual: Any) -> list[SistemaHubDto]:
		"""Lista sistemas ativos e visiveis para o usuario logado.

		Parametros:
		usuarioAtual: Usuario autenticado no contexto do Flask-Login.

		Retorno:
		list[SistemaHubDto]: Sistemas elegiveis para exibicao no painel principal.
		"""
		id_usuario = int(str(usuarioAtual.get_id()).strip()) if usuarioAtual and usuarioAtual.get_id() else None
		id_grupo = getattr(usuarioAtual, "grupo_id", None)
		usuario_eh_admin = self._usuarioEhAdminMaster(usuarioAtual)

		sessao = self._securityManager.session_factory()
		try:
			sistemas_ativos = (
				sessao.query(Tb_Sistema)
				.filter(Tb_Sistema.Ativo == True)
				.filter(Tb_Sistema.Id_Sistema != 0)
				.order_by(Tb_Sistema.Nome_Sistema.asc())
				.all()
			)
			permissoes_grupo = self._carregarPermissoesGrupo(sessao, id_grupo)
			overrides_usuario = self._carregarOverridesUsuario(sessao, id_usuario)

			retorno: list[SistemaHubDto] = []
			for sistema in sistemas_ativos:
				pode_acessar = self._avaliarAcessoSistema(
					idPermissaoBase=sistema.Id_Permissao_Base,
					permissoesGrupo=permissoes_grupo,
					overridesUsuario=overrides_usuario,
					usuarioEhAdmin=usuario_eh_admin,
				)

				if not pode_acessar:
					continue

				retorno.append(
					SistemaHubDto(
						idSistema=int(sistema.Id_Sistema),
						nomeSistema=sistema.Nome_Sistema,
						descricaoSistema=sistema.Descricao_Sistema,
						ativo=bool(sistema.Ativo),
						emManutencao=bool(sistema.Em_Manutencao),
						icone=sistema.Icone,
						link=sistema.Link,
						idPermissaoBase=sistema.Id_Permissao_Base,
						podeAcessar=pode_acessar,
					)
				)

			return retorno
		finally:
			sessao.close()
