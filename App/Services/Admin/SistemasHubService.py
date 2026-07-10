"""Servicos de dominio do Hub Central.

Este modulo concentra as regras para carregar sistemas visiveis no painel
principal e para administrar o catalogo de sistemas da plataforma.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from sqlalchemy import func

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

	def listarSistemasParaAdministracao(self) -> list[Tb_Sistema]:
		"""Lista todos os sistemas para a tela administrativa."""
		sessao = self._securityManager.session_factory()
		try:
			return sessao.query(Tb_Sistema).order_by(Tb_Sistema.Id_Sistema.asc()).all()
		finally:
			sessao.close()

	def salvarSistema(self, payload: dict[str, Any]) -> Tb_Sistema:
		"""Cria ou atualiza um sistema no catalogo central.

		Parametros:
		payload: Dicionario com os campos do formulario administrativo.

		Retorno:
		Tb_Sistema: Entidade persistida apos commit.
		"""
		id_sistema = int(payload.get("idSistema") or 0)
		nome_sistema_informado = str(payload.get("nomeSistema") or "").strip()
		sessao = self._securityManager.session_factory()
		try:
			if id_sistema > 0:
				sistema = sessao.query(Tb_Sistema).filter(Tb_Sistema.Id_Sistema == id_sistema).first()
				if not sistema:
					raise ValueError("Sistema informado nao foi encontrado.")
			else:
				# Se o cliente enviar id=0 em um fluxo de edicao, reaproveita o registro existente por nome.
				sistema_existente = None
				if nome_sistema_informado:
					sistema_existente = (
						sessao.query(Tb_Sistema)
						.filter(func.lower(Tb_Sistema.Nome_Sistema) == nome_sistema_informado.lower())
						.first()
					)

				if sistema_existente:
					sistema = sistema_existente
				else:
					sistema = Tb_Sistema()
					sessao.add(sistema)

			sistema.Nome_Sistema = nome_sistema_informado
			sistema.Descricao_Sistema = str(payload.get("descricaoSistema") or "").strip() or None
			sistema.Ativo = bool(payload.get("ativo", True))
			sistema.Em_Manutencao = bool(payload.get("emManutencao", False))
			sistema.Icone = str(payload.get("icone") or "").strip() or None
			sistema.Link = str(payload.get("link") or "").strip() or None

			id_permissao_base = payload.get("idPermissaoBase")
			sistema.Id_Permissao_Base = int(id_permissao_base) if id_permissao_base not in (None, "") else None

			if not sistema.Nome_Sistema:
				raise ValueError("Nome do sistema e obrigatorio.")

			sessao.commit()
			sessao.refresh(sistema)
			return sistema
		except Exception:
			sessao.rollback()
			raise
		finally:
			sessao.close()
