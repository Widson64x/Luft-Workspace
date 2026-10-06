"""Registro das rotas do Luft-Workspace.

Cada módulo de rotas expõe um Blueprint; a lista BLUEPRINTS define o prefixo de cada um.
A página inicial (Principal) fica na raiz.
"""

from App.Routes.Principal import PrincipalBp

# Rotas de validação (não produtivas): importadas pelo efeito de anexar ao PrincipalBp.
from App.Routes.Testes import TestesNotificacoes, TestesPublicacoes  # noqa: F401

BLUEPRINTS = (
    (PrincipalBp, None),
)


def RegistrarRotas(app):
    """Registra todos os blueprints da aplicação."""
    for blueprint, prefixo in BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=prefixo)
