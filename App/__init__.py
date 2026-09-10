"""Fabrica da aplicacao do Hub Central.

Este modulo inicializa o Flask, integra LuftCore para UI global e
ativa o modulo de seguranca LuftSecurity com sistema_id = 0.
"""

from __future__ import annotations

import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, current_app, session
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from luftcore.extensions.flask_extension import LuftCorePackages, LuftUser
from luftcore.extensions.seguranca_extension import LuftSecurity
from luftcore.modules.auditoria import LuftAuditoria
from App.Models.SqlServer.Usuario import Usuario, UsuarioGrupo
from App.Models.SqlServer.Permissoes import (
    Tb_Permissao,
    Tb_PermissaoGrupo,
    Tb_PermissaoUsuario,
    Tb_LogAcesso,
    Tb_LogDetalhe,
)
from App.Db.Connections import GetSqlServerSession
from App.Services.Admin.SistemasHubService import ServicoSistemasHub


try:
    from _version import __version__
except ImportError:
    from ._version import __version__
except ImportError:
    __version__ = "0.1.0"

load_dotenv()


def ResolverBooleanoAmbiente(valor: str | None, padrao: bool = False) -> bool:
    """Converte valor textual de ambiente em booleano.

    Parametros:
    valor: Valor bruto lido das variaveis de ambiente.
    padrao: Valor retornado quando nao houver correspondencia.

    Retorno:
    bool: Valor booleano normalizado.
    """
    if valor is None:
        return padrao

    valor_normalizado = str(valor).strip().lower()
    if valor_normalizado in {"1", "true", "sim", "yes", "on"}:
        return True
    if valor_normalizado in {"0", "false", "nao", "não", "no", "off"}:
        return False
    return padrao


def ResolverInteiroAmbiente(valor: str | None, padrao: int) -> int:
    """Converte valor textual de ambiente em inteiro.

    Parametros:
    valor: Valor bruto lido das variaveis de ambiente.
    padrao: Valor retornado quando a conversao for invalida.

    Retorno:
    int: Valor inteiro normalizado.
    """
    if valor is None:
        return padrao

    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def ResolverListaAmbiente(valor: str | None) -> list[str]:
    """Converte string CSV de ambiente para lista sanitizada de itens.

    Parametros:
    valor: Conteudo bruto da variavel de ambiente em formato CSV.

    Retorno:
    list[str]: Lista de itens sem valores vazios.
    """
    if not valor:
        return []

    return [item.strip() for item in str(valor).split(",") if item and item.strip()]


def ConfigurarSessaoCompartilhada(app: Flask) -> None:
    """Aplica configuracoes de sessao para SSO entre aplicacoes Flask/LuftCore.

    Parametros:
    app: Aplicacao Flask que recebera as configuracoes de sessao.

    Retorno:
    None
    """
    app.config["SESSION_COOKIE_NAME"] = os.getenv("SESSION_COOKIE_NAME", "luft_sessao")
    app.config["SESSION_COOKIE_PATH"] = os.getenv("SESSION_COOKIE_PATH", "/")

    dominio_cookie = (os.getenv("SESSION_COOKIE_DOMAIN") or "").strip()
    if dominio_cookie:
        app.config["SESSION_COOKIE_DOMAIN"] = dominio_cookie

    same_site_cookie = (os.getenv("SESSION_COOKIE_SAMESITE") or "Lax").strip()
    if same_site_cookie:
        app.config["SESSION_COOKIE_SAMESITE"] = same_site_cookie

    secure_cookie = ResolverBooleanoAmbiente(os.getenv("SESSION_COOKIE_SECURE"), False)
    app.config["SESSION_COOKIE_SECURE"] = secure_cookie
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    if "PERMANENT_SESSION_LIFETIME_MINUTES" in os.environ:
        minutos_sessao = ResolverInteiroAmbiente(
            os.getenv("PERMANENT_SESSION_LIFETIME_MINUTES"),
            720,
        )
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=max(minutos_sessao, 1))

    # Mantem coerencia entre cookie de sessao e cookie de "lembrar-me" do Flask-Login.
    app.config["REMEMBER_COOKIE_NAME"] = os.getenv("REMEMBER_COOKIE_NAME", "luft_sessao_remember")
    app.config["REMEMBER_COOKIE_PATH"] = app.config["SESSION_COOKIE_PATH"]
    app.config["REMEMBER_COOKIE_SECURE"] = secure_cookie
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")

    if dominio_cookie:
        app.config["REMEMBER_COOKIE_DOMAIN"] = dominio_cookie


def ConfigurarPoliticaSsoGlobal(app: Flask) -> None:
    """Configura comportamento global de SSO entre aplicações vinculadas.

    Parametros:
    app: Aplicacao Flask que recebera as configuracoes de SSO global.

    Retorno:
    None
    """
    app.config["LUFT_SSO_GLOBAL_ATIVO"] = ResolverBooleanoAmbiente(
        os.getenv("LUFT_SSO_GLOBAL_ATIVO"),
        True,
    )
    app.config["LUFT_SSO_APPS_VINCULADAS"] = ResolverListaAmbiente(
        os.getenv("LUFT_SSO_APPS_VINCULADAS"),
    )


