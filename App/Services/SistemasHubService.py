"""Consulta do catalogo de sistemas com a autorizacao hierarquica do LuftBase."""

from __future__ import annotations

from dataclasses import dataclass

from luftbase.autorizacao import PermissaoLuftBase
from luftbase.autorizacao.repositorio import RepositorioAutorizacao
from luftbase.identidade import UsuarioAutenticado
from luftbase.infraestrutura.banco.sessoes import BancoSQLAlchemy
from luftbase.persistencia.core import Permissao, Sistema
from sqlalchemy import and_, select


@dataclass(frozen=True, slots=True)
class SistemaHub:
    """Sistema visivel e destacado do ORM."""

    id_sistema: int
    nome: str
    descricao: str | None
    em_manutencao: bool
    icone: str | None
    link: str | None


class SistemasHubService:
    """Lista apenas sistemas cujo acesso tenha sido comprovado pelo RBAC."""

    def __init__(self, banco_core: BancoSQLAlchemy) -> None:
        self._banco = banco_core
        self._autorizacao = RepositorioAutorizacao(banco_core)

    def listar_para_usuario(self, usuario: object) -> list[SistemaHub]:
        """Nega sistemas sem uma permissao de acesso ativa e concedida."""

        if not isinstance(usuario, UsuarioAutenticado):
            return []
        with self._banco.leitura() as sessao:
            linhas = sessao.execute(
                select(
                    Sistema.id_sistema,
                    Sistema.nome_sistema,
                    Sistema.descricao_sistema,
                    Sistema.em_manutencao,
                    Sistema.icone,
                    Sistema.link,
                    Permissao.chave_permissao,
                )
                .outerjoin(
                    Permissao,
                    and_(
                        Permissao.id_sistema == Sistema.id_sistema,
                        Permissao.eh_acesso_sistema.is_(True),
                        Permissao.ativo.is_(True),
                    ),
                )
                .where(Sistema.ativo.is_(True), Sistema.id_sistema != 0)
                .order_by(Sistema.ordem_exibicao, Sistema.nome_sistema)
            ).all()

        sistemas: list[SistemaHub] = []
        for linha in linhas:
            # Se o sistema possui permissão base (eh_acesso_sistema = True), verifica a concessão.
            # Se não possuir permissão base cadastrada, restringe a administradores (SISTEMA_ADMINISTRAR).
            chave = linha.chave_permissao or PermissaoLuftBase.SISTEMA_ADMINISTRAR.value
            id_escopo = linha.id_sistema if linha.chave_permissao else 0
            decisao = self._autorizacao.consultar(
                id_sistema=id_escopo,
                id_usuario=usuario.id_usuario,
                id_grupo=usuario.id_grupo,
                chaves=(chave,),
            )
            if decisao.get(chave, False):
                sistemas.append(
                    SistemaHub(
                        id_sistema=linha.id_sistema,
                        nome=linha.nome_sistema,
                        descricao=linha.descricao_sistema,
                        em_manutencao=bool(linha.em_manutencao),
                        icone=linha.icone,
                        link=linha.link,
                    )
                )
        return sistemas
