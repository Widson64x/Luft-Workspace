"""Publica a nota global "Nova plataforma Luft" (mudança para o LuftBase) no ambiente do .env.

Rode na pasta do Workspace, com o .env do ambiente desejado (homologação primeiro):

    python scripts/PublicarChangelogPlataforma.py                   # só mostra o que faria
    python scripts/PublicarChangelogPlataforma.py --executar        # cria, publica e notifica
    python scripts/PublicarChangelogPlataforma.py --executar --rascunho   # só cria o rascunho
    python scripts/PublicarChangelogPlataforma.py --executar --sem-notificar

É seguro repetir: uma nota já publicada não é duplicada, e um rascunho é atualizado com o texto atual.
A nota é GLOBAL (sistema 0): aparece em Notas de Atualização de todos os sistemas.
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def main():
    parser = argparse.ArgumentParser(description="Publica a nota global de lançamento do LuftBase.")
    parser.add_argument("--versao", default="2.0", help="versão exibida na nota (padrão: 2.0)")
    parser.add_argument("--executar", action="store_true", help="grava no banco (padrão: só simula)")
    parser.add_argument("--rascunho", action="store_true", help="cria sem publicar")
    parser.add_argument("--sem-notificar", action="store_true", help="publica sem notificar os usuários")
    args = parser.parse_args()

    from luftbase.conteudo import changelog_plataforma as nota

    print(f"Título : {nota.TITULO}")
    print(f"Versão : {args.versao} | global (sistema 0) | notificação: {'não' if args.sem_notificar else 'sim'}")
    print(f"Texto  : {len(nota.CONTEUDO)} caracteres")
    if not args.executar:
        print("\nSimulação concluída: nada foi gravado. Use --executar para aplicar.")
        return 0

    from App import CriarApp
    from luftbase.plataforma import obter_luftbase

    app = CriarApp()
    with app.app_context():
        resultado = nota.publicar_changelog_plataforma(
            obter_luftbase().publicacoes,
            versao=args.versao,
            notificar=not args.sem_notificar,
            publicar=not args.rascunho,
        )
    rotulos = {"criada": "criada", "atualizada": "rascunho atualizado", "ja_publicada": "já estava publicada"}
    print(f"\nNota #{resultado.id_publicacao}: {rotulos[resultado.acao]}"
          f"{' e publicada' if resultado.publicada and resultado.acao != 'ja_publicada' else ''}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
