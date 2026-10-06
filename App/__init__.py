"""
Pacote do Luft-Workspace sobre o LuftBase.

O LuftBase instala login (LDAP + sessão compartilhada), permissões, auditoria, notificações,
publicações, mensagens, temas, e-mail e o Painel de Controle. Aqui ficam só as rotas e as
regras de negócio.

Padrão Luft: este arquivo tem a mesma ordem em todos os sistemas (imports, fábrica, contexto
global); o que é particular de cada sistema fica no fim, em "Particularidades".
Desenvolvimento: `python App.py`. Produção: `Wsgi.py`.
"""

from flask import Flask, current_app
from flask_login import current_user
from luftbase import DefinicaoModelo, PlataformaLuft, consultar_permissoes, contexto_painel

from App import Conexoes
from App._version import __version__
from App.Buscas import BUSCAS
from App.Catalogo import CATALOGO, PARAMETROS, PERMISSOES_MENU
from App.Configuracoes import ConfiguracaoAtual
from App.Models.POSTGRES import ModelsPostgres
from App.Routes import RegistrarRotas
from App.Services.LogService import LogService
from App.Services.SistemasHubService import SistemasHubService


def CriarApp(configuracao=None, fabrica_infraestrutura=None):
    """Fábrica padrão: Flask, LuftBase, conexões, rotas e contexto global dos templates."""
    LogService.Inicializar()

    app = Flask(
        __name__,
        template_folder='Templates',
        static_folder='Static',
        static_url_path='/Static',
    )
    app.config['LUFT_APLICACAO_VERSAO'] = __version__
    app.config['LUFT_LOG_DIR'] = ConfiguracaoAtual.DIR_LOGS

    # O catálogo (Catalogo.py) é conferido no core e completado a cada inicialização.
    # Os parâmetros aparecem em Painel de Controle > Configurações Gerais.
    # As tabelas do PostgreSQL são conferidas (sem DDL) e ausências aparecem no log.
    # As buscas (Buscas.py) alimentam a barra de busca global, além do menu.
    modelos = [DefinicaoModelo.de_modelo(m) for m in ModelsPostgres()]
    estado = PlataformaLuft(
        fabrica_infraestrutura, catalogo=CATALOGO, parametros=PARAMETROS, modelos=modelos, buscas=BUSCAS
    ).inicializar(app, configuracao)
    Conexoes.Inicializar(estado)

    RegistrarRotas(app)
    _RegistrarContextoGlobal(app, estado)
    _RegistrarParticularidades(app, estado)

    LogService.Info("App", f"Aplicação iniciada no ambiente {estado.configuracao.aplicacao.ambiente.value}.")
    return app


def _RegistrarContextoGlobal(app, estado):
    """Variáveis disponíveis em todos os templates (layout, Painel de Controle e menu)."""

    @app.context_processor
    def InjetarContextoGlobal():
        decisoes = consultar_permissoes(PERMISSOES_MENU.values())
        return {
            # As páginas do LuftBase (Painel de Controle, comunicados) estendem este layout.
            'layout_base': 'Layout/BaseLayout.html',
            'luft_base_template': 'Layout/BaseLayout.html',
            **contexto_painel(),
            'SidebarPermissoes': {
                nome: bool(decisoes.get(chave, False)) for nome, chave in PERMISSOES_MENU.items()
            },
            **_ContextoParticular(estado),
        }


# ========================================================================================
# Particularidades do Luft-Workspace
# ========================================================================================

def _ContextoParticular(estado):
    """Hub: catálogo de sistemas do usuário para o menu lateral e as iniciais do avatar."""
    usuario_iniciais = 'US'
    if not current_user.is_authenticated:
        return {'sistemas_menu': [], 'SistemasMenu': [], 'usuario_iniciais': usuario_iniciais}

    partes_nome = [p for p in str(getattr(current_user, 'nome_completo', '')).split() if p]
    if partes_nome:
        usuario_iniciais = ''.join(p[0] for p in (partes_nome[0], partes_nome[-1])).upper()
    try:
        sistemas = SistemasHubService(estado.bancos.core).listar_para_usuario(
            current_user._get_current_object()
        )
    except Exception:
        current_app.logger.exception('Falha ao carregar o catálogo de sistemas do Hub')
        sistemas = []
    return {
        'sistemas_menu': sistemas,
        'SistemasMenu': sistemas,
        'usuario_iniciais': usuario_iniciais,
    }


def _RegistrarParticularidades(app, estado):
    """Rotas e ajustes que só existem no Workspace (por ora, nenhum)."""

