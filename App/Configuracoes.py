"""
Parâmetros próprios do Luft-Workspace.

Bancos, Vault, sessão, LDAP e e-mail pertencem ao LuftBase (variáveis LUFT_* e segredos do
Vault). Aqui ficam apenas diretórios e parâmetros de execução particulares desta aplicação.

Padrão Luft: a configuração comum vem primeiro; o que é particular do sistema, no fim.
"""

import os
import platform

from dotenv import load_dotenv

load_dotenv()

NOME_APLICACAO = "Luft-Workspace"


def _ObterBoolEnv(NomeVariavel, ValorPadrao=False):
    Valor = os.getenv(NomeVariavel)
    if Valor is None:
        return ValorPadrao
    return Valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


class ConfiguracaoBase:
    APP_NAME = os.getenv("APP_NAME", NOME_APLICACAO)

    AMBIENTE = (os.getenv("LUFT_AMBIENTE") or "desenvolvimento").strip().lower()
    DEBUG = AMBIENTE not in {"producao", "production", "prod", "prd"}

    # Raiz do projeto (pai do pacote App): Data/ e Logs/ ficam fora do código.
    DIR_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_UPLOADS = os.path.join(DIR_BASE, "Data", "Uploads")
    DIR_TEMP = os.path.join(DIR_BASE, "Data", "Temp")
    DIR_LOGS = os.path.join(DIR_BASE, "Logs")

    # Mostra o SQL emitido pelo SQLAlchemy (diagnóstico)
    MOSTRAR_LOGS_DB = _ObterBoolEnv("DB_CONNECT_LOGS", False)


# ========================================================================================
# Particularidades do Luft-Workspace
# ========================================================================================

class ConfiguracaoWorkspace(ConfiguracaoBase):
    """O Hub não tem parâmetros além dos padrão."""


ConfiguracaoAtual = ConfiguracaoWorkspace()


def NormalizarNomesServicosWindows():
    """Converte nomes systemd conhecidos para seus equivalentes no SCM do Windows."""
    if platform.system().lower() != "windows":
        return
    nomes_padrao = {
        "LUFT_WORKSPACE_SERVICE_NAME": "Luft-Workspace",
        "LUFT_CONTROL_SERVICE_NAME": "Luft-Control",
        "LUFT_CONNECTAIR_SERVICE_NAME": "Luft-ConnectAir",
        "LUFT_INTEGRADOR_SERVICE_NAME": "Luft-Integrador",
        "NGINX_SERVICE_NAME": "nginx",
    }
    for variavel, nome_padrao in nomes_padrao.items():
        configurado = (os.getenv(variavel) or "").strip()
        if not configurado or configurado.lower().endswith(".service"):
            os.environ[variavel] = nome_padrao


NormalizarNomesServicosWindows()

