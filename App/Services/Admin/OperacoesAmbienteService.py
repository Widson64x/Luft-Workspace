"""Servicos de operacao de ambiente, descoberta de projetos e ciclo de vida.

Este modulo centraliza leitura e atualizacao de variaveis permitidas em
arquivos .env de projetos monitorados, descoberta automatica de caminhos
por ambiente (Windows/Linux) e operacoes de servico.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any
import platform
import re
import shutil
import subprocess


@dataclass(frozen=True)
class VariavelPermitida:
    """Define uma variavel de ambiente elegivel para exibicao/edicao.

    Atributos:
    chave: Nome exato da variavel no arquivo .env.
    descricao: Texto explicativo para exibicao na interface.
    permiteEdicao: Indica se a variavel pode ser alterada pela UI.
    mascarar: Indica se o valor deve ser ocultado na listagem.
    """

    chave: str
    descricao: str
    permiteEdicao: bool = True
    mascarar: bool = False


@dataclass(frozen=True)
class ProjetoOperacao:
    """Define um projeto alvo para operacoes de ambiente.

    Atributos:
    idProjeto: Identificador estavel utilizado na API.
    nomeProjeto: Nome amigavel exibido para administracao.
    caminhoEnv: Caminho absoluto do arquivo .env do projeto.
    variaveisPermitidas: Colecao de variaveis elegiveis para gerenciamento.
    """

    idProjeto: str
    nomeProjeto: str
    caminhoProjeto: Path | None
    caminhoEnv: Path | None
    caminhosVenv: tuple[Path, ...]
    variaveisPermitidas: tuple[VariavelPermitida, ...]


@dataclass(frozen=True)
class ServicoControlavel:
    """Define um servico Windows controlavel pela interface.

    Atributos:
    idServico: Identificador estavel usado na API/UI.
    nomeExibicao: Nome amigavel exibido na interface.
    nomeVariavelServico: Variavel de ambiente que informa o nome do servico.
    descricao: Contexto funcional do servico.
    """

    idServico: str
    nomeExibicao: str
    nomeVariavelServico: str
    descricao: str


class ServicoOperacoesAmbiente:
    """Servico de aplicacao para operacoes administrativas de ambiente."""

    _VARIAVEIS_PADRAO: tuple[VariavelPermitida, ...] = (
        VariavelPermitida("APP_NAME", "Nome da aplicacao no topo do sistema."),
        VariavelPermitida("APP_ENV", "Ambiente atual (development/homologation/production)."),
        VariavelPermitida("HOST", "Host de bind do servidor HTTP."),
        VariavelPermitida("PORT", "Porta de bind do servidor HTTP."),
        VariavelPermitida("ROUTE_PREFIX", "Prefixo de rota aplicado no proxy."),
        VariavelPermitida("SISTEMA_ID", "Identificador do sistema no LuftCore."),
        VariavelPermitida("DEBUG_PERMISSIONS", "Liga logs de diagnostico de permissao."),
        VariavelPermitida("SESSION_COOKIE_NAME", "Nome do cookie de sessao compartilhada."),
        VariavelPermitida("SESSION_COOKIE_PATH", "Path do cookie de sessao."),
        VariavelPermitida("SESSION_COOKIE_DOMAIN", "Dominio compartilhado do cookie de sessao."),
        VariavelPermitida("SESSION_COOKIE_SAMESITE", "Politica SameSite do cookie de sessao."),
        VariavelPermitida("SESSION_COOKIE_SECURE", "Define cookie seguro em conexoes HTTPS."),
        VariavelPermitida("REMEMBER_COOKIE_NAME", "Nome do cookie remember do Flask-Login."),
        VariavelPermitida("PERMANENT_SESSION_LIFETIME_MINUTES", "Tempo de vida da sessao em minutos."),
    )

    _CATALOGO_PROJETOS: tuple[dict[str, Any], ...] = (
        {
            "idProjeto": "workspace",
            "nomeProjeto": "Workspace",
            "nomesDiretorio": ("Workspace",),
            "variavelCaminhoProjeto": "WORKSPACE_PROJECT_DIR",
            "variaveisPermitidas": _VARIAVEIS_PADRAO + (
                VariavelPermitida("LUFT_USAR_PREFIXO_MENSAGENS", "Ativa prefixo no endpoint de mensagens."),
            ),
            "subpastasExtrasVenv": (),
        },
        {
            "idProjeto": "luft-control",
            "nomeProjeto": "Luft-Control",
            "nomesDiretorio": ("Luft-Control",),
            "variavelCaminhoProjeto": "LUFT_CONTROL_PROJECT_DIR",
            "variaveisPermitidas": _VARIAVEIS_PADRAO,
            "subpastasExtrasVenv": (),
        },
        {
            "idProjeto": "luft-connectair",
            "nomeProjeto": "Luft-ConnectAir",
            "nomesDiretorio": ("Luft-ConnectAir",),
            "variavelCaminhoProjeto": "LUFT_CONNECTAIR_PROJECT_DIR",
            "variaveisPermitidas": _VARIAVEIS_PADRAO + (
                VariavelPermitida("AMBIENTE_APP", "Ambiente funcional do ConnectAir."),
                VariavelPermitida("SESSION_TIMEOUT_MINUTES", "Timeout da sessao de usuario em minutos."),
            ),
            "subpastasExtrasVenv": (),
        },
        {
            "idProjeto": "luft-docs",
            "nomeProjeto": "Luft-Docs (Web/API)",
            "nomesDiretorio": ("Luft-Docs",),
            "variavelCaminhoProjeto": "LUFT_DOCS_PROJECT_DIR",
            "variaveisPermitidas": _VARIAVEIS_PADRAO + (
                VariavelPermitida("BASE_PREFIX", "Prefixo base da aplicacao web do Luft-Docs."),
                VariavelPermitida("API_PREFIX", "Prefixo base da API do Luft-Docs."),
                VariavelPermitida("APP_HOST", "Host de bind da API do Luft-Docs."),
                VariavelPermitida("APP_PORT", "Porta de bind da API do Luft-Docs."),
            ),
            "subpastasExtrasVenv": ("Luft-Docs", "Luft-Docs_API"),
        },
        {
            "idProjeto": "luft-integrador",
            "nomeProjeto": "Luft-Integrador",
            "nomesDiretorio": ("Luft-Integrador",),
            "variavelCaminhoProjeto": "LUFT_INTEGRADOR_PROJECT_DIR",
            "variaveisPermitidas": _VARIAVEIS_PADRAO,
            "subpastasExtrasVenv": (),
        },
    )

    _SERVICOS: tuple[ServicoControlavel, ...] = (
        ServicoControlavel(
            idServico="workspace",
            nomeExibicao="Workspace",
            nomeVariavelServico="WORKSPACE_SERVICE_NAME",
            descricao="Servico do Hub central (porta 9010).",
        ),
        ServicoControlavel(
            idServico="luft-control",
            nomeExibicao="Luft-Control",
            nomeVariavelServico="LUFT_CONTROL_SERVICE_NAME",
            descricao="Servico da aplicacao Luft-Control (porta 9002).",
        ),
        ServicoControlavel(
            idServico="luft-connectair",
            nomeExibicao="Luft-ConnectAir",
            nomeVariavelServico="LUFT_CONNECTAIR_SERVICE_NAME",
            descricao="Servico da aplicacao Luft-ConnectAir (porta 9003).",
        ),
        ServicoControlavel(
            idServico="luft-docs-web",
            nomeExibicao="Luft-Docs Web",
            nomeVariavelServico="LUFT_DOCS_WEB_SERVICE_NAME",
            descricao="Servico da aplicacao Luft-Docs web (porta 9000).",
        ),
        ServicoControlavel(
            idServico="luft-docs-api",
            nomeExibicao="Luft-Docs API",
            nomeVariavelServico="LUFT_DOCS_API_SERVICE_NAME",
            descricao="Servico da API Luft-Docs (porta 9001).",
        ),
        ServicoControlavel(
            idServico="luft-integrador",
            nomeExibicao="Luft-Integrador",
            nomeVariavelServico="LUFT_INTEGRADOR_SERVICE_NAME",
            descricao="Servico da aplicacao Luft-Integrador (porta 9005).",
        ),
        ServicoControlavel(
            idServico="nginx",
            nomeExibicao="Nginx",
            nomeVariavelServico="NGINX_SERVICE_NAME",
            descricao="Servico de proxy reverso Nginx.",
        ),
    )

    _PADRAO_CHAVE = re.compile(r"^[A-Z][A-Z0-9_]*$")

    def __init__(self) -> None:
        """Inicializa cache de descoberta dos projetos monitorados."""
        self._projetos_descobertos = self._descobrirProjetos()

    def listarProjetos(self) -> list[dict[str, Any]]:
        """Lista projetos administraveis de ambiente."""
        retorno: list[dict[str, Any]] = []
        for projeto in self._projetos_descobertos:
            retorno.append(
                {
                    "idProjeto": projeto.idProjeto,
                    "nomeProjeto": projeto.nomeProjeto,
                    "caminhoProjeto": str(projeto.caminhoProjeto) if projeto.caminhoProjeto else "",
                    "caminhoEnv": str(projeto.caminhoEnv) if projeto.caminhoEnv else "",
                    "arquivoExiste": bool(projeto.caminhoEnv and projeto.caminhoEnv.exists()),
                    "venvs": [str(caminho) for caminho in projeto.caminhosVenv],
                    "venvEncontrada": len(projeto.caminhosVenv) > 0,
                }
            )
        return retorno

    def listarVariaveisProjeto(self, idProjeto: str) -> list[dict[str, Any]]:
        """Lista variaveis permitidas para um projeto especifico."""
        projeto = self._obterProjeto(idProjeto)
        mapa_env = self._carregarMapaEnv(projeto.caminhoEnv)
        retorno: list[dict[str, Any]] = []

        for variavel in projeto.variaveisPermitidas:
            valor_atual = mapa_env.get(variavel.chave)
            retorno.append(
                {
                    "chave": variavel.chave,
                    "descricao": variavel.descricao,
                    "permiteEdicao": variavel.permiteEdicao,
                    "mascarar": variavel.mascarar,
                    "valor": self._mascararValor(valor_atual) if variavel.mascarar else (valor_atual or ""),
                    "valorDefinido": valor_atual is not None,
                }
            )

        return retorno

    def atualizarVariavelProjeto(self, idProjeto: str, chave: str, valor: str) -> None:
        """Atualiza variavel permitida em arquivo .env do projeto."""
        projeto = self._obterProjeto(idProjeto)
        definicao_variavel = self._obterVariavelPermitida(projeto, chave)

        if not definicao_variavel.permiteEdicao:
            raise ValueError("A variavel solicitada esta bloqueada para edicao.")

        if not self._PADRAO_CHAVE.match(chave):
            raise ValueError("A chave informada possui formato invalido.")

        valor_normalizado = "" if valor is None else str(valor).strip()
        if not projeto.caminhoEnv:
            raise ValueError("Arquivo .env nao localizado para o projeto selecionado.")
        self._atualizarArquivoEnv(projeto.caminhoEnv, chave, valor_normalizado)

    def listarServicos(self) -> list[dict[str, Any]]:
        """Lista servicos com status operacional atual."""
        retorno: list[dict[str, Any]] = []

        for servico in self._SERVICOS:
            nome_servico_real = self._resolverNomeServico(servico)
            if not nome_servico_real:
                retorno.append(
                    {
                        "idServico": servico.idServico,
                        "nomeExibicao": servico.nomeExibicao,
                        "nomeServico": "",
                        "status": "NAO_CONFIGURADO",
                        "descricao": servico.descricao,
                        "comandos": [],
                        "detalhe": f"Variavel {servico.nomeVariavelServico} nao configurada.",
                    }
                )
                continue

            status = self._consultarStatusServico(nome_servico_real)
            retorno.append(
                {
                    "idServico": servico.idServico,
                    "nomeExibicao": servico.nomeExibicao,
                    "nomeServico": nome_servico_real,
                    "status": status,
                    "descricao": servico.descricao,
                    "comandos": self._definirComandosDisponiveis(status),
                    "detalhe": f"Servico configurado como {nome_servico_real}.",
                }
            )

        return retorno

    def executarAcaoServico(self, idServico: str, acao: str) -> dict[str, Any]:
        """Executa uma ação de ciclo de vida sobre um serviço configurado.

        Parametros:
        idServico: Identificador lógico do serviço.
        acao: Ação desejada (`iniciar`, `parar` ou `reiniciar`).

        Retorno:
        dict[str, Any]: Resultado operacional com histórico e status final.
        """
        acao_normalizada = str(acao or "").strip().lower()
        if acao_normalizada not in {"iniciar", "parar", "reiniciar"}:
            raise ValueError("A ação informada é inválida.")

        definicao_servico = self._obterServicoControlavel(idServico)
        nome_servico = self._resolverNomeServico(definicao_servico)
        if not nome_servico:
            raise ValueError(f"A variável {definicao_servico.nomeVariavelServico} não está configurada.")

        comandos = self._montarComandosServico(nome_servico, acao_normalizada)
        historico: list[dict[str, Any]] = []
        for comando in comandos:
            historico.append(self._executarComandoServico(comando))

        status_final = self._consultarStatusServico(nome_servico)
        return {
            "idServico": definicao_servico.idServico,
            "nomeServico": nome_servico,
            "acao": acao_normalizada,
            "historico": historico,
            "statusFinal": status_final,
        }

    def _descobrirProjetos(self) -> tuple[ProjetoOperacao, ...]:
        """Descobre os projetos administráveis com base em roots configuradas e overrides."""
        projetos: list[ProjetoOperacao] = []

        for definicao in self._CATALOGO_PROJETOS:
            caminho_projeto = self._resolverCaminhoProjeto(definicao)
            caminho_env = (caminho_projeto / ".env") if caminho_projeto else None
            caminhos_venv = self._localizarVenvsProjeto(caminho_projeto, definicao.get("subpastasExtrasVenv", ()))
            projetos.append(
                ProjetoOperacao(
                    idProjeto=str(definicao["idProjeto"]),
                    nomeProjeto=str(definicao["nomeProjeto"]),
                    caminhoProjeto=caminho_projeto,
                    caminhoEnv=caminho_env,
                    caminhosVenv=caminhos_venv,
                    variaveisPermitidas=tuple(definicao.get("variaveisPermitidas", ())),
                )
            )

        return tuple(projetos)

    def _obterRaizesBuscaProjetos(self) -> tuple[Path, ...]:
        """Monta a lista de raízes candidatas para descoberta automática de projetos."""
        candidatos: list[Path] = []
        bruto_roots = str(os.getenv("OPERACOES_SCAN_ROOTS") or "").strip()
        if bruto_roots:
            for trecho in re.split(r"[;|]", bruto_roots):
                caminho = Path(trecho.strip()).expanduser()
                if trecho.strip():
                    candidatos.append(caminho)

        diretorio_atual = Path(__file__).resolve()
        candidatos.extend(
            [
                diretorio_atual.parents[3],
                diretorio_atual.parents[4] / "Projetos",
                diretorio_atual.parents[4] / "Aplicacoes",
                Path("C:/Applications/Python/Projetos"),
                Path("C:/Applications/Python/Aplicacoes"),
            ]
        )

        unicos: list[Path] = []
        vistos: set[str] = set()
        for caminho in candidatos:
            chave = str(caminho).strip().lower()
            if not chave or chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(caminho)

        return tuple(unicos)

    def _resolverCaminhoProjeto(self, definicao: dict[str, Any]) -> Path | None:
        """Resolve o caminho físico de um projeto via override explícito ou descoberta."""
        variavel_caminho = str(definicao.get("variavelCaminhoProjeto") or "").strip()
        caminho_override = str(os.getenv(variavel_caminho) or "").strip()
        if caminho_override:
            caminho_resolvido = Path(caminho_override).expanduser()
            if caminho_resolvido.exists():
                return caminho_resolvido

        nomes_diretorio = tuple(str(item).strip() for item in definicao.get("nomesDiretorio", ()) if str(item).strip())
        for raiz in self._obterRaizesBuscaProjetos():
            if not raiz.exists():
                continue
            for nome_diretorio in nomes_diretorio:
                candidato_direto = raiz / nome_diretorio
                if candidato_direto.exists():
                    return candidato_direto

                try:
                    for caminho_encontrado in raiz.rglob(nome_diretorio):
                        if caminho_encontrado.is_dir():
                            return caminho_encontrado
                except OSError:
                    continue

        return None

    def _localizarVenvsProjeto(self, caminhoProjeto: Path | None, subpastasExtrasVenv: tuple[str, ...] | list[str]) -> tuple[Path, ...]:
        """Localiza virtualenvs associados ao projeto principal e submódulos específicos."""
        if not caminhoProjeto:
            return tuple()

        candidatos = [caminhoProjeto / ".venv", caminhoProjeto / "venv"]
        for subpasta in subpastasExtrasVenv:
            candidatos.append(caminhoProjeto / subpasta / ".venv")
            candidatos.append(caminhoProjeto / subpasta / "venv")

        venvs: list[Path] = []
        vistos: set[str] = set()
        for candidato in candidatos:
            chave = str(candidato).lower()
            if chave in vistos:
                continue
            vistos.add(chave)
            if candidato.exists() and candidato.is_dir():
                venvs.append(candidato)

        return tuple(venvs)

    def _obterProjeto(self, idProjeto: str) -> ProjetoOperacao:
        """Retorna a definição de projeto correspondente ao identificador informado."""
        id_normalizado = str(idProjeto or "").strip().lower()
        for projeto in self._projetos_descobertos:
            if projeto.idProjeto.lower() == id_normalizado:
                return projeto
        raise ValueError("Projeto informado não foi encontrado.")

    def _obterServicoControlavel(self, idServico: str) -> ServicoControlavel:
        """Retorna a definição de serviço correspondente ao identificador lógico."""
        id_normalizado = str(idServico or "").strip().lower()
        for servico in self._SERVICOS:
            if servico.idServico.lower() == id_normalizado:
                return servico
        raise ValueError("Serviço informado não foi encontrado.")

    def _obterVariavelPermitida(self, projeto: ProjetoOperacao, chave: str) -> VariavelPermitida:
        """Valida se a variável pertence à whitelist do projeto selecionado."""
        chave_normalizada = str(chave or "").strip().upper()
        for variavel in projeto.variaveisPermitidas:
            if variavel.chave.upper() == chave_normalizada:
                return variavel
        raise ValueError("A variável informada não está permitida para este projeto.")

    def _carregarMapaEnv(self, caminhoEnv: Path | None) -> dict[str, str]:
        """Lê o arquivo `.env` do projeto em um mapa chave/valor simples."""
        if not caminhoEnv or not caminhoEnv.exists():
            return {}

        mapa: dict[str, str] = {}
        for linha in caminhoEnv.read_text(encoding="utf-8", errors="ignore").splitlines():
            linha_limpa = linha.strip()
            if not linha_limpa or linha_limpa.startswith("#") or "=" not in linha_limpa:
                continue

            chave, valor = linha_limpa.split("=", 1)
            mapa[chave.strip()] = valor.strip().strip('"').strip("'")

        return mapa

    def _atualizarArquivoEnv(self, caminhoEnv: Path, chave: str, valor: str) -> None:
        """Atualiza ou cria uma chave em arquivo `.env`, preservando as demais linhas."""
        caminhoEnv.parent.mkdir(parents=True, exist_ok=True)
        linhas = []
        if caminhoEnv.exists():
            linhas = caminhoEnv.read_text(encoding="utf-8", errors="ignore").splitlines()

        chave_normalizada = chave.strip()
        valor_serializado = valor.strip()
        nova_linha = f"{chave_normalizada}={valor_serializado}"
        atualizado = False
        linhas_saida: list[str] = []

        for linha in linhas:
            if linha.strip().startswith(f"{chave_normalizada}="):
                linhas_saida.append(nova_linha)
                atualizado = True
            else:
                linhas_saida.append(linha)

        if not atualizado:
            if linhas_saida and linhas_saida[-1].strip():
                linhas_saida.append("")
            linhas_saida.append(nova_linha)

        caminhoEnv.write_text("\n".join(linhas_saida) + "\n", encoding="utf-8")

    def _mascararValor(self, valor: str | None) -> str:
        """Mascara parcialmente valores sensíveis para exibição em listagem."""
        if not valor:
            return ""
        if len(valor) <= 4:
            return "*" * len(valor)
        return f"{'*' * max(len(valor) - 4, 4)}{valor[-4:]}"

    def _resolverNomeServico(self, servico: ServicoControlavel) -> str:
        """Resolve o nome técnico do serviço via variável de ambiente dedicada."""
        return str(os.getenv(servico.nomeVariavelServico) or "").strip()

    def _consultarStatusServico(self, nomeServico: str) -> str:
        """Consulta o status atual do serviço no sistema operacional hospedeiro."""
        nome_plataforma = platform.system().lower()
        try:
            if nome_plataforma == "windows":
                resultado = subprocess.run(
                    ["sc", "query", nomeServico],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    check=False,
                )
                saida = f"{resultado.stdout}\n{resultado.stderr}".upper()
                if "FAILED 1060" in saida or "DOES NOT EXIST" in saida:
                    return "NAO_ENCONTRADO"
                if "RUNNING" in saida:
                    return "RUNNING"
                if "STOPPED" in saida:
                    return "STOPPED"
                return "DESCONHECIDO"

            resultado = subprocess.run(
                ["systemctl", "is-active", nomeServico],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False,
            )
            saida = (resultado.stdout or resultado.stderr or "").strip().lower()
            if saida == "active":
                return "RUNNING"
            if saida in {"inactive", "failed", "deactivating"}:
                return "STOPPED"
            if saida == "unknown":
                return "NAO_ENCONTRADO"
            return "DESCONHECIDO"
        except FileNotFoundError:
            return "DESCONHECIDO"

    def _definirComandosDisponiveis(self, status: str) -> list[str]:
        """Lista comandos operacionais disponíveis para o status atual."""
        if status == "RUNNING":
            return ["parar", "reiniciar"]
        if status == "STOPPED":
            return ["iniciar"]
        if status == "NAO_CONFIGURADO":
            return []
        return ["iniciar", "parar", "reiniciar"]

    def _montarComandosServico(self, nomeServico: str, acao: str) -> list[list[str]]:
        """Monta os comandos nativos para executar a ação solicitada sobre o serviço."""
        nome_plataforma = platform.system().lower()
        if nome_plataforma == "windows":
            if acao == "reiniciar":
                return [["sc", "stop", nomeServico], ["sc", "start", nomeServico]]
            verbo = {"iniciar": "start", "parar": "stop"}[acao]
            return [["sc", verbo, nomeServico]]

        if acao == "reiniciar":
            return [["systemctl", "restart", nomeServico]]
        verbo = {"iniciar": "start", "parar": "stop"}[acao]
        return [["systemctl", verbo, nomeServico]]

    def _executarComandoServico(self, comando: list[str]) -> dict[str, str | int]:
        """Executa um comando de controle de serviço e captura saída detalhada."""
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        return {
            "comando": " ".join(comando),
            "status": "SUCESSO" if resultado.returncode == 0 else "ERRO",
            "codigoRetorno": int(resultado.returncode),
            "saida": (resultado.stdout or resultado.stderr or "").strip(),
        }
