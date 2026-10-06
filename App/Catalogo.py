"""
Catálogo de módulos e permissões do Luft-Workspace no LuftBase.

O Hub não tem módulos próprios: o acesso à página inicial, o Painel de Controle e a
administração usam as permissões da plataforma (PermissaoLuftBase), já cadastradas no core.
Quando o Workspace ganhar permissões próprias, elas entram aqui, no mesmo formato do
Luft-ConnectAir (Permissao + CATALOGO), e o LuftBase as confere a cada inicialização.

Padrão Luft: estes nomes existem em todos os sistemas (Permissao, CATALOGO, PARAMETROS,
PERMISSOES_MENU), mesmo quando vazios.
"""

from enum import StrEnum


class Permissao(StrEnum):
    """Permissões próprias do sistema (nenhuma por ora)."""


# Sem catálogo próprio: o LuftBase não confere nem cria permissões para o Workspace.
CATALOGO = None

# Parâmetros: aparecem em Painel de Controle > Configurações Gerais.
PARAMETROS = ()

# Permissões do menu lateral e dos atalhos (nome -> chave), consultadas em lote.
PERMISSOES_MENU = {}
