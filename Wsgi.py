"""Producao do Luft-Workspace: servidor padrao do LuftBase (Waitress).

Host, porta, prefixo e threads vem do .env (LUFT_SERVIDOR_* ou HOST/PORT/ROUTE_PREFIX).
Em desenvolvimento use o App.py.
"""

from luftbase.servidor import executar

if __name__ == "__main__":
    executar("App:CriarApp")