def CriarApp() -> Flask:
    """Cria e configura a aplicacao Flask do Hub Central.

    Retorno:
    Flask: Instancia configurada da aplicacao.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "Templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "Static"),
        static_url_path="/Static",
    )

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.secret_key = os.getenv("APP_SECRET_KEY", "gAAAAABqTWMijKXcZkhPlaQvDXxciI2tqksklJWs1ehCYn9sEoWzqL7WPtmjCekhqqrwVV7_31KmNCZbmZZS0z9pmYLvI4gJFw==")
    ConfigurarSessaoCompartilhada(app)
    ConfigurarPoliticaSsoGlobal(app)

    route_prefix = (os.getenv("ROUTE_PREFIX") or "").strip()

    gerenciador_usuario = LuftUser(
        callback_usuario=lambda: current_user,
        attr_nome="nome",
        nome_completo="nome_completo",
        email="email",
        cargo="nome_grupo",
    )

    LuftCorePackages(
        app=app,
        nome_app=os.getenv("APP_NAME", "Luft WorkSpace"),
        tipo_versao_app=os.getenv("APP_ENV"),
        versao_app=__version__,
        gerenciador_usuario=gerenciador_usuario,
        habilitar_mensagens=True,
        injetar_tema=True,
        injetar_global=True,
        injetar_animacoes=True,
        injetar_js=True,
        mostrar_topbar=True,
        mostrar_pesquisa=False,
        mostrar_notificacoes=True,
        mostrar_breadcrumb=True,
    )

    # Configurar polling de notificações para quasi tempo-real (5s)
    app.config["LUFT_NOTIFICACOES_POLLING_MS"] = 5000
    app.jinja_env.globals["luft_notificacoes_polling_ms"] = 5000

    # Registrar serviço de notificações no app.extensions
    from luftcore.modules.notificacoes.services import ServicoNotificacoes
    servico_notificacoes = ServicoNotificacoes(
        session_factory=GetSqlServerSession,
        sistema_id=int(os.getenv("SISTEMA_ID", "0")),
    )
    app.extensions["luft_notificacoes"] = servico_notificacoes

    usar_prefixo_mensagens = ResolverBooleanoAmbiente(
        os.getenv("LUFT_USAR_PREFIXO_MENSAGENS"),
        False,
    )

    if route_prefix and usar_prefixo_mensagens:
        endpoint_mensagens = f"{route_prefix}/_luftcore/mensagens"
        app.config["LUFT_ENDPOINT_MENSAGENS"] = endpoint_mensagens
        app.config["LUFT_MESSAGE_BACKEND_ENDPOINT"] = endpoint_mensagens
        app.jinja_env.globals["luft_endpoint_mensagens"] = endpoint_mensagens
        app.jinja_env.globals["luft_message_backend_endpoint"] = endpoint_mensagens

    luft_security = LuftSecurity()
    luft_security.init_app(
        app=app,
        sistema_id=int(os.getenv("SISTEMA_ID", "0")),
        session_factory=GetSqlServerSession,
        ldap_server=os.getenv("LDAP_SERVER", "luftfarma.com.br"),
        ldap_domain=os.getenv("LDAP_DOMAIN", "luftfarma"),
        user_model=Usuario,
        group_model=UsuarioGrupo,
        permissao_model=Tb_Permissao,
        permissao_grupo_model=Tb_PermissaoGrupo,
        permissao_usuario_model=Tb_PermissaoUsuario,
        log_acesso_model=Tb_LogAcesso,
        debug_permissions=(os.getenv("DEBUG_PERMISSIONS", "false").lower() == "true"),
    )

    # Inicializar modulo de Auditoria (LogAcesso + LogDetalhe)
    luft_auditoria = LuftAuditoria()
    luft_auditoria.init_app(
        app=app,
        session_factory=GetSqlServerSession,
        sistema_id=int(os.getenv("SISTEMA_ID", "0")),
        log_acesso_model=Tb_LogAcesso,
        log_detalhe_model=Tb_LogDetalhe,
        log_dir=os.getenv("LOG_DIRECTORY", "Logs"),
    )

    from luftcore.extensions.logging_extension import ConfigurarLogsGlobais
    ConfigurarLogsGlobais(app, GetSqlServerSession, sistema_id=int(os.getenv("SISTEMA_ID", "0")))

    from App.Routes.Main import PrincipalBp

    app.register_blueprint(PrincipalBp)

    @app.before_request
    def RenovarSessaoSsoQuandoAutenticado() -> None:
        """Renova os metadados da sessão compartilhada para SSO global.

        A sessão compartilhada permite o passe livre entre aplicações que
        utilizam a mesma chave e os mesmos parâmetros de cookie.

        Retorno:
        None
        """
        if not app.config.get("LUFT_SSO_GLOBAL_ATIVO", True):
            return

        if current_user.is_authenticated:
            session.permanent = True
            session.modified = True

    @app.teardown_appcontext
    def EncerrarSessoesBancoAoFinalizarRequisicao(exception: Exception | None = None) -> None:
        """Garante a liberacao absoluta das sessoes SQLAlchemy e sockets ODBC ao fim de cada requisicao HTTP."""
        try:
            from App.Db.Connections import RemoverSessaoSqlServer
            RemoverSessaoSqlServer()
        except Exception:
            pass

    @app.context_processor
    def InjetarNavegacaoLayout():
        """Injeta os sistemas visíveis na navegação lateral.

        Retorno:
        dict: Sistemas e configurações globais utilizados pelo layout.
        """
        if not current_user.is_authenticated:
            return {
                "SistemasMenu": [],
            }

        try:
            security_manager = current_app.extensions["luft_security"]
            servico_sistemas = ServicoSistemasHub(security_manager)
            sistemas_menu = servico_sistemas.listarSistemasVisiveisParaUsuario(current_user)
        except Exception as erro:
            current_app.logger.warning("Erro ao carregar menu lateral: %s", str(erro))
            sistemas_menu = []

        return {
            "SistemasMenu": sistemas_menu,
            "SsoGlobalAtivo": bool(app.config.get("LUFT_SSO_GLOBAL_ATIVO", True)),
            "SsoAplicacoesVinculadas": app.config.get("LUFT_SSO_APPS_VINCULADAS", []),
        }

    return app
