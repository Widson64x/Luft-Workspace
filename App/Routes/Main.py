"""Modulo de compatibilidade das rotas do Hub Central.

Este arquivo preserva o ponto de importacao historico enquanto as
rotas passam a viver em modulos separados por funcionalidade.
"""

from __future__ import annotations

from App.Routes.Principal import PrincipalBp  # noqa: F401

# Importacoes por efeito colateral: cada modulo anexa rotas ao mesmo blueprint.
from App.Routes.Testes import TestesNotificacoes, TestesPublicacoes  # noqa: F401
