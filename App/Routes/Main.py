"""Modulo de compatibilidade das rotas do Hub Central.

Este arquivo preserva o ponto de importacao historico enquanto as
rotas passam a viver em modulos separados por funcionalidade.
"""

from __future__ import annotations

from App.Routes.Principal import PrincipalBp

# Importacoes por efeito colateral: cada modulo anexa rotas ao mesmo blueprint.
from App.Routes.Admin import AdminSistemas  # noqa: F401
from App.Routes.Admin import Configuracoes  # noqa: F401
from App.Routes.Admin import OperacoesAmbiente  # noqa: F401
