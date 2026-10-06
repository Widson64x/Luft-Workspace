"""Provas de integracao do piloto M10 sem acessar infraestrutura real."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from luftbase.configuracao import ConfiguracaoLuftBase
from luftbase.identidade import UsuarioAutenticado
from luftbase.infraestrutura.fabrica import FabricaInfraestruturaMemoria

from App import CriarApp
from App.Services.SistemasHubService import SistemasHubService


def _configuracao() -> ConfiguracaoLuftBase:
    return ConfiguracaoLuftBase.de_mapeamento(
        {
            "LUFT_APLICACAO_VERSAO": "0.1.1",
            "LUFT_AMBIENTE": "desenvolvimento",
            "LUFT_SISTEMA_ID": 0,
            "LUFT_VAULT_ENDERECO": "http://vault.invalid:8200",
            "LUFT_LDAP_SERVIDOR": "ldap.invalid",
            "LUFT_LDAP_DOMINIO": "luft",
        }
    )


def test_factory_instala_luftbase_e_rotas_sem_rede() -> None:
    app = CriarApp(_configuracao(), FabricaInfraestruturaMemoria())
    regras = {regra.rule for regra in app.url_map.iter_rules()}

    assert "luftbase" in app.extensions
    assert app.config["LUFT_SISTEMA_ID"] == 0
    assert "/login" in regras
    assert "/_luftbase/publicacoes" in regras
    assert "/_luftbase/interface/preferencia" in regras
    assert "/publicacoes/atualizacoes" in regras
    assert "/publicacoes/painel/comunicados" in regras
    assert "/seguranca/gerenciador" in regras
    assert "/configuracoes/painel" in regras
    assert app.test_client().get("/login").status_code == 200


def test_home_autenticada_renderiza_com_servicos_do_luftbase(monkeypatch) -> None:
    app = CriarApp(_configuracao(), FabricaInfraestruturaMemoria())
    estado = app.extensions["luftbase"]
    usuario = UsuarioAutenticado(2759, "widson", "Widson", None, 7, "TI")
    monkeypatch.setattr(
        type(estado.autorizacao),
        "possui",
        lambda _servico, _usuario, _chave: True,
    )
    monkeypatch.setattr(
        type(estado.autorizacao),
        "consultar",
        lambda _servico, _usuario, chaves: {chave: True for chave in chaves},
    )
    monkeypatch.setattr(
        SistemasHubService,
        "listar_para_usuario",
        lambda _servico, _usuario: [
            SimpleNamespace(
                id_sistema=1,
                nome="ConnectAir",
                descricao="Gestao aerea",
                em_manutencao=False,
                icone="ph-bold ph-airplane-tilt",
                link="/connectair",
            )
        ],
    )
    monkeypatch.setattr(
        type(estado.publicacoes),
        "listar_para_usuario",
        lambda _servico, _usuario, _grupo, **_opcoes: SimpleNamespace(itens=()),
    )
    cliente = app.test_client()
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = usuario.get_id()
        sessao["_fresh"] = True
        sessao["luftbase_usuario"] = usuario.como_dict()
        sessao["luftbase_preferencia_tema"] = {"tema": "luft", "modo": "SISTEMA"}

    resposta = cliente.get("/")

    assert resposta.status_code == 200
    assert b"LUFT WORKSPACE" in resposta.data
    assert b"/_luftbase/publicacoes/eventos" in resposta.data
    assert "Hub de Sistemas" in resposta.text
    assert "Painel de Controle" in resposta.text
    assert "?tab=tab-auditoria" in resposta.text
    assert "tab-configuracoes&amp;sub=auditoria" not in resposta.text
    assert "ph-bold ph-airplane-tilt" in resposta.text
    assert ">Modo<" in resposta.text
    assert ">Config.<" in resposta.text
    assert ">Sair<" in resposta.text
    assert "widson.araujo" not in resposta.text


def test_css_do_hub_preserva_acoes_e_modo_escuro() -> None:
    raiz = Path(__file__).parents[1]
    css_layout = raiz / "App" / "Static" / "Css" / "Hub.css"
    css_home = raiz / "App" / "Static" / "Css" / "HubHome.css"
    layout = css_layout.read_text(encoding="utf-8")
    home = css_home.read_text(encoding="utf-8")

    # O acabamento da sidebar pertence ao LuftBase (sidebar.css); o Hub.css nao a duplica,
    # senao o azul fixo copiado aqui anula os tokens de tema (luft, luft-esg).
    import luftbase

    sidebar = (
        Path(luftbase.__file__).parent / "interface" / "static" / "css" / "sidebar.css"
    ).read_text(encoding="utf-8")
    assert ".luft-actions {" not in layout
    assert ".luft-nav-link" not in layout
    assert sidebar.count(".luft-actions {") == 1
    assert "grid-template-columns: repeat(3, 1fr)" in sidebar
    assert ".luft-btn-action span" in sidebar
    assert layout.count("{") == layout.count("}")
    assert home.count("{") == home.count("}")
    assert "[data-luft-mode='escuro']) .hub-kpi-card" in home
    # O escuro do Hub segue o tema ativo (token), com o slate original apenas como fallback.
    assert "background: var(--luft-bg-panel, #1e293b)" in home


def test_nao_restou_dependencia_executavel_do_luftcore() -> None:
    raiz = Path(__file__).parents[1]
    arquivos = [
        *raiz.joinpath("App").rglob("*.py"),
        *raiz.joinpath("App").rglob("*.html"),
        raiz / "requirements.txt",
    ]

    padrao = re.compile(
        r"(?:from\s+luftcore|import\s+luftcore|luftcore/)", re.IGNORECASE
    )
    ocorrencias = [
        str(arquivo.relative_to(raiz))
        for arquivo in arquivos
        if padrao.search(arquivo.read_text(encoding="utf-8"))
    ]

    assert ocorrencias == []


class _ResultadoFalso:
    def __init__(self, linhas: list[SimpleNamespace]) -> None:
        self._linhas = linhas

    def all(self) -> list[SimpleNamespace]:
        return self._linhas


class _SessaoFalsa:
    def __init__(self, linhas: list[SimpleNamespace]) -> None:
        self._linhas = linhas
        self.consultas = 0

    def execute(self, _consulta: object) -> _ResultadoFalso:
        self.consultas += 1
        return _ResultadoFalso(self._linhas)


class _BancoFalso:
    def __init__(self, linhas: list[SimpleNamespace]) -> None:
        self.sessao = _SessaoFalsa(linhas)

    @contextmanager
    def leitura(self) -> Iterator[_SessaoFalsa]:
        yield self.sessao


def _sistema(
    identificador: int,
    *,
    chave: str | None = "PLATAFORMA.SISTEMA.ACESSAR",
) -> SimpleNamespace:
    return SimpleNamespace(
        id_sistema=identificador,
        nome_sistema=f"Sistema {identificador}",
        descricao_sistema=None,
        em_manutencao=False,
        icone=None,
        link=f"/sistema-{identificador}",
        chave_permissao=chave,
    )


def test_catalogo_respeita_autorizacao_hierarquica_e_negacao(monkeypatch) -> None:
    banco = _BancoFalso(
        [
            _sistema(1, chave="PLATAFORMA.SISTEMA.ACESSAR"),
            _sistema(2, chave="CONNECTAIR.SISTEMA.ACESSAR"),
            _sistema(3, chave="CONTROL.SISTEMA.ACESSAR"),
            _sistema(4, chave="INTEGRADOR.SISTEMA.ACESSAR"),
        ]
    )
    usuario = UsuarioAutenticado(2759, "widson", "Widson", None, 7, "TI")
    servico = SistemasHubService(banco)  # type: ignore[arg-type]

    def mock_consultar(
        *,
        id_sistema: int,
        id_usuario: int,
        id_grupo: int | None,
        chaves: tuple[str, ...],
    ) -> dict[str, bool]:
        chave = chaves[0]
        # Sistema 1 e 3 permitidos, 2 bloqueado explicitamente, 4 sem regra
        if id_sistema in (1, 3):
            return {chave: True}
        return {chave: False}

    monkeypatch.setattr(servico._autorizacao, "consultar", mock_consultar)

    sistemas = servico.listar_para_usuario(usuario)

    assert [sistema.id_sistema for sistema in sistemas] == [1, 3]


def test_painel_publicacoes_autorizado_renderiza_com_sucesso(monkeypatch) -> None:
    app = CriarApp(_configuracao(), FabricaInfraestruturaMemoria())
    estado = app.extensions["luftbase"]
    usuario = UsuarioAutenticado(2280, "widson", "Widson", None, 6, "TI")
    monkeypatch.setattr(
        type(estado.autorizacao),
        "possui",
        lambda _servico, _usuario, _chave: True,
    )
    monkeypatch.setattr(
        type(estado.autorizacao),
        "consultar",
        lambda _servico, _usuario, chaves: {chave: True for chave in chaves},
    )
    import luftbase.web.publicacoes as modulo_publicacoes

    monkeypatch.setattr(modulo_publicacoes, "_listar_administracao", lambda _tipo: [])
    monkeypatch.setattr(
        modulo_publicacoes,
        "_listar_sistemas",
        lambda: [{"id": 0, "nome": "Todos os sistemas (global)"}],
    )
    monkeypatch.setattr(modulo_publicacoes, "_listar_grupos", list)

    cliente = app.test_client()
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = usuario.get_id()
        sessao["_fresh"] = True
        sessao["luftbase_usuario"] = usuario.como_dict()
        sessao["luftbase_preferencia_tema"] = {"tema": "luft", "modo": "SISTEMA"}

    r_comunicados = cliente.get("/publicacoes/painel/comunicados")
    assert r_comunicados.status_code == 200
    assert "Comunicados" in r_comunicados.text

    r_atualizacoes = cliente.get("/publicacoes/painel/atualizacoes")
    assert r_atualizacoes.status_code == 200
    assert "Notas de Atualização" in r_atualizacoes.text


def test_painel_publicacoes_sem_permissao_responde_403(monkeypatch) -> None:
    app = CriarApp(_configuracao(), FabricaInfraestruturaMemoria())
    estado = app.extensions["luftbase"]
    usuario = UsuarioAutenticado(2280, "widson", "Widson", None, 6, "TI")
    monkeypatch.setattr(
        type(estado.autorizacao),
        "possui",
        lambda _servico, _usuario, _chave: False,
    )
    monkeypatch.setattr(
        type(estado.autorizacao),
        "consultar",
        lambda _servico, _usuario, chaves: {chave: False for chave in chaves},
    )

    cliente = app.test_client()
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = usuario.get_id()
        sessao["_fresh"] = True
        sessao["luftbase_usuario"] = usuario.como_dict()
        sessao["luftbase_preferencia_tema"] = {"tema": "luft", "modo": "SISTEMA"}

    r_comunicados = cliente.get("/publicacoes/painel/comunicados")
    assert r_comunicados.status_code == 403

    r_atualizacoes = cliente.get("/publicacoes/painel/atualizacoes")
    assert r_atualizacoes.status_code == 403
