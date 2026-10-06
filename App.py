"""Desenvolvimento do Luft-Workspace: `python App.py` (depurador e recarga automatica).

Em producao use o Wsgi.py. Host e porta vem do .env (HOST/PORT ou LUFT_SERVIDOR_*).
"""

from luftbase.servidor import executar_desenvolvimento

if __name__ == "__main__":
    executar_desenvolvimento("App:CriarApp")
