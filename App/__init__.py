"""Fabrica da aplicacao do Hub Central.

Este modulo inicializa o Flask, integra LuftCore para UI global e
ativa o modulo de seguranca LuftSecurity com sistema_id = 0.
"""

from __future__ import annotations

import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, current_app, redirect, request, session, url_for
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from luftcore.extensions.flask_extension import LuftCorePackages, LuftUser
from luftcore.extensions.seguranca_extension import LuftSecurity
from luftcore.modules.seguranca import (
    Tb_LogAcesso,
    Tb_Permissao,
    Tb_PermissaoGrupo,
    Tb_PermissaoUsuario,
    Usuario,
    UsuarioGrupo,
)
from luftcore.modules.seguranca.services import LuftPermissionService

from App.Db.Connections import GetSqlServerSession
from App.Services.Admin.SistemasHubService import ServicoSistemasHub

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
    app.secret_key = os.getenv("APP_SECRET_KEY", "hub-central-dev")
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
        nome_app=os.getenv("APP_NAME", "Luft Hub"),
        gerenciador_usuario=gerenciador_usuario,
        habilitar_mensagens=True,
        injetar_tema=True,
        injetar_global=True,
        injetar_animacoes=True,
        injetar_js=True,
        mostrar_topbar=True,
        mostrar_pesquisa=False,
        mostrar_notificacoes=False,
        mostrar_breadcrumb=True,
    )

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

    from App.Routes.Main import PrincipalBp

    app.register_blueprint(PrincipalBp)

    @app.before_request
    def RenovarSessaoSsoQuandoAutenticado() -> None:
        """Aplica políticas globais por requisição (legado + sessão SSO).

        Redireciona a rota administrativa legada para a tela consolidada
        de sistemas e renova metadados da sessão para SSO global.

        A sessão compartilhada permite o passe livre entre aplicações que
        utilizam a mesma chave e os mesmos parâmetros de cookie.

        Retorno:
        None
        """
        caminho_normalizado = request.path.rstrip("/") or "/"
        if caminho_normalizado == "/admin":
            return redirect(url_for("Principal.PainelSistemas"), code=302)

        if not app.config.get("LUFT_SSO_GLOBAL_ATIVO", True):
            return

        if current_user.is_authenticated:
            session.permanent = True
            session.modified = True

    @app.context_processor
    def InjetarPermissoesLayout():
        """Injeta dados globais de layout para navegação lateral e permissões.

        Retorno:
        dict: Flags e listas utilizadas para renderizar a árvore de navegação.
        """
        if not current_user.is_authenticated:
            return {
                "PodeAdministrarHub": False,
                "SistemasMenu": [],
            }

        permission_service = LuftPermissionService(current_app.extensions["luft_security"])
        pode_administrar = permission_service.verificar_permissao(current_user, "ADMIN.PAINEL.VISUALIZAR")

        try:
            from App.Services.Admin.ConfiguracoesHubService import ServicoConfiguracoesHub
            security_manager = current_app.extensions["luft_security"]
            servico_sistemas = ServicoSistemasHub(security_manager)
            servico_config = ServicoConfiguracoesHub(security_manager)
            sistemas_menu = servico_sistemas.listarSistemasVisiveisParaUsuario(current_user)
            modulos_configuracao = servico_config.listarModulosPermitidos(current_user)
        except Exception as erro:
            current_app.logger.warning("Erro ao carregar menu lateral: %s", str(erro))
            sistemas_menu = []
            modulos_configuracao = []

        return {
            "PodeAdministrarHub": bool(pode_administrar),
            "SistemasMenu": sistemas_menu,
            "ModulosConfiguracaoMenu": modulos_configuracao,
            "SsoGlobalAtivo": bool(app.config.get("LUFT_SSO_GLOBAL_ATIVO", True)),
            "SsoAplicacoesVinculadas": app.config.get("LUFT_SSO_APPS_VINCULADAS", []),
        }

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        IniciarAgendadorWorkflowsBackground(app)
    elif not hasattr(app, "_agendador_iniciado"):
        app._agendador_iniciado = True
        IniciarAgendadorWorkflowsBackground(app)

    return app


def IniciarAgendadorWorkflowsBackground(app: Flask) -> None:
    """Inicializa um worker thread em segundo plano para rodar tarefas agendadas."""
    import threading
    import time
    from App.Services.Admin.OrquestracaoBancoService import ServicoOrquestracaoBanco

    def worker():
        time.sleep(3)
        servico = ServicoOrquestracaoBanco()
        while True:
            try:
                with app.app_context():
                    servico.processarWorkflowsAgendados()
            except Exception as erro:
                app.logger.error("Erro no worker do Agendador de Tarefas: %s", str(erro))
            time.sleep(15)

    thread = threading.Thread(target=worker, daemon=True, name="AgendadorWorkflowsThread")
    thread.start()
