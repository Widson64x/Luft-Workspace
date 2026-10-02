"""Sincroniza o checkout do deploy com o diretório da aplicação no Windows.

O destino se torna um espelho do repositório, mas arquivos de ambiente,
ambientes virtuais, logs e dados locais permanecem intocados.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil

PASTAS_PRESERVADAS = {
    ".git",
    ".venv",
    ".idea",
    ".pytest_cache",
    "logs",
    "data/save",
    "data/temp",
}

ARQUIVOS_PRESERVADOS = {
    ".env",
    "db.sqlite3",
    "db.sqlite3-journal",
    "deploy-log.txt",
}


def _normalizar(caminho: str) -> str:
    return caminho.replace("\\", "/").strip("/").lower()


def deve_preservar_pasta(caminho_relativo: str) -> bool:
    caminho = _normalizar(caminho_relativo)
    return any(
        caminho == pasta or caminho.startswith(f"{pasta}/")
        for pasta in PASTAS_PRESERVADAS
    )


def deve_preservar_arquivo(caminho_relativo: str) -> bool:
    caminho = caminho_relativo.replace("\\", "/").strip("/")
    if os.path.basename(caminho).lower() in ARQUIVOS_PRESERVADOS:
        return True
    return deve_preservar_pasta(os.path.dirname(caminho))


def corrigir_casing(pasta_pai: str, nome_esperado: str) -> None:
    """Corrige diferenças de maiúsculas/minúsculas no NTFS em duas etapas."""
    if not os.path.exists(pasta_pai):
        return

    try:
        entradas = os.listdir(pasta_pai)
    except OSError:
        return

    for entrada in entradas:
        if entrada.lower() != nome_esperado.lower() or entrada == nome_esperado:
            continue

        caminho_atual = os.path.join(pasta_pai, entrada)
        caminho_temporario = os.path.join(pasta_pai, f"{entrada}._casetmp")
        caminho_final = os.path.join(pasta_pai, nome_esperado)
        try:
            os.replace(caminho_atual, caminho_temporario)
            os.replace(caminho_temporario, caminho_final)
            print(f"  [CASING CORRIGIDO] {entrada} -> {nome_esperado}")
        except OSError as erro:
            print(f"  [AVISO] Não foi possível corrigir o casing de {entrada}: {erro}")
        return


def arquivos_iguais(primeiro: str, segundo: str) -> bool:
    """Compara conteúdo sem confiar apenas em tamanho ou data de modificação."""
    if not os.path.isfile(primeiro) or not os.path.isfile(segundo):
        return False
    if os.path.getsize(primeiro) != os.path.getsize(segundo):
        return False

    def calcular_hash(caminho: str) -> bytes:
        resumo = hashlib.sha256()
        with open(caminho, "rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                resumo.update(bloco)
        return resumo.digest()

    return calcular_hash(primeiro) == calcular_hash(segundo)


def sincronizar_espelho(origem: str, destino: str, simular: bool = False) -> None:
    origem = os.path.abspath(origem)
    destino = os.path.abspath(destino)

    if origem == destino:
        raise ValueError("Origem e destino do deploy não podem ser iguais.")
    try:
        destino_dentro_da_origem = os.path.commonpath((origem, destino)) == origem
    except ValueError:
        # Unidades diferentes no Windows (por exemplo, checkout em D: e app em C:).
        destino_dentro_da_origem = False
    if destino_dentro_da_origem:
        raise ValueError("O destino do deploy não pode ficar dentro do checkout de origem.")
    if not os.path.isdir(origem):
        raise FileNotFoundError(f"Checkout de origem não encontrado: {origem}")

    print(
        "Iniciando espelhamento:\n"
        f"  Origem: {origem}\n"
        f"  Destino: {destino}\n"
        f"  Simulação: {simular}"
    )

    if not simular:
        os.makedirs(destino, exist_ok=True)

    arquivos_origem: set[str] = set()
    pastas_origem: set[str] = set()

    for raiz, pastas, arquivos in os.walk(origem):
        relativo_raiz = os.path.relpath(raiz, origem)
        pastas[:] = [
            pasta
            for pasta in pastas
            if not deve_preservar_pasta(
                os.path.join(relativo_raiz, pasta) if relativo_raiz != "." else pasta
            )
        ]

        if relativo_raiz != ".":
            pastas_origem.add(_normalizar(relativo_raiz))

        destino_atual = destino if relativo_raiz == "." else os.path.join(destino, relativo_raiz)
        if not simular:
            os.makedirs(destino_atual, exist_ok=True)
            if relativo_raiz != ".":
                corrigir_casing(os.path.dirname(destino_atual), os.path.basename(destino_atual))

        for arquivo in arquivos:
            relativo_arquivo = (
                arquivo
                if relativo_raiz == "."
                else os.path.normpath(os.path.join(relativo_raiz, arquivo))
            )
            if deve_preservar_arquivo(relativo_arquivo):
                continue

            arquivos_origem.add(_normalizar(relativo_arquivo))
            caminho_origem = os.path.join(raiz, arquivo)
            caminho_destino = os.path.join(destino_atual, arquivo)

            if not simular:
                corrigir_casing(destino_atual, arquivo)

            copiar = not arquivos_iguais(caminho_origem, caminho_destino)

            if copiar:
                print(f"  [COPIAR] {relativo_arquivo}")
                if not simular:
                    shutil.copy2(caminho_origem, caminho_destino)

    if not os.path.isdir(destino):
        print("Espelhamento simulado com sucesso.")
        return

    for raiz, _pastas, arquivos in os.walk(destino, topdown=False):
        relativo_raiz = os.path.relpath(raiz, destino)
        if deve_preservar_pasta(relativo_raiz):
            continue

        for arquivo in arquivos:
            relativo_arquivo = (
                arquivo
                if relativo_raiz == "."
                else os.path.normpath(os.path.join(relativo_raiz, arquivo))
            )
            if deve_preservar_arquivo(relativo_arquivo):
                continue
            if _normalizar(relativo_arquivo) in arquivos_origem:
                continue

            print(f"  [REMOVER OBSOLETO] {relativo_arquivo}")
            if not simular:
                os.remove(os.path.join(raiz, arquivo))

        if relativo_raiz == "." or deve_preservar_pasta(relativo_raiz):
            continue
        if _normalizar(relativo_raiz) in pastas_origem:
            continue
        if not os.listdir(raiz):
            print(f"  [REMOVER DIRETÓRIO VAZIO] {relativo_raiz}")
            if not simular:
                os.rmdir(raiz)

    print("Espelhamento concluído com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincronizador de deploy do Luft-Workspace")
    parser.add_argument("origem", help="Diretório do checkout do runner")
    parser.add_argument("destino", help="Diretório da aplicação no servidor")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem alterar o destino")
    argumentos = parser.parse_args()

    sincronizar_espelho(
        argumentos.origem,
        argumentos.destino,
        simular=argumentos.dry_run,
    )
