"""
Busca global (barra superior) do Luft-Workspace: o que o sistema ensina o LuftBase a procurar.

Além do menu (que o LuftBase pesquisa sozinho), cada provedor abaixo vira um grupo de
resultados. A consulta roda dentro da requisição, só para quem tem a permissão do provedor, e
cada resultado precisa apontar para uma tela que o usuário consiga abrir.

Padrão Luft: este arquivo existe em todos os sistemas e expõe BUSCAS (vazio se não houver).
"""

from flask_login import current_user
from luftbase import ProvedorBusca, ResultadoBusca

from App.Conexoes import ObterBancoCore
from App.Services.SistemasHubService import SistemasHubService


def _Sistemas(termo, limite):
    """Sistemas do Hub que o usuário pode acessar (a regra de acesso é a do próprio Hub)."""
    alvo = termo.casefold()
    sistemas = SistemasHubService(ObterBancoCore()).listar_para_usuario(current_user._get_current_object())
    achados = [
        s for s in sistemas
        if s.link and not s.em_manutencao and (alvo in s.nome.casefold() or alvo in (s.descricao or '').casefold())
    ]
    return [
        ResultadoBusca(
            titulo=s.nome,
            subtitulo=s.descricao,
            url=s.link,
            icone=s.icone if s.icone and s.icone.startswith('ph-') else None,
        )
        for s in achados[:limite]
    ]


BUSCAS = (
    ProvedorBusca(
        id='sistemas',
        titulo='Sistemas',
        icone='ph-bold ph-squares-four',
        buscar=_Sistemas,
        # Os links dos sistemas podem ser endereços completos (outro serviço ou prefixo).
        urls_externas=True,
        minimo_caracteres=2,
    ),
)
