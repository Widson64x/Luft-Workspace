"""Serviços da central de orquestração de bancos de dados.

Este modulo implementa o motor administrativo da central de orquestração
de bancos de dados, permitindo conexões reutilizáveis, preview de consultas,
transformação de campos, escrita dinâmica no destino e trilha completa
de execução.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import logging
import os
import re
import traceback
from typing import Any

from luftcore.extensions.sqlalchemy_extension import SqlAlchemyExtension
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, Numeric, String, Table, Text, event, inspect, text
from sqlalchemy.engine import Engine

from App.Db.Connections import GetSqlServerEngine
from App.Models.OrquestracaoBancoModel import (
    TbBancoConexao,
    TbBancoExecucao,
    TbBancoExecucaoLog,
    TbBancoTarefa,
    TbBancoTarefaCampo,
)

logger = logging.getLogger(__name__)

FUSO_BRASILIA = timezone(timedelta(hours=-3))


class EstruturaOrquestracaoBancoNaoConfiguradaError(RuntimeError):
    """Indica ausência da estrutura SQL obrigatória da central de orquestração."""


class ServicoOrquestracaoBanco:
    """Serviço de aplicação para tarefas e orquestração de bancos de dados."""

    @staticmethod
    def _obterAgoraBrasilia() -> datetime:
        """Retorna a data e hora atual no fuso horario de Brasilia (UTC-3) sem tzinfo para persistencia no SQL Server."""
        return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)

    _TABELA_CONEXAO = TbBancoConexao.NOME_TABELA_QUALIFICADA
    _TABELA_WORKFLOW = TbBancoTarefa.NOME_TABELA_QUALIFICADA
    _TABELA_CAMPO = TbBancoTarefaCampo.NOME_TABELA_QUALIFICADA
    _TABELA_EXECUCAO = TbBancoExecucao.NOME_TABELA_QUALIFICADA
    _TABELA_EXECUCAO_LOG = TbBancoExecucaoLog.NOME_TABELA_QUALIFICADA

    _TIPOS_BANCO = {
        "MSSQL": "mssql",
        "ORACLE": "oracle",
        "POSTGRESQL": "postgresql",
    }
    _TIPOS_TRANSFORMACAO = {
        "DIRETO",
        "TEXTO_MAIUSCULO",
        "TEXTO_MINUSCULO",
        "TRIM",
        "INTEGER",
        "DECIMAL",
        "BOOLEANO",
        "DATA_ISO",
        "TEMPLATE",
        "VALOR_PADRAO",
        "AUTO_SEQUENCIAL",
    }
    _TIPOS_AGENDAMENTO = {"MANUAL", "INTERVALO", "DIARIO", "DATA_ESPECIFICA"}
    _MODOS_DESTINO = {"TABELA_ALVO", "QUERY_DESTINO"}
    _MODOS_CARGA = {"APPEND", "TRUNCATE_APPEND"}
    _PADRAO_HORARIO = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    _PADRAO_IDENTIFICADOR = re.compile(r"^[A-Za-z0-9_\.\[\]\-]+$")

    def obterDiagnosticoEstrutura(self) -> dict[str, Any]:
        """Consulta se a estrutura SQL da central ja foi provisionada.

        Retorno:
        dict[str, Any]: Estado consolidado das tabelas obrigatorias.
        """
        consulta = text(
            f"""
            SELECT
                CASE WHEN OBJECT_ID('{self._TABELA_CONEXAO}', 'U') IS NOT NULL THEN 1 ELSE 0 END AS TabelaConexaoExiste,
                CASE WHEN OBJECT_ID('{self._TABELA_WORKFLOW}', 'U') IS NOT NULL THEN 1 ELSE 0 END AS TabelaWorkflowExiste,
                CASE WHEN OBJECT_ID('{self._TABELA_CAMPO}', 'U') IS NOT NULL THEN 1 ELSE 0 END AS TabelaCampoExiste,
                CASE WHEN OBJECT_ID('{self._TABELA_EXECUCAO}', 'U') IS NOT NULL THEN 1 ELSE 0 END AS TabelaExecucaoExiste,
                CASE WHEN OBJECT_ID('{self._TABELA_EXECUCAO_LOG}', 'U') IS NOT NULL THEN 1 ELSE 0 END AS TabelaExecucaoLogExiste
            """
        )

        with GetSqlServerEngine().connect() as conexao:
            linha = conexao.execute(consulta).mappings().first()
            conexao.rollback()

        diagnostico = {
            "tabelaConexaoExiste": bool(linha["TabelaConexaoExiste"]) if linha else False,
            "tabelaWorkflowExiste": bool(linha["TabelaWorkflowExiste"]) if linha else False,
            "tabelaCampoExiste": bool(linha["TabelaCampoExiste"]) if linha else False,
            "tabelaExecucaoExiste": bool(linha["TabelaExecucaoExiste"]) if linha else False,
            "tabelaExecucaoLogExiste": bool(linha["TabelaExecucaoLogExiste"]) if linha else False,
        }
        diagnostico["estruturaPronta"] = all(diagnostico.values())
        diagnostico["mensagem"] = (
            "Estrutura SQL da central de orquestração de bancos ainda não foi criada."
            if not diagnostico["estruturaPronta"]
            else "Estrutura SQL disponível."
        )
        return diagnostico

    def garantirEstruturaDisponivel(self) -> None:
        """Valida se a estrutura SQL obrigatoria esta disponivel e aplica migracoes."""
        diagnostico = self.obterDiagnosticoEstrutura()
        if not diagnostico["estruturaPronta"]:
            raise EstruturaOrquestracaoBancoNaoConfiguradaError(diagnostico["mensagem"])
        
        migracao_chave = text(
            f"""
            IF COL_LENGTH('{self._TABELA_CAMPO}', 'E_Chave') IS NULL
            BEGIN
                ALTER TABLE {self._TABELA_CAMPO} ADD E_Chave BIT NOT NULL CONSTRAINT DF_Tb_BancoTarefaCampo_EChave DEFAULT (0);
                ALTER TABLE {self._TABELA_CAMPO} ADD Ultimo_Valor_Sequencial INT NULL CONSTRAINT DF_Tb_BancoTarefaCampo_UltimoSeq DEFAULT (0);
            END
            """
        )
        with GetSqlServerEngine().begin() as conexao:
            conexao.execute(migracao_chave)

    def listarConexoes(self) -> list[dict[str, Any]]:
        """Lista conexoes reutilizaveis cadastradas na central."""
        self.garantirEstruturaDisponivel()

        consulta = text(
            f"""
            SELECT
                Id_Conexao,
                Nome_Conexao,
                Tipo_Banco,
                Caminho_Segredo_Vault,
                Driver_Banco,
                Schema_Padrao,
                Parametros_Conexao_Json,
                Ativo,
                Observacao,
                Atualizado_Em
            FROM {self._TABELA_CONEXAO}
            ORDER BY Nome_Conexao ASC
            """
        )

        with GetSqlServerEngine().connect() as conexao:
            linhas = conexao.execute(consulta).mappings().all()
            conexao.rollback()

        retorno: list[dict[str, Any]] = []
        for linha in linhas:
            retorno.append(
                {
                    "idConexao": int(linha["Id_Conexao"]),
                    "nomeConexao": linha["Nome_Conexao"],
                    "tipoBanco": linha["Tipo_Banco"],
                    "caminhoSegredoVault": linha["Caminho_Segredo_Vault"],
                    "driverBanco": linha["Driver_Banco"] or "",
                    "schemaPadrao": linha["Schema_Padrao"] or "",
                    "parametrosConexao": self._desserializarJson(linha["Parametros_Conexao_Json"]),
                    "ativo": bool(linha["Ativo"]),
                    "observacao": linha["Observacao"] or "",
                    "atualizadoEm": self._formatarData(linha["Atualizado_Em"]),
                }
            )

        return retorno

    def listarProcedimentos(self) -> list[dict[str, Any]]:
        """Lista tarefas de orquestração configuradas."""
        self.garantirEstruturaDisponivel()

        consulta = text(
            f"""
            SELECT
                wf.Id_Workflow,
                wf.Nome_Workflow,
                wf.Descricao_Workflow,
                wf.Modo_Destino,
                wf.Query_Destino,
                wf.Schema_Destino,
                wf.Tabela_Destino,
                wf.Modo_Carga,
                wf.Criar_Tabela_Automaticamente,
                wf.Tipo_Agendamento,
                wf.Configuracao_Agendamento,
                wf.Intervalo_Minutos,
                wf.Timeout_Segundos,
                wf.Lote_Linhas,
                wf.Ativo,
                wf.Ultima_Execucao_Em,
                wf.Proxima_Execucao_Em,
                wf.Duracao_Ultima_Execucao_Ms,
                wf.Status_Ultima_Execucao,
                wf.Total_Linhas_Ultima_Execucao,
                wf.Mensagem_Ultima_Execucao,
                co.Nome_Conexao AS Nome_Conexao_Origem,
                cd.Nome_Conexao AS Nome_Conexao_Destino
            FROM {self._TABELA_WORKFLOW} wf
            INNER JOIN {self._TABELA_CONEXAO} co ON co.Id_Conexao = wf.Id_Conexao_Origem
            INNER JOIN {self._TABELA_CONEXAO} cd ON cd.Id_Conexao = wf.Id_Conexao_Destino
            ORDER BY wf.Nome_Workflow ASC
            """
        )

        with GetSqlServerEngine().connect() as conexao:
            linhas = conexao.execute(consulta).mappings().all()
            conexao.rollback()

        retorno: list[dict[str, Any]] = []
        for linha in linhas:
            configuracao_agendamento = self._desserializarJson(linha["Configuracao_Agendamento"])
            retorno.append(
                {
                    "idProcedimento": int(linha["Id_Workflow"]),
                    "nomeProcedimento": linha["Nome_Workflow"],
                    "descricaoProcedimento": linha["Descricao_Workflow"] or "",
                    "nomeConexaoOrigem": linha["Nome_Conexao_Origem"],
                    "nomeConexaoDestino": linha["Nome_Conexao_Destino"],
                    "modoDestino": linha["Modo_Destino"],
                    "queryDestino": linha["Query_Destino"] or "",
                    "schemaDestino": linha["Schema_Destino"] or "",
                    "tabelaDestino": linha["Tabela_Destino"] or "",
                    "modoCarga": linha["Modo_Carga"],
                    "criarTabelaAutomaticamente": bool(linha["Criar_Tabela_Automaticamente"]),
                    "tipoAgendamento": linha["Tipo_Agendamento"],
                    "configuracaoAgendamento": configuracao_agendamento,
                    "descricaoAgendamento": self._descreverAgendamento(
                        linha["Tipo_Agendamento"],
                        configuracao_agendamento,
                        linha["Intervalo_Minutos"],
                    ),
                    "intervaloMinutos": linha["Intervalo_Minutos"],
                    "timeoutSegundos": int(linha["Timeout_Segundos"]),
                    "loteLinhas": int(linha["Lote_Linhas"]),
                    "ativo": bool(linha["Ativo"]),
                    "ultimaExecucaoEm": self._formatarData(linha["Ultima_Execucao_Em"]),
                    "proximaExecucaoEm": self._formatarData(linha["Proxima_Execucao_Em"]),
                    "duracaoUltimaExecucaoMs": linha["Duracao_Ultima_Execucao_Ms"] or 0,
                    "statusUltimaExecucao": linha["Status_Ultima_Execucao"] or "NUNCA_EXECUTADO",
                    "totalLinhasUltimaExecucao": linha["Total_Linhas_Ultima_Execucao"] or 0,
                    "mensagemUltimaExecucao": linha["Mensagem_Ultima_Execucao"] or "",
                }
            )

        return retorno

    def obterDetalheProcedimento(self, idProcedimento: int) -> dict[str, Any]:
        """Obtem configuracao completa de uma tarefa para edicao."""
        self.garantirEstruturaDisponivel()

        consulta = text(
            f"""
            SELECT
                Id_Workflow,
                Nome_Workflow,
                Descricao_Workflow,
                Id_Conexao_Origem,
                Id_Conexao_Destino,
                Query_Origem,
                Modo_Destino,
                Query_Destino,
                Schema_Destino,
                Tabela_Destino,
                Modo_Carga,
                Criar_Tabela_Automaticamente,
                Tipo_Agendamento,
                Configuracao_Agendamento,
                Intervalo_Minutos,
                Timeout_Segundos,
                Lote_Linhas,
                Ativo
            FROM {self._TABELA_WORKFLOW}
            WHERE Id_Workflow = :idProcedimento
            """
        )

        with GetSqlServerEngine().connect() as conexao:
            linha = conexao.execute(consulta, {"idProcedimento": int(idProcedimento)}).mappings().first()
            conexao.rollback()

        if not linha:
            raise ValueError("Tarefa informada nao foi encontrada.")

        configuracao_agendamento = self._desserializarJson(linha["Configuracao_Agendamento"])
        campos = self._listarCamposWorkflow(int(idProcedimento))

        return {
            "idProcedimento": int(linha["Id_Workflow"]),
            "nomeProcedimento": linha["Nome_Workflow"],
            "descricaoProcedimento": linha["Descricao_Workflow"] or "",
            "idConexaoOrigem": int(linha["Id_Conexao_Origem"]),
            "idConexaoDestino": int(linha["Id_Conexao_Destino"]),
            "origemQuery": linha["Query_Origem"],
            "modoDestino": linha["Modo_Destino"],
            "queryDestino": linha["Query_Destino"] or "",
            "schemaDestino": linha["Schema_Destino"] or "",
            "tabelaDestino": linha["Tabela_Destino"] or "",
            "modoCarga": linha["Modo_Carga"],
            "criarTabelaAutomaticamente": bool(linha["Criar_Tabela_Automaticamente"]),
            "tipoAgendamento": linha["Tipo_Agendamento"],
            "configuracaoAgendamento": configuracao_agendamento,
            "intervaloMinutos": linha["Intervalo_Minutos"],
            "horarioExecucao": configuracao_agendamento.get("horarioExecucao") or "",
            "dataExecucaoEspecifica": configuracao_agendamento.get("dataExecucaoEspecifica") or "",
            "timeoutSegundos": int(linha["Timeout_Segundos"]),
            "loteLinhas": int(linha["Lote_Linhas"]),
            "ativo": bool(linha["Ativo"]),
            "mapaCampos": campos,
        }

    def listarHistoricoExecucao(self, idProcedimento: int, limite: int = 30) -> list[dict[str, Any]]:
        """Lista historico resumido de execucoes da tarefa."""
        self.garantirEstruturaDisponivel()

        consulta = text(
            f"""
            SELECT TOP (:limite)
                Id_Execucao,
                Data_Inicio,
                Data_Fim,
                Duracao_Ms,
                Status_Execucao,
                Total_Linhas_Origem,
                Total_Linhas_Processadas,
                Total_Linhas_Escritas,
                Mensagem_Resumo,
                Executado_Por
            FROM {self._TABELA_EXECUCAO}
            WHERE Id_Workflow = :idProcedimento
            ORDER BY Id_Execucao DESC
            """
        )

        with GetSqlServerEngine().connect() as conexao:
            linhas = conexao.execute(
                consulta,
                {"idProcedimento": int(idProcedimento), "limite": int(max(limite, 1))},
            ).mappings().all()
            conexao.rollback()

        retorno: list[dict[str, Any]] = []
        for linha in linhas:
            retorno.append(
                {
                    "idExecucao": int(linha["Id_Execucao"]),
                    "dataInicio": self._formatarData(linha["Data_Inicio"]),
                    "dataFim": self._formatarData(linha["Data_Fim"]),
                    "duracaoMs": linha["Duracao_Ms"] or 0,
                    "statusExecucao": linha["Status_Execucao"],
                    "totalLinhasOrigem": linha["Total_Linhas_Origem"] or 0,
                    "totalLinhasProcessadas": linha["Total_Linhas_Processadas"] or 0,
                    "totalLinhasEscritas": linha["Total_Linhas_Escritas"] or 0,
                    "mensagem": linha["Mensagem_Resumo"] or "",
                    "executadoPor": linha["Executado_Por"] or "",
                }
            )
        return retorno

    def testarConexaoPayload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Testa o acesso ao banco via Vault usando os parametros informados antes de permitir salvar."""
        tipo_banco = str(payload.get("tipoBanco") or "").strip().upper()
        caminho_segredo_vault = str(payload.get("caminhoSegredoVault") or "").strip()
        driver_banco = str(payload.get("driverBanco") or "").strip() or None
        parametros_brutos = payload.get("parametrosConexao")

        if isinstance(parametros_brutos, str):
            try:
                parametros_conexao = json.loads(parametros_brutos) if parametros_brutos.strip() else {}
            except Exception as e:
                raise ValueError("Os parametros adicionais precisam estar em JSON valido.") from e
        elif isinstance(parametros_brutos, dict):
            parametros_conexao = parametros_brutos
        else:
            parametros_conexao = {}

        if tipo_banco not in self._TIPOS_BANCO:
            raise ValueError("Tipo de banco invalido para a conexao.")
        if not caminho_segredo_vault:
            raise ValueError("Informe o caminho do segredo no Vault.")

        tipo_banco_extensao = self._TIPOS_BANCO[tipo_banco]
        argumentos_extensao: dict[str, Any] = {
            "vault_addr": os.getenv("VAULT_ADDR"),
            "vault_token_criptografado": os.getenv("VAULT_TOKEN"),
            "token_acesso": os.getenv("TOKEN_ACESSO"),
            "caminho_segredo": caminho_segredo_vault,
            "tipo_banco": tipo_banco_extensao,
        }

        if not driver_banco:
            if tipo_banco == "MSSQL":
                driver_banco = os.getenv("DB_DRIVER") or os.getenv("SQLDB_DRIVER") or "ODBC Driver 17 for SQL Server"
            elif tipo_banco == "ORACLE":
                driver_banco = "oracledb"

        if driver_banco:
            argumentos_extensao["driver_banco"] = driver_banco

        if tipo_banco == "MSSQL" and not parametros_conexao:
            parametros_conexao = {"TrustServerCertificate": os.getenv("SQLDB_TRUST_SERVER_CERTIFICATE", "yes")}

        if tipo_banco != "MSSQL" and parametros_conexao:
            parametros_conexao = {
                k: v for k, v in parametros_conexao.items()
                if k.lower() not in {"trustservercertificate", "trust_server_certificate"}
            }

        if parametros_conexao:
            argumentos_extensao["parametros_conexao"] = parametros_conexao

        try:
            extensao = SqlAlchemyExtension(**argumentos_extensao)
            engine = extensao.obter_engine()

            if tipo_banco == "ORACLE":
                @event.listens_for(engine, "do_connect")
                def _substituir_sid_por_service_name(dialect, conn_rec, cargs, cparams):
                    dsn = cparams.get("dsn")
                    if isinstance(dsn, str) and "(CONNECT_DATA=(SID=" in dsn:
                        cparams["dsn"] = dsn.replace("(CONNECT_DATA=(SID=", "(CONNECT_DATA=(SERVICE_NAME=")

            with engine.connect() as conexao:
                query_teste = text("SELECT 1 FROM DUAL") if tipo_banco == "ORACLE" else text("SELECT 1")
                conexao.execute(query_teste).scalar()
            return {"sucesso": True, "mensagem": "Conexao testada com sucesso via Vault!"}
        except Exception as erro:
            mensagem_erro = str(erro)
            raise ValueError(f"Falha ao conectar no banco via Vault: {mensagem_erro}") from erro

    def salvarConexao(self, payload: dict[str, Any], usuarioAtual: str) -> int:
        """Cria ou atualiza uma conexao reutilizavel apos validar obrigatoriamente a conectividade."""
        self.garantirEstruturaDisponivel()

        self.testarConexaoPayload(payload)

        id_conexao = int(payload.get("idConexao") or 0)
        nome_conexao = str(payload.get("nomeConexao") or "").strip()
        tipo_banco = str(payload.get("tipoBanco") or "").strip().upper()
        caminho_segredo_vault = str(payload.get("caminhoSegredoVault") or "").strip()
        driver_banco = str(payload.get("driverBanco") or "").strip() or None
        schema_padrao = str(payload.get("schemaPadrao") or "").strip() or None
        parametros_conexao = self._serializarJson(payload.get("parametrosConexao") or {})
        ativo = bool(payload.get("ativo", True))
        observacao = str(payload.get("observacao") or "").strip() or None

        if not nome_conexao:
            raise ValueError("Informe o nome da conexao.")
        if tipo_banco not in self._TIPOS_BANCO:
            raise ValueError("Tipo de banco invalido para a conexao.")
        if not caminho_segredo_vault:
            raise ValueError("Informe o caminho do segredo no Vault.")

        if id_conexao > 0:
            consulta = text(
                f"""
                UPDATE {self._TABELA_CONEXAO}
                SET
                    Nome_Conexao = :nomeConexao,
                    Tipo_Banco = :tipoBanco,
                    Caminho_Segredo_Vault = :caminhoSegredoVault,
                    Driver_Banco = :driverBanco,
                    Schema_Padrao = :schemaPadrao,
                    Parametros_Conexao_Json = :parametrosConexao,
                    Ativo = :ativo,
                    Observacao = :observacao,
                    Atualizado_Em = :atualizadoEm,
                    Atualizado_Por = :atualizadoPor
                WHERE Id_Conexao = :idConexao
                """
            )
            with GetSqlServerEngine().begin() as conexao:
                resultado = conexao.execute(
                    consulta,
                    {
                        "idConexao": id_conexao,
                        "nomeConexao": nome_conexao,
                        "tipoBanco": tipo_banco,
                        "caminhoSegredoVault": caminho_segredo_vault,
                        "driverBanco": driver_banco,
                        "schemaPadrao": schema_padrao,
                        "parametrosConexao": parametros_conexao,
                        "ativo": 1 if ativo else 0,
                        "observacao": observacao,
                        "atualizadoEm": self._obterAgoraBrasilia(),
                        "atualizadoPor": usuarioAtual,
                    },
                )
                if int(resultado.rowcount or 0) == 0:
                    raise ValueError("Conexao informada nao foi encontrada para atualizacao.")
            return id_conexao

        consulta_insert = text(
            f"""
            SET NOCOUNT ON;
            INSERT INTO {self._TABELA_CONEXAO}
            (
                Nome_Conexao,
                Tipo_Banco,
                Caminho_Segredo_Vault,
                Driver_Banco,
                Schema_Padrao,
                Parametros_Conexao_Json,
                Ativo,
                Observacao,
                Criado_Em,
                Atualizado_Em,
                Criado_Por,
                Atualizado_Por
            )
            OUTPUT INSERTED.Id_Conexao AS idConexao
            VALUES
            (
                :nomeConexao,
                :tipoBanco,
                :caminhoSegredoVault,
                :driverBanco,
                :schemaPadrao,
                :parametrosConexao,
                :ativo,
                :observacao,
                :criadoEm,
                :atualizadoEm,
                :criadoPor,
                :atualizadoPor
            )
            """
        )

        agora = self._obterAgoraBrasilia()
        with GetSqlServerEngine().begin() as conexao:
            linha = conexao.execute(
                consulta_insert,
                {
                    "nomeConexao": nome_conexao,
                    "tipoBanco": tipo_banco,
                    "caminhoSegredoVault": caminho_segredo_vault,
                    "driverBanco": driver_banco,
                    "schemaPadrao": schema_padrao,
                    "parametrosConexao": parametros_conexao,
                    "ativo": 1 if ativo else 0,
                    "observacao": observacao,
                    "criadoEm": agora,
                    "atualizadoEm": agora,
                    "criadoPor": usuarioAtual,
                    "atualizadoPor": usuarioAtual,
                },
            ).mappings().first()

        if not linha:
            raise RuntimeError("Falha ao criar conexao.")
        return int(linha["idConexao"])

    def excluirConexao(self, idConexao: int) -> None:
        """Exclui uma conexao cadastrada se nao estiver vinculada a nenhuma tarefa."""
        self.garantirEstruturaDisponivel()
        id_conexao = int(idConexao)

        consulta_uso = text(
            f"""
            SELECT COUNT(*) AS total
            FROM {self._TABELA_WORKFLOW}
            WHERE Id_Conexao_Origem = :idConexao OR Id_Conexao_Destino = :idConexao
            """
        )
        with GetSqlServerEngine().connect() as conexao:
            total_uso = int(conexao.execute(consulta_uso, {"idConexao": id_conexao}).scalar() or 0)

        if total_uso > 0:
            raise ValueError(f"A conexao nao pode ser excluida pois esta em uso por {total_uso} tarefa(s).")

        consulta_delete = text(f"DELETE FROM {self._TABELA_CONEXAO} WHERE Id_Conexao = :idConexao")
        with GetSqlServerEngine().begin() as conexao:
            conexao.execute(consulta_delete, {"idConexao": id_conexao})

    def _validarSintaxeWorkflow(self, workflow: dict[str, Any]) -> None:
        """Valida a sintaxe SQL da origem e do destino no banco de dados antes de salvar."""
        if workflow.get("idConexaoOrigem") and workflow.get("queryOrigem"):
            try:
                engine_origem = self._obterEngineConexao(workflow["idConexaoOrigem"])
                query_origem_test = self._validarQueryLeitura(workflow["queryOrigem"])
                with engine_origem.connect() as conexao:
                    res = conexao.execute(text(query_origem_test))
                    res.mappings().fetchmany(1)
            except Exception as err_origem:
                msg = str(getattr(err_origem, "orig", err_origem))
                msg = re.sub(r'^\(.*?\)\s*', '', msg)
                raise ValueError(f"Erro na Query de Origem: {msg}")

        if workflow.get("idConexaoDestino") and workflow.get("modoDestino") == "QUERY_DESTINO" and workflow.get("queryDestino"):
            try:
                engine_destino = self._obterEngineConexao(workflow["idConexaoDestino"])
                query_destino_raw = workflow["queryDestino"].strip()
                query_destino_sql = re.sub(r'@\{([^}]+)\}', lambda m: f":{m.group(1).lower()}", query_destino_raw)
                query_limpa = re.sub(r'/\*.*?\*/', '', query_destino_sql, flags=re.DOTALL)
                query_limpa = re.sub(r'--.*', '', query_limpa).strip()
                es_merge = query_limpa.upper().startswith("MERGE")
                if es_merge and not query_destino_sql.strip().endswith(";"):
                    query_destino_sql = query_destino_sql.rstrip() + ";"

                variaveis = [v.lower() for v in re.findall(r'@\{([^}]+)\}', query_destino_raw)]
                params_nulos = {v: None for v in variaveis}

                with engine_destino.connect() as conexao:
                    trans = conexao.begin()
                    try:
                        dialect_name = str(engine_destino.dialect.name).lower()
                        if "mssql" in dialect_name or "sqlserver" in dialect_name or "pyodbc" in dialect_name:
                            query_validacao = f"SET NOEXEC ON;\n{query_destino_sql}\nSET NOEXEC OFF;"
                            conexao.execute(text(query_validacao), params_nulos)
                        else:
                            conexao.execute(text(query_destino_sql), params_nulos)
                    finally:
                        trans.rollback()
            except Exception as err_destino:
                msg = str(getattr(err_destino, "orig", err_destino))
                msg = re.sub(r'^\(.*?\)\s*', '', msg)
                raise ValueError(f"Erro de sintaxe na Query de Destino: {msg}")

    def salvarProcedimento(self, payload: dict[str, Any], usuarioAtual: str) -> int:
        """Cria ou atualiza uma tarefa de orquestração de banco."""
        self.garantirEstruturaDisponivel()

        workflow = self._normalizarWorkflowPayload(payload)
        self._validarSintaxeWorkflow(workflow)

        proxima_execucao = self._calcularProximaExecucao(
            baseUtc=self._obterAgoraBrasilia(),
            tipoAgendamento=workflow["tipoAgendamento"],
            configuracaoAgendamento=workflow["configuracaoAgendamento"],
            intervaloMinutos=workflow["intervaloMinutos"],
            ativo=workflow["ativo"],
        )

        if workflow["idWorkflow"]:
            consulta_update = text(
                f"""
                UPDATE {self._TABELA_WORKFLOW}
                SET
                    Nome_Workflow = :nomeWorkflow,
                    Descricao_Workflow = :descricaoWorkflow,
                    Id_Conexao_Origem = :idConexaoOrigem,
                    Id_Conexao_Destino = :idConexaoDestino,
                    Query_Origem = :queryOrigem,
                    Modo_Destino = :modoDestino,
                    Query_Destino = :queryDestino,
                    Schema_Destino = :schemaDestino,
                    Tabela_Destino = :tabelaDestino,
                    Modo_Carga = :modoCarga,
                    Criar_Tabela_Automaticamente = :criarTabelaAutomaticamente,
                    Tipo_Agendamento = :tipoAgendamento,
                    Configuracao_Agendamento = :configuracaoAgendamento,
                    Intervalo_Minutos = :intervaloMinutos,
                    Timeout_Segundos = :timeoutSegundos,
                    Lote_Linhas = :loteLinhas,
                    Ativo = :ativo,
                    Proxima_Execucao_Em = :proximaExecucaoEm,
                    Atualizado_Em = :atualizadoEm,
                    Atualizado_Por = :atualizadoPor
                WHERE Id_Workflow = :idWorkflow
                """
            )
            parametros = self._montarParametrosPersistenciaWorkflow(workflow, usuarioAtual, proxima_execucao)
            with GetSqlServerEngine().begin() as conexao:
                resultado = conexao.execute(consulta_update, parametros)
                if int(resultado.rowcount or 0) == 0:
                    raise ValueError("Tarefa informada nao foi encontrada para atualizacao.")
                self._substituirCamposWorkflow(conexao, int(workflow["idWorkflow"]), workflow["mapaCampos"])
            return int(workflow["idWorkflow"])

        consulta_insert = text(
            f"""
            SET NOCOUNT ON;
            INSERT INTO {self._TABELA_WORKFLOW}
            (
                Nome_Workflow,
                Descricao_Workflow,
                Id_Conexao_Origem,
                Id_Conexao_Destino,
                Query_Origem,
                Modo_Destino,
                Query_Destino,
                Schema_Destino,
                Tabela_Destino,
                Modo_Carga,
                Criar_Tabela_Automaticamente,
                Tipo_Agendamento,
                Configuracao_Agendamento,
                Intervalo_Minutos,
                Timeout_Segundos,
                Lote_Linhas,
                Ativo,
                Proxima_Execucao_Em,
                Status_Ultima_Execucao,
                Criado_Em,
                Atualizado_Em,
                Criado_Por,
                Atualizado_Por
            )
            OUTPUT INSERTED.Id_Workflow AS idWorkflow
            VALUES
            (
                :nomeWorkflow,
                :descricaoWorkflow,
                :idConexaoOrigem,
                :idConexaoDestino,
                :queryOrigem,
                :modoDestino,
                :queryDestino,
                :schemaDestino,
                :tabelaDestino,
                :modoCarga,
                :criarTabelaAutomaticamente,
                :tipoAgendamento,
                :configuracaoAgendamento,
                :intervaloMinutos,
                :timeoutSegundos,
                :loteLinhas,
                :ativo,
                :proximaExecucaoEm,
                'NUNCA_EXECUTADO',
                :criadoEm,
                :atualizadoEm,
                :criadoPor,
                :atualizadoPor
            )
            """
        )
        parametros = self._montarParametrosPersistenciaWorkflow(workflow, usuarioAtual, proxima_execucao)
        with GetSqlServerEngine().begin() as conexao:
            linha = conexao.execute(consulta_insert, parametros).mappings().first()
            if not linha:
                raise RuntimeError("Falha ao criar tarefa de orquestração.")
            id_workflow = int(linha["idWorkflow"])
            self._substituirCamposWorkflow(conexao, id_workflow, workflow["mapaCampos"])
        return id_workflow

    def excluirProcedimento(self, idProcedimento: int) -> None:
        """Exclui uma tarefa de orquestração e todo seu histórico de execuções."""
        self.garantirEstruturaDisponivel()
        id_procedimento = int(idProcedimento)

        with GetSqlServerEngine().begin() as conexao:
            conexao.execute(
                text(
                    f"""
                    DELETE FROM {self._TABELA_EXECUCAO_LOG}
                    WHERE Id_Execucao IN (
                        SELECT Id_Execucao FROM {self._TABELA_EXECUCAO} WHERE Id_Workflow = :idProcedimento
                    )
                    """
                ),
                {"idProcedimento": id_procedimento},
            )
            conexao.execute(
                text(f"DELETE FROM {self._TABELA_EXECUCAO} WHERE Id_Workflow = :idProcedimento"),
                {"idProcedimento": id_procedimento},
            )
            conexao.execute(
                text(f"DELETE FROM {self._TABELA_CAMPO} WHERE Id_Workflow = :idProcedimento"),
                {"idProcedimento": id_procedimento},
            )
            conexao.execute(
                text(f"DELETE FROM {self._TABELA_WORKFLOW} WHERE Id_Workflow = :idProcedimento"),
                {"idProcedimento": id_procedimento},
            )

    def testarOrigem(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Executa a query de origem em modo preview para montagem da tarefa."""
        self.garantirEstruturaDisponivel()

        id_conexao_origem = int(payload.get("idConexaoOrigem") or 0)
        query_origem = str(payload.get("origemQuery") or payload.get("queryOrigem") or "").strip()
        if id_conexao_origem <= 0:
            raise ValueError("Informe a conexao de origem para testar.")

        query_origem = self._validarQueryLeitura(query_origem)
        engine_origem = self._obterEngineConexao(id_conexao_origem)
        colunas, linhas = self._executarPreviewQuery(engine_origem, query_origem, limite=20)
        resumo = self._resumirLinhas(colunas, linhas)

        return {
            "colunas": resumo["colunas"],
            "amostras": linhas[:20],
            "resumo": resumo,
            "mapaCamposSugerido": self._sugerirMapaCampos(colunas),
        }

    def testarWorkflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Testa a orquestração completa sem persistir dados no destino."""
        workflow = self._normalizarWorkflowPayload(payload, exigirId=False)
        engine_origem = self._obterEngineConexao(workflow["idConexaoOrigem"])

        colunas_origem, linhas_origem_todas = self._executarPreviewQuery(engine_origem, workflow["queryOrigem"], limite=0)

        mapa_campos = workflow["mapaCampos"] or self._sugerirMapaCampos(colunas_origem)
        linhas_transformadas_todas = self._transformarLinhas(linhas_origem_todas, mapa_campos)
        colunas_destino = self._extrairColunasDestino(linhas_transformadas_todas, mapa_campos)
        validacao_destino = self._validarDestinoWorkflow(workflow, colunas_destino, linhas_transformadas_todas)

        total_extraidas = len(linhas_origem_todas)
        total_transformadas = len(linhas_transformadas_todas)

        total_insercoes = 0
        total_atualizacoes = 0
        chaves_configuradas = [c["nomeCampoDestino"] for c in mapa_campos if c.get("eChave")]

        if workflow["modoDestino"] == "QUERY_DESTINO":
            total_insercoes = validacao_destino.get("totalInsercoes", len(linhas_transformadas_todas))
            total_atualizacoes = validacao_destino.get("totalAtualizacoes", 0)
        elif chaves_configuradas and linhas_transformadas_todas and validacao_destino.get("tabelaExiste"):
            try:
                engine_destino = self._obterEngineConexao(workflow["idConexaoDestino"])
                schema = workflow["schemaDestino"] or "dbo"
                tabela = workflow["tabelaDestino"]
                if tabela:
                    condicoes = " AND ".join([f"{col} = :{col.lower()}" for col in chaves_configuradas])
                    sql_check = f"SELECT COUNT(1) FROM {schema}.{tabela} WHERE {condicoes}"
                    with engine_destino.connect() as conn:
                        for linha in linhas_transformadas_todas:
                            params = {col.lower(): linha.get(col) for col in chaves_configuradas}
                            resultado = conn.execute(text(sql_check), params).scalar()
                            if resultado and resultado > 0:
                                total_atualizacoes += 1
                            else:
                                total_insercoes += 1
            except Exception:
                total_insercoes = total_transformadas
                total_atualizacoes = 0
        elif linhas_transformadas_todas:
            total_insercoes = total_transformadas

        preview_final = validacao_destino.get("previewResolvido")
        if not preview_final:
            preview_final = linhas_transformadas_todas[:20]
        else:
            preview_final = preview_final[:20]

        return {
            "resumoOrigem": self._resumirLinhas(colunas_origem, linhas_origem_todas[:20]),
            "previewDestino": preview_final,
            "colunasDestino": list(preview_final[0].keys()) if preview_final else colunas_destino,
            "validacaoDestino": validacao_destino,
            "simulacao": {
                "totalExtraidas": total_extraidas,
                "totalTransformadas": total_transformadas,
                "totalInsercoesPrevistas": total_insercoes,
                "totalAtualizacoesPrevistas": total_atualizacoes,
                "chavesUtilizadas": chaves_configuradas,
            },
        }

    def executarProcedimento(self, idProcedimento: int, usuarioAtual: str) -> dict[str, Any]:
        """Executa uma tarefa de orquestração completa."""
        self.garantirEstruturaDisponivel()

        workflow = self.obterDetalheProcedimento(idProcedimento)
        engine_origem = self._obterEngineConexao(workflow["idConexaoOrigem"])
        engine_destino = self._obterEngineConexao(workflow["idConexaoDestino"])

        data_inicio = self._obterAgoraBrasilia()
        id_execucao = self._registrarInicioExecucao(idProcedimento, usuarioAtual, data_inicio)
        total_origem = 0
        total_processadas = 0
        total_escritas = 0

        try:
            self._registrarLogExecucao(
                id_execucao,
                "INICIO",
                "INFO",
                "Execução da tarefa iniciada.",
                {
                    "workflow": workflow["nomeProcedimento"],
                    "origem": workflow["idConexaoOrigem"],
                    "destino": workflow["idConexaoDestino"],
                },
            )

            with engine_origem.connect() as conexao_origem:
                resultado_origem = conexao_origem.execute(text(workflow["origemQuery"]))
                colunas_origem = list(resultado_origem.keys())
                mapa_campos = workflow["mapaCampos"] or self._sugerirMapaCampos(colunas_origem)

                lote_origem = resultado_origem.mappings().fetchmany(workflow["loteLinhas"])
                if not lote_origem:
                    raise ValueError("A query de origem nao retornou registros para processar.")

                while lote_origem:
                    linhas_transformadas = self._transformarLinhas(lote_origem, mapa_campos)
                    total_origem += len(lote_origem)
                    total_processadas += len(linhas_transformadas)

                    with engine_destino.begin() as conexao_destino:
                        total_escritas += self._escreverDestino(
                            conexao_destino=conexao_destino,
                            engineDestino=engine_destino,
                            workflow=workflow,
                            linhasTransformadas=linhas_transformadas,
                        )

                    lote_origem = resultado_origem.mappings().fetchmany(workflow["loteLinhas"])

            data_fim = self._obterAgoraBrasilia()
            duracao_ms = int((data_fim - data_inicio).total_seconds() * 1000)
            mensagem = f"Tarefa executada com sucesso. Linhas lidas: {total_origem}. Linhas escritas: {total_escritas}."
            self._registrarLogExecucao(id_execucao, "FIM", "INFO", mensagem, None)
            self._registrarFimExecucao(
                idExecucao=id_execucao,
                idWorkflow=idProcedimento,
                dataFim=data_fim,
                duracaoMs=duracao_ms,
                statusExecucao="SUCESSO",
                totalLinhasOrigem=total_origem,
                totalLinhasProcessadas=total_processadas,
                totalLinhasEscritas=total_escritas,
                mensagemResumo=mensagem,
                erroStack="",
            )
            return {
                "idProcedimento": idProcedimento,
                "idExecucao": id_execucao,
                "statusExecucao": "SUCESSO",
                "totalLinhasOrigem": total_origem,
                "totalLinhasProcessadas": total_processadas,
                "totalLinhasEscritas": total_escritas,
                "duracaoMs": duracao_ms,
                "mensagem": mensagem,
            }
        except Exception as erro_execucao:
            data_fim = self._obterAgoraBrasilia()
            duracao_ms = int((data_fim - data_inicio).total_seconds() * 1000)
            mensagem = f"Falha na execução: {str(erro_execucao)}"
            self._registrarLogExecucao(id_execucao, "ERRO", "ERROR", mensagem, {"stack": traceback.format_exc(limit=20)})
            self._registrarFimExecucao(
                idExecucao=id_execucao,
                idWorkflow=idProcedimento,
                dataFim=data_fim,
                duracaoMs=duracao_ms,
                statusExecucao="ERRO",
                totalLinhasOrigem=total_origem,
                totalLinhasProcessadas=total_processadas,
                totalLinhasEscritas=total_escritas,
                mensagemResumo=mensagem,
                erroStack=traceback.format_exc(limit=20),
            )
            raise

    def _montarParametrosPersistenciaWorkflow(self, workflow: dict[str, Any], usuarioAtual: str, proximaExecucao: datetime | None) -> dict[str, Any]:
        """Monta parametros comuns de persistencia da tarefa."""
        agora = self._obterAgoraBrasilia()
        return {
            "idWorkflow": workflow["idWorkflow"],
            "nomeWorkflow": workflow["nomeProcedimento"],
            "descricaoWorkflow": workflow["descricaoProcedimento"],
            "idConexaoOrigem": workflow["idConexaoOrigem"],
            "idConexaoDestino": workflow["idConexaoDestino"],
            "queryOrigem": workflow["queryOrigem"],
            "modoDestino": workflow["modoDestino"],
            "queryDestino": workflow["queryDestino"],
            "schemaDestino": workflow["schemaDestino"],
            "tabelaDestino": workflow["tabelaDestino"],
            "modoCarga": workflow["modoCarga"],
            "criarTabelaAutomaticamente": 1 if workflow["criarTabelaAutomaticamente"] else 0,
            "tipoAgendamento": workflow["tipoAgendamento"],
            "configuracaoAgendamento": self._serializarJson(workflow["configuracaoAgendamento"]),
            "intervaloMinutos": workflow["intervaloMinutos"],
            "timeoutSegundos": workflow["timeoutSegundos"],
            "loteLinhas": workflow["loteLinhas"],
            "ativo": 1 if workflow["ativo"] else 0,
            "proximaExecucaoEm": proximaExecucao,
            "criadoEm": agora,
            "atualizadoEm": agora,
            "criadoPor": usuarioAtual,
            "atualizadoPor": usuarioAtual,
        }

    def _substituirCamposWorkflow(self, conexaoControle, idWorkflow: int, mapaCampos: list[dict[str, Any]]) -> None:
        """Substitui o conjunto de mapeamentos de campo de uma tarefa."""
        conexaoControle.execute(text(f"DELETE FROM {self._TABELA_CAMPO} WHERE Id_Workflow = :idWorkflow"), {"idWorkflow": int(idWorkflow)})
        if not mapaCampos:
            return

        consulta_insert = text(
            f"""
            INSERT INTO {self._TABELA_CAMPO}
            (
                Id_Workflow,
                Ordem_Execucao,
                Nome_Campo_Origem,
                Nome_Campo_Destino,
                Tipo_Transformacao,
                Expressao_Transformacao,
                Valor_Padrao,
                Ativo,
                E_Chave,
                Ultimo_Valor_Sequencial
            )
            VALUES
            (
                :idWorkflow,
                :ordemExecucao,
                :nomeCampoOrigem,
                :nomeCampoDestino,
                :tipoTransformacao,
                :expressaoTransformacao,
                :valorPadrao,
                :ativo,
                :eChave,
                :ultimoValorSequencial
            )
            """
        )

        for indice, campo in enumerate(mapaCampos, start=1):
            conexaoControle.execute(
                consulta_insert,
                {
                    "idWorkflow": int(idWorkflow),
                    "ordemExecucao": int(campo.get("ordemExecucao") or indice),
                    "nomeCampoOrigem": campo.get("nomeCampoOrigem") or None,
                    "nomeCampoDestino": campo["nomeCampoDestino"],
                    "tipoTransformacao": campo["tipoTransformacao"],
                    "expressaoTransformacao": campo.get("expressaoTransformacao") or None,
                    "valorPadrao": campo.get("valorPadrao") or None,
                    "ativo": 1 if campo.get("ativo", True) else 0,
                    "eChave": 1 if campo.get("eChave", False) else 0,
                    "ultimoValorSequencial": int(campo.get("ultimoValorSequencial") or 0),
                },
            )

    def _listarCamposWorkflow(self, idWorkflow: int) -> list[dict[str, Any]]:
        """Lista o mapeamento de campos salvo para uma tarefa."""
        consulta = text(
            f"""
            SELECT
                Id_Workflow_Campo,
                Ordem_Execucao,
                Nome_Campo_Origem,
                Nome_Campo_Destino,
                Tipo_Transformacao,
                Expressao_Transformacao,
                Valor_Padrao,
                Ativo,
                E_Chave,
                Ultimo_Valor_Sequencial
            FROM {self._TABELA_CAMPO}
            WHERE Id_Workflow = :idWorkflow
            ORDER BY Ordem_Execucao ASC, Id_Workflow_Campo ASC
            """
        )
        with GetSqlServerEngine().connect() as conexao:
            linhas = conexao.execute(consulta, {"idWorkflow": int(idWorkflow)}).mappings().all()
            conexao.rollback()

        retorno: list[dict[str, Any]] = []
        for linha in linhas:
            retorno.append(
                {
                    "idWorkflowCampo": int(linha["Id_Workflow_Campo"]),
                    "ordemExecucao": int(linha["Ordem_Execucao"]),
                    "nomeCampoOrigem": linha["Nome_Campo_Origem"] or "",
                    "nomeCampoDestino": linha["Nome_Campo_Destino"],
                    "tipoTransformacao": linha["Tipo_Transformacao"],
                    "expressaoTransformacao": linha["Expressao_Transformacao"] or "",
                    "valorPadrao": linha["Valor_Padrao"] or "",
                    "ativo": bool(linha["Ativo"]),
                    "eChave": bool(linha["E_Chave"]),
                    "ultimoValorSequencial": linha["Ultimo_Valor_Sequencial"] or 0,
                }
            )
        return retorno

    def _normalizarWorkflowPayload(self, payload: dict[str, Any], exigirId: bool = False) -> dict[str, Any]:
        """Valida e normaliza o payload completo de uma tarefa."""
        id_workflow = int(payload.get("idProcedimento") or payload.get("idWorkflow") or 0)
        nome_procedimento = str(payload.get("nomeProcedimento") or payload.get("nomeWorkflow") or "").strip()
        descricao_procedimento = str(payload.get("descricaoProcedimento") or payload.get("descricaoWorkflow") or "").strip()
        id_conexao_origem = int(payload.get("idConexaoOrigem") or 0)
        id_conexao_destino = int(payload.get("idConexaoDestino") or 0)
        query_origem = str(payload.get("origemQuery") or payload.get("queryOrigem") or "").strip()
        modo_destino = str(payload.get("modoDestino") or "TABELA_ALVO").strip().upper()
        query_destino = str(payload.get("queryDestino") or "").strip()
        schema_destino = str(payload.get("schemaDestino") or "").strip()
        tabela_destino = str(payload.get("tabelaDestino") or "").strip()
        modo_carga = str(payload.get("modoCarga") or "APPEND").strip().upper()
        criar_tabela_automaticamente = bool(payload.get("criarTabelaAutomaticamente", True))
        tipo_agendamento = str(payload.get("tipoAgendamento") or "MANUAL").strip().upper()
        intervalo_minutos_bruto = payload.get("intervaloMinutos")
        intervalo_minutos = int(intervalo_minutos_bruto) if str(intervalo_minutos_bruto or "").strip() else None
        horario_execucao = str(payload.get("horarioExecucao") or "").strip()
        data_execucao_especifica = str(payload.get("dataExecucaoEspecifica") or "").strip()
        timeout_segundos = int(payload.get("timeoutSegundos") or 1800)
        lote_linhas = int(payload.get("loteLinhas") or 1000)
        ativo = bool(payload.get("ativo", True))
        mapa_campos = self._normalizarMapaCampos(payload.get("mapaCampos") or [])

        if exigirId and id_workflow <= 0:
            raise ValueError("Tarefa invalida para esta operacao.")
        if not nome_procedimento:
            raise ValueError("Informe o nome da tarefa.")
        if id_conexao_origem <= 0:
            raise ValueError("Informe uma conexao de origem.")
        if id_conexao_destino <= 0:
            raise ValueError("Informe uma conexao de destino.")
        if modo_destino not in self._MODOS_DESTINO:
            raise ValueError("Modo de destino invalido.")
        if modo_carga not in self._MODOS_CARGA:
            raise ValueError("Modo de carga invalido.")
        if timeout_segundos < 30:
            raise ValueError("Timeout deve ser de pelo menos 30 segundos.")
        if lote_linhas < 1:
            raise ValueError("Lote de linhas deve ser maior que zero.")

        query_origem = self._validarQueryLeitura(query_origem)

        if modo_destino == "TABELA_ALVO":
            if not tabela_destino:
                raise ValueError("Informe a tabela de destino.")
            self._validarIdentificador(schema_destino or "dbo", "schema de destino")
            self._validarIdentificador(tabela_destino, "tabela de destino")
        else:
            if not query_destino:
                raise ValueError("Informe a query de destino para o modo QUERY_DESTINO.")
            query_destino = query_destino.rstrip(";").strip()

        configuracao_agendamento, intervalo_minutos = self._normalizarConfiguracaoAgendamento(
            tipoAgendamento=tipo_agendamento,
            intervaloMinutos=intervalo_minutos,
            horarioExecucao=horario_execucao,
            dataExecucaoEspecifica=data_execucao_especifica,
        )

        return {
            "idWorkflow": id_workflow if id_workflow > 0 else None,
            "nomeProcedimento": nome_procedimento,
            "descricaoProcedimento": descricao_procedimento,
            "idConexaoOrigem": id_conexao_origem,
            "idConexaoDestino": id_conexao_destino,
            "queryOrigem": query_origem,
            "modoDestino": modo_destino,
            "queryDestino": query_destino,
            "schemaDestino": schema_destino or "dbo",
            "tabelaDestino": tabela_destino,
            "modoCarga": modo_carga,
            "criarTabelaAutomaticamente": criar_tabela_automaticamente,
            "tipoAgendamento": tipo_agendamento,
            "configuracaoAgendamento": configuracao_agendamento,
            "intervaloMinutos": intervalo_minutos,
            "timeoutSegundos": timeout_segundos,
            "loteLinhas": lote_linhas,
            "ativo": ativo,
            "mapaCampos": mapa_campos,
        }

    def _normalizarMapaCampos(self, mapaCampos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Valida e normaliza configuracoes de mapeamento de campo."""
        retorno: list[dict[str, Any]] = []
        for indice, campo in enumerate(mapaCampos, start=1):
            nome_campo_destino = str(campo.get("nomeCampoDestino") or "").strip()
            nome_campo_origem = str(campo.get("nomeCampoOrigem") or "").strip()
            tipo_transformacao = str(campo.get("tipoTransformacao") or "DIRETO").strip().upper()
            expressao_transformacao = str(campo.get("expressaoTransformacao") or "").strip()
            valor_padrao = str(campo.get("valorPadrao") or "").strip()
            ativo = bool(campo.get("ativo", True))

            if not nome_campo_destino:
                raise ValueError("Todos os mapeamentos precisam informar o campo de destino.")
            self._validarIdentificador(nome_campo_destino, "campo de destino")
            if nome_campo_origem:
                self._validarIdentificador(nome_campo_origem, "campo de origem")
            if tipo_transformacao not in self._TIPOS_TRANSFORMACAO:
                raise ValueError(f"Tipo de transformacao invalido: {tipo_transformacao}.")

            retorno.append(
                {
                    "ordemExecucao": int(campo.get("ordemExecucao") or indice),
                    "nomeCampoOrigem": nome_campo_origem,
                    "nomeCampoDestino": nome_campo_destino,
                    "tipoTransformacao": tipo_transformacao,
                    "expressaoTransformacao": expressao_transformacao,
                    "valorPadrao": valor_padrao,
                    "ativo": ativo,
                }
            )

        return retorno

    def _executarPreviewQuery(self, engineConexao: Engine, query: str, limite: int) -> tuple[list[str], list[dict[str, Any]]]:
        """Executa uma consulta em modo preview e retorna amostras."""
        query_limpa = str(query or "").strip().rstrip(";").strip()
        with engineConexao.connect() as conexao:
            resultado = conexao.execute(text(query_limpa))
            colunas = list(resultado.keys())
            linhas = [dict(linha) for linha in resultado.mappings().fetchmany(int(max(limite, 1)))]
        return colunas, linhas

    def _resumirLinhas(self, colunas: list[str], linhas: list[dict[str, Any]]) -> dict[str, Any]:
        """Gera resumo tecnico da amostra retornada pela query."""
        colunas_resumo: list[dict[str, Any]] = []
        for coluna in colunas:
            valores = [linha.get(coluna) for linha in linhas]
            primeiro_valor = next((valor for valor in valores if valor is not None), None)
            tipo_inferido = self._inferirTipoValor(primeiro_valor)
            colunas_resumo.append(
                {
                    "nomeCampo": coluna,
                    "tipoInferido": tipo_inferido,
                    "nulosNaAmostra": len([valor for valor in valores if valor is None]),
                    "exemplo": self._serializarValorPreview(primeiro_valor),
                }
            )

        return {
            "totalLinhasAmostra": len(linhas),
            "totalColunas": len(colunas),
            "colunas": colunas_resumo,
        }

    def _sugerirMapaCampos(self, colunas: list[str]) -> list[dict[str, Any]]:
        """Gera mapeamento direto padrao com base nas colunas da origem."""
        retorno: list[dict[str, Any]] = []
        for indice, coluna in enumerate(colunas, start=1):
            retorno.append(
                {
                    "ordemExecucao": indice,
                    "nomeCampoOrigem": coluna,
                    "nomeCampoDestino": coluna,
                    "tipoTransformacao": "DIRETO",
                    "expressaoTransformacao": "",
                    "valorPadrao": "",
                    "ativo": True,
                }
            )
        return retorno

    def _transformarLinhas(self, linhasOrigem: list[dict[str, Any]], mapaCampos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aplica o mapeamento configurado sobre uma amostra ou lote."""
        linhas_destino: list[dict[str, Any]] = []
        campos_ativos = [campo for campo in mapaCampos if campo.get("ativo", True)]
        for linha_origem in linhasOrigem:
            nova_linha: dict[str, Any] = {}
            for campo in campos_ativos:
                if str(campo.get("tipoTransformacao") or "").upper() == "AUTO_SEQUENCIAL":
                    seq = int(campo.get("ultimoValorSequencial") or 0) + 1
                    campo["ultimoValorSequencial"] = seq
                    nova_linha[campo["nomeCampoDestino"]] = seq
                else:
                    nova_linha[campo["nomeCampoDestino"]] = self._transformarValorCampo(linha_origem, campo)
            linhas_destino.append(nova_linha)
        return linhas_destino

    def _transformarValorCampo(self, linhaOrigem: dict[str, Any], campo: dict[str, Any]) -> Any:
        """Aplica a regra de transformacao de um campo especifico."""
        nome_campo_origem = campo.get("nomeCampoOrigem") or ""
        valor = linhaOrigem.get(nome_campo_origem) if nome_campo_origem else None
        tipo_transformacao = str(campo.get("tipoTransformacao") or "DIRETO").upper()
        expressao = str(campo.get("expressaoTransformacao") or "")
        valor_padrao = campo.get("valorPadrao") or None

        if tipo_transformacao == "VALOR_PADRAO":
            return valor_padrao

        if tipo_transformacao == "TEMPLATE":
            return self._resolverTemplate(expressao, linhaOrigem, valor_padrao)

        if valor is None and valor_padrao not in (None, ""):
            valor = valor_padrao

        if valor is None:
            return None

        if tipo_transformacao == "DIRETO":
            return valor
        if tipo_transformacao == "TEXTO_MAIUSCULO":
            return str(valor).upper()
        if tipo_transformacao == "TEXTO_MINUSCULO":
            return str(valor).lower()
        if tipo_transformacao == "TRIM":
            return str(valor).strip()
        if tipo_transformacao == "INTEGER":
            return int(valor)
        if tipo_transformacao == "DECIMAL":
            return Decimal(str(valor))
        if tipo_transformacao == "BOOLEANO":
            return str(valor).strip().lower() in {"1", "true", "sim", "yes", "s", "y"}
        if tipo_transformacao == "DATA_ISO":
            if isinstance(valor, datetime):
                return valor.isoformat()
            return str(valor)
        return valor

    def _resolverTemplate(self, expressao: str, linhaOrigem: dict[str, Any], valorPadrao: Any) -> str:
        """Resolve templates simples no formato ${Campo}."""
        if not expressao:
            return str(valorPadrao or "")
        retorno = expressao
        for chave, valor in linhaOrigem.items():
            retorno = retorno.replace(f"${{{chave}}}", "" if valor is None else str(valor))
        return retorno

    def _extrairColunasDestino(self, linhasTransformadas: list[dict[str, Any]], mapaCampos: list[dict[str, Any]]) -> list[str]:
        """Lista colunas de destino efetivamente produzidas pela transformacao."""
        if linhasTransformadas:
            return list(linhasTransformadas[0].keys())
        return [campo["nomeCampoDestino"] for campo in mapaCampos if campo.get("ativo", True)]

    def _extrairQueryUsing(self, querySql: str) -> str | None:
        """Extrai a instrucao SELECT de dentro da clausula USING (...) AS Origem lidando com parenteses aninhados."""
        match_start = re.search(r'USING\s*\(', str(querySql or ""), re.IGNORECASE)
        if not match_start:
            return None

        pos_start = match_start.end()
        depth = 1
        i = pos_start
        sql_str = str(querySql)
        while i < len(sql_str) and depth > 0:
            ch = sql_str[i]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1

        if depth == 0:
            conteudo_using = sql_str[pos_start:i].strip()
            if conteudo_using.upper().startswith("SELECT"):
                return conteudo_using
        return None

    def _validarDestinoWorkflow(self, workflow: dict[str, Any], colunasDestino: list[str], linhasTransformadas: list[dict[str, Any]]) -> dict[str, Any]:
        """Valida o destino configurado sem persistir dados."""
        engine_destino = self._obterEngineConexao(workflow["idConexaoDestino"])
        retorno: dict[str, Any] = {
            "modoDestino": workflow["modoDestino"],
            "tabelaExiste": None,
            "ddlSugerida": "",
            "queryDestinoValida": True,
            "previewResolvido": [],
            "totalInsercoes": 0,
            "totalAtualizacoes": 0,
        }

        if workflow["modoDestino"] == "QUERY_DESTINO" and not workflow["queryDestino"]:
            raise ValueError("Query de destino obrigatoria para o modo QUERY_DESTINO.")

        tabela_existe = None
        if workflow["modoDestino"] == "TABELA_ALVO":
            tabela_existe = False
            if workflow["tabelaDestino"]:
                try:
                    inspector_destino = inspect(engine_destino)
                    tabela_existe = inspector_destino.has_table(workflow["tabelaDestino"], schema=workflow["schemaDestino"])
                except Exception:
                    tabela_existe = False

            retorno["tabelaExiste"] = tabela_existe
            if not tabela_existe and workflow["tabelaDestino"]:
                retorno["ddlSugerida"] = self._gerarDdlSugeridaTabela(workflow["schemaDestino"], workflow["tabelaDestino"], linhasTransformadas)

        if workflow["modoDestino"] == "QUERY_DESTINO":
            import re
            variaveis_query = [v.lower() for v in re.findall(r'@\{([^}]+)\}', workflow["queryDestino"])]
            query_destino_sql = re.sub(r'@\{([^}]+)\}', lambda m: f":{m.group(1).lower()}", workflow["queryDestino"])
            query_destino_sql = query_destino_sql.strip()

            query_limpa = re.sub(r'/\*.*?\*/', '', query_destino_sql, flags=re.DOTALL)
            query_limpa = re.sub(r'--.*', '', query_limpa).strip()
            es_merge = query_limpa.upper().startswith("MERGE")
            if es_merge and not query_destino_sql.strip().endswith(";"):
                query_destino_sql = query_destino_sql.rstrip() + ";"

            if linhasTransformadas:
                with engine_destino.connect() as conexao_destino:
                    transacao = conexao_destino.begin()
                    try:
                        if workflow["criarTabelaAutomaticamente"] and workflow["tabelaDestino"]:
                            self._obterOuCriarTabelaDestino(
                                engineDestino=engine_destino,
                                schemaDestino=workflow["schemaDestino"],
                                tabelaDestino=workflow["tabelaDestino"],
                                criarTabelaAutomaticamente=True,
                                linhasTransformadas=linhasTransformadas,
                                mapaCampos=workflow["mapaCampos"],
                            )
                        sql_using_template = self._extrairQueryUsing(workflow["queryDestino"])
                        if sql_using_template:
                            for amostra in linhasTransformadas[:20]:
                                sql_eval = sql_using_template
                                for k, v in amostra.items():
                                    val_literal = "NULL"
                                    if v is not None:
                                        if isinstance(v, (int, float, Decimal)):
                                            val_literal = str(v)
                                        elif isinstance(v, bool):
                                            val_literal = "1" if v else "0"
                                        else:
                                            v_str = str(v).replace("'", "''")
                                            val_literal = f"'{v_str}'"

                                    sql_eval = re.sub(r'@\{\s*' + re.escape(k) + r'\s*\}', val_literal, sql_eval, flags=re.IGNORECASE)
                                    sql_eval = re.sub(r':' + re.escape(k) + r'\b', val_literal, sql_eval, flags=re.IGNORECASE)

                                sql_eval = re.sub(r'@\{[^}]+\}', 'NULL', sql_eval)
                                sql_eval = re.sub(r':\w+\b', 'NULL', sql_eval)

                                try:
                                    res_sample = conexao_destino.execute(text(sql_eval)).mappings().first()
                                    if res_sample:
                                        retorno["previewResolvido"].append(dict(res_sample))
                                except Exception:
                                    pass

                        query_exec = query_destino_sql
                        if es_merge:
                            sql_base = query_destino_sql.rstrip().rstrip(";").strip()
                            query_exec = f"{sql_base} OUTPUT $action AS [Acao_Simulacao];"

                        total_ins = 0
                        total_upd = 0
                        contou_acoes = False

                        for idx, linha in enumerate(linhasTransformadas):
                            parametros = {k.lower(): v for k, v in linha.items()}
                            for var in variaveis_query:
                                if var not in parametros:
                                    parametros[var] = None
                            try:
                                res_exec = conexao_destino.execute(text(query_exec), parametros)
                                if es_merge:
                                    acoes = [r["Acao_Simulacao"] for r in res_exec.mappings().all() if "Acao_Simulacao" in r]
                                    for ac in acoes:
                                        if str(ac).upper() == "INSERT":
                                            total_ins += 1
                                        elif str(ac).upper() == "UPDATE":
                                            total_upd += 1
                                    if acoes:
                                        contou_acoes = True
                            except Exception as ex_sub:
                                print(f"[DEBUG WORKFLOW VALIDACAO] Falha na linha {idx} com query_exec ({ex_sub}). Tentando query_destino_sql...")
                                try:
                                    conexao_destino.execute(text(query_destino_sql), parametros)
                                except Exception as ex_direto:
                                    print(f"[DEBUG WORKFLOW VALIDACAO FAIL] Linha {idx} com erro 23000/DB!\nParametros: {parametros}\nErro: {ex_direto}")
                                    logger.error(f"[VALIDACAO QUERY DESTINO FAILS] Parametros da linha {idx}: {parametros}")
                                    raise ex_direto

                        if contou_acoes:
                            retorno["totalInsercoes"] = total_ins
                            retorno["totalAtualizacoes"] = total_upd
                        elif es_merge:
                            retorno["totalInsercoes"] = len(linhasTransformadas)

                    except Exception as erro_query:
                        msg_erro = str(erro_query)
                        if getattr(erro_query, 'orig', None):
                            msg_erro = str(erro_query.orig)
                        print(f"[DEBUG ERRO QUERY DESTINO DETALHADO]: {msg_erro}")
                        raise ValueError(f"Erro de sintaxe ou limitacao na Query de Destino:\n{msg_erro}")
                    finally:
                        transacao.rollback()
            return retorno

        retorno["tabelaExiste"] = tabela_existe
        if not tabela_existe:
            retorno["ddlSugerida"] = self._gerarDdlSugeridaTabela(workflow["schemaDestino"], workflow["tabelaDestino"], linhasTransformadas)
        return retorno

    def _escreverDestino(self, conexao_destino, engineDestino: Engine, workflow: dict[str, Any], linhasTransformadas: list[dict[str, Any]]) -> int:
        """Persiste um lote transformado no destino configurado."""
        if not linhasTransformadas:
            return 0

        if workflow["modoDestino"] == "QUERY_DESTINO":
            import re
            variaveis_query = [v.lower() for v in re.findall(r'@\{([^}]+)\}', workflow["queryDestino"])]
            query_destino_sql = re.sub(r'@\{([^}]+)\}', lambda m: f":{m.group(1).lower()}", workflow["queryDestino"])
            query_destino_sql = query_destino_sql.strip()
            
            query_limpa = re.sub(r'/\*.*?\*/', '', query_destino_sql, flags=re.DOTALL)
            query_limpa = re.sub(r'--.*', '', query_limpa).strip()
            if query_limpa.upper().startswith("MERGE") and not query_destino_sql.strip().endswith(";"):
                query_destino_sql = query_destino_sql.rstrip() + ";"
            
            linhas_processadas = []
            for linha in linhasTransformadas:
                nova_linha = {k.lower(): v for k, v in linha.items()}
                for var in variaveis_query:
                    if var not in nova_linha:
                        nova_linha[var] = None
                linhas_processadas.append(nova_linha)

            if workflow.get("criarTabelaAutomaticamente") and workflow.get("tabelaDestino"):
                self._obterOuCriarTabelaDestino(
                    engineDestino=engineDestino,
                    schemaDestino=workflow["schemaDestino"],
                    tabelaDestino=workflow["tabelaDestino"],
                    criarTabelaAutomaticamente=True,
                    linhasTransformadas=linhasTransformadas,
                    mapaCampos=workflow["mapaCampos"],
                )

            try:
                conexao_destino.execute(text(query_destino_sql), linhas_processadas)
            except Exception as erro_escrever:
                print(f"[DEBUG EXECUCAO QUERY DESTINO FAIL]\nQuery:\n{query_destino_sql}\nPrimeiras 2 linhas params:\n{linhas_processadas[:2]}\nErro: {erro_escrever}")
                logger.error(f"[EXECUCAO QUERY DESTINO FAIL] {erro_escrever}")
                raise
            return len(linhasTransformadas)

        tabela_destino = self._obterOuCriarTabelaDestino(
            engineDestino=engineDestino,
            schemaDestino=workflow["schemaDestino"],
            tabelaDestino=workflow["tabelaDestino"],
            criarTabelaAutomaticamente=workflow["criarTabelaAutomaticamente"],
            linhasTransformadas=linhasTransformadas,
            mapaCampos=workflow["mapaCampos"],
        )

        if workflow["modoCarga"] == "TRUNCATE_APPEND":
            conexao_destino.execute(text(f"TRUNCATE TABLE {workflow['schemaDestino']}.{workflow['tabelaDestino']}"))
            workflow["modoCarga"] = "APPEND"

        conexao_destino.execute(tabela_destino.insert(), linhasTransformadas)
        self._atualizarValoresSequenciais(workflow["mapaCampos"])
        return len(linhasTransformadas)

    def _atualizarValoresSequenciais(self, mapaCampos: list[dict[str, Any]]) -> None:
        """Atualiza no banco o Ultimo_Valor_Sequencial se a transformacao for AUTO_SEQUENCIAL."""
        campos_seq = [c for c in mapaCampos if str(c.get("tipoTransformacao") or "").upper() == "AUTO_SEQUENCIAL" and c.get("idWorkflowCampo")]
        if not campos_seq:
            return
            
        consulta_update = text(
            f"""
            UPDATE {self._TABELA_CAMPO}
            SET Ultimo_Valor_Sequencial = :ultimoValorSequencial
            WHERE Id_Workflow_Campo = :idWorkflowCampo
            """
        )
        with GetSqlServerEngine().begin() as conexao:
            for campo in campos_seq:
                conexao.execute(
                    consulta_update,
                    {
                        "ultimoValorSequencial": int(campo.get("ultimoValorSequencial") or 0),
                        "idWorkflowCampo": int(campo["idWorkflowCampo"]),
                    }
                )

    def _obterOuCriarTabelaDestino(
        self,
        engineDestino: Engine,
        schemaDestino: str,
        tabelaDestino: str,
        criarTabelaAutomaticamente: bool,
        linhasTransformadas: list[dict[str, Any]],
        mapaCampos: list[dict[str, Any]],
    ) -> Table:
        """Retorna a tabela de destino carregada ou cria quando permitido."""
        tabela_existe = False
        try:
            inspector_destino = inspect(engineDestino)
            tabela_existe = inspector_destino.has_table(tabelaDestino, schema=schemaDestino)
        except Exception:
            tabela_existe = False

        metadata_destino = MetaData(schema=schemaDestino)

        if tabela_existe:
            try:
                return Table(tabelaDestino, metadata_destino, autoload_with=engineDestino, schema=schemaDestino)
            except Exception:
                pass

        if not criarTabelaAutomaticamente and not tabela_existe:
            raise ValueError(f"Tabela de destino '{schemaDestino}.{tabelaDestino}' nao existe e a criacao automatica esta desabilitada.")

        colunas_tabela: list[Column] = []
        primeira_linha = linhasTransformadas[0] if linhasTransformadas else {}
        for nome_coluna, valor_coluna in primeira_linha.items():
            campo_mapa = next((c for c in mapaCampos if c["nomeCampoDestino"] == nome_coluna), None)
            is_chave = bool(campo_mapa.get("eChave")) if campo_mapa else False
            colunas_tabela.append(Column(nome_coluna, self._inferirTipoSqlAlchemy(valor_coluna), primary_key=is_chave, nullable=not is_chave))

        tabela = Table(tabelaDestino, metadata_destino, *colunas_tabela, schema=schemaDestino)
        try:
            metadata_destino.create_all(engineDestino, tables=[tabela])
        except Exception as e:
            logger.error("Erro ao criar tabela de destino: %s", str(e))
        return tabela

    def _gerarDdlSugeridaTabela(self, schemaDestino: str, tabelaDestino: str, linhasTransformadas: list[dict[str, Any]]) -> str:
        """Gera uma sugestao simples de DDL para tabela de destino."""
        primeira_linha = linhasTransformadas[0] if linhasTransformadas else {}
        definicoes: list[str] = []
        for nome_coluna, valor_coluna in primeira_linha.items():
            definicoes.append(f"    [{nome_coluna}] {self._inferirTipoSqlTexto(valor_coluna)} NULL")

        corpo = ",\n".join(definicoes) if definicoes else "    [Id] INT NULL"
        return f"CREATE TABLE {schemaDestino}.{tabelaDestino} (\n{corpo}\n);"

    def _obterEngineConexao(self, idConexao: int) -> Engine:
        """Resolve e instancia a engine SQLAlchemy para a conexao escolhida via LuftCore."""
        registro = self._obterRegistroConexao(idConexao)
        tipo_banco_extensao = self._TIPOS_BANCO.get(registro["Tipo_Banco"])
        if not tipo_banco_extensao:
            raise ValueError("Tipo de banco nao suportado para esta conexao.")

        parametros_conexao = self._desserializarJson(registro["Parametros_Conexao_Json"])
        argumentos_extensao: dict[str, Any] = {
            "vault_addr": os.getenv("VAULT_ADDR"),
            "vault_token_criptografado": os.getenv("VAULT_TOKEN"),
            "token_acesso": os.getenv("TOKEN_ACESSO"),
            "caminho_segredo": registro["Caminho_Segredo_Vault"],
            "tipo_banco": tipo_banco_extensao,
        }

        driver_banco = registro["Driver_Banco"]
        if not driver_banco:
            if registro["Tipo_Banco"] == "MSSQL":
                driver_banco = os.getenv("DB_DRIVER") or os.getenv("SQLDB_DRIVER") or "ODBC Driver 17 for SQL Server"
            elif registro["Tipo_Banco"] == "ORACLE":
                driver_banco = "oracledb"

        if driver_banco:
            argumentos_extensao["driver_banco"] = driver_banco

        if registro["Tipo_Banco"] == "MSSQL" and not parametros_conexao:
            parametros_conexao = {"TrustServerCertificate": os.getenv("SQLDB_TRUST_SERVER_CERTIFICATE", "yes")}

        if registro["Tipo_Banco"] != "MSSQL" and parametros_conexao:
            parametros_conexao = {
                k: v for k, v in parametros_conexao.items()
                if k.lower() not in {"trustservercertificate", "trust_server_certificate"}
            }

        if parametros_conexao:
            argumentos_extensao["parametros_conexao"] = parametros_conexao

        extensao = SqlAlchemyExtension(**argumentos_extensao)
        engine = extensao.obter_engine()

        if registro["Tipo_Banco"] == "ORACLE":
            @event.listens_for(engine, "do_connect")
            def _substituir_sid_por_service_name(dialect, conn_rec, cargs, cparams):
                dsn = cparams.get("dsn")
                if isinstance(dsn, str) and "(CONNECT_DATA=(SID=" in dsn:
                    cparams["dsn"] = dsn.replace("(CONNECT_DATA=(SID=", "(CONNECT_DATA=(SERVICE_NAME=")

        return engine

    def _obterRegistroConexao(self, idConexao: int) -> dict[str, Any]:
        """Busca o registro de uma conexao cadastrada."""
        consulta = text(
            f"""
            SELECT
                Id_Conexao,
                Nome_Conexao,
                Tipo_Banco,
                Caminho_Segredo_Vault,
                Driver_Banco,
                Schema_Padrao,
                Parametros_Conexao_Json,
                Ativo
            FROM {self._TABELA_CONEXAO}
            WHERE Id_Conexao = :idConexao
            """
        )
        with GetSqlServerEngine().connect() as conexao:
            linha = conexao.execute(consulta, {"idConexao": int(idConexao)}).mappings().first()

        if not linha or not bool(linha["Ativo"]):
            raise ValueError("Conexao informada nao foi encontrada ou esta inativa.")
        return dict(linha)

    def _registrarInicioExecucao(self, idWorkflow: int, usuarioAtual: str, dataInicio: datetime) -> int:
        """Cria o registro principal de uma nova execucao."""
        consulta = text(
            f"""
            SET NOCOUNT ON;
            INSERT INTO {self._TABELA_EXECUCAO}
            (
                Id_Workflow,
                Data_Inicio,
                Status_Execucao,
                Executado_Por
            )
            OUTPUT INSERTED.Id_Execucao AS idExecucao
            VALUES
            (
                :idWorkflow,
                :dataInicio,
                'EM_EXECUCAO',
                :executadoPor
            );
            """
        )
        with GetSqlServerEngine().begin() as conexao:
            linha = conexao.execute(
                consulta,
                {"idWorkflow": int(idWorkflow), "dataInicio": dataInicio, "executadoPor": usuarioAtual},
            ).mappings().first()
        if not linha:
            raise RuntimeError("Falha ao registrar inicio da execucao.")
        return int(linha["idExecucao"])

    def _registrarFimExecucao(
        self,
        idExecucao: int,
        idWorkflow: int,
        dataFim: datetime,
        duracaoMs: int,
        statusExecucao: str,
        totalLinhasOrigem: int,
        totalLinhasProcessadas: int,
        totalLinhasEscritas: int,
        mensagemResumo: str,
        erroStack: str,
    ) -> None:
        """Finaliza a execucao e consolida os indicadores na tarefa."""
        tipo_agendamento, configuracao_agendamento, intervalo_minutos, ativo = self._obterConfiguracaoAgendamentoWorkflow(idWorkflow)
        proxima_execucao = None if statusExecucao == "ERRO" else self._calcularProximaExecucao(
            baseUtc=dataFim,
            tipoAgendamento=tipo_agendamento,
            configuracaoAgendamento=configuracao_agendamento,
            intervaloMinutos=intervalo_minutos,
            ativo=ativo,
        )

        consulta_execucao = text(
            f"""
            UPDATE {self._TABELA_EXECUCAO}
            SET
                Data_Fim = :dataFim,
                Duracao_Ms = :duracaoMs,
                Status_Execucao = :statusExecucao,
                Total_Linhas_Origem = :totalLinhasOrigem,
                Total_Linhas_Processadas = :totalLinhasProcessadas,
                Total_Linhas_Escritas = :totalLinhasEscritas,
                Mensagem_Resumo = :mensagemResumo,
                Erro_Stack = :erroStack
            WHERE Id_Execucao = :idExecucao
            """
        )
        consulta_workflow = text(
            f"""
            UPDATE {self._TABELA_WORKFLOW}
            SET
                Ultima_Execucao_Em = :dataFim,
                Proxima_Execucao_Em = :proximaExecucao,
                Duracao_Ultima_Execucao_Ms = :duracaoMs,
                Status_Ultima_Execucao = :statusExecucao,
                Total_Linhas_Ultima_Execucao = :totalLinhasEscritas,
                Mensagem_Ultima_Execucao = :mensagemResumo,
                Atualizado_Em = :atualizadoEm
            WHERE Id_Workflow = :idWorkflow
            """
        )
        with GetSqlServerEngine().begin() as conexao:
            conexao.execute(
                consulta_execucao,
                {
                    "idExecucao": int(idExecucao),
                    "dataFim": dataFim,
                    "duracaoMs": int(duracaoMs),
                    "statusExecucao": statusExecucao,
                    "totalLinhasOrigem": int(totalLinhasOrigem),
                    "totalLinhasProcessadas": int(totalLinhasProcessadas),
                    "totalLinhasEscritas": int(totalLinhasEscritas),
                    "mensagemResumo": mensagemResumo[:2000],
                    "erroStack": erroStack,
                },
            )
            conexao.execute(
                consulta_workflow,
                {
                    "idWorkflow": int(idWorkflow),
                    "dataFim": dataFim,
                    "proximaExecucao": proxima_execucao,
                    "duracaoMs": int(duracaoMs),
                    "statusExecucao": statusExecucao,
                    "totalLinhasEscritas": int(totalLinhasEscritas),
                    "mensagemResumo": mensagemResumo[:1000],
                    "atualizadoEm": self._obterAgoraBrasilia(),
                },
            )

    def _registrarLogExecucao(self, idExecucao: int, etapaLog: str, nivelLog: str, mensagemLog: str, payloadLog: Any) -> None:
        """Registra um evento detalhado no log da execucao."""
        consulta = text(
            f"""
            INSERT INTO {self._TABELA_EXECUCAO_LOG}
            (
                Id_Execucao,
                Etapa_Log,
                Nivel_Log,
                Mensagem_Log,
                Payload_Log,
                Criado_Em
            )
            VALUES
            (
                :idExecucao,
                :etapaLog,
                :nivelLog,
                :mensagemLog,
                :payloadLog,
                :criadoEm
            )
            """
        )
        with GetSqlServerEngine().begin() as conexao:
            conexao.execute(
                consulta,
                {
                    "idExecucao": int(idExecucao),
                    "etapaLog": etapaLog[:120],
                    "nivelLog": nivelLog[:24],
                    "mensagemLog": mensagemLog[:2000],
                    "payloadLog": self._serializarJson(payloadLog) if payloadLog is not None else None,
                    "criadoEm": self._obterAgoraBrasilia(),
                },
            )

    def _obterConfiguracaoAgendamentoWorkflow(self, idWorkflow: int) -> tuple[str, dict[str, Any], int | None, bool]:
        """Consulta a configuracao de agendamento persistida."""
        consulta = text(
            f"""
            SELECT Tipo_Agendamento, Configuracao_Agendamento, Intervalo_Minutos, Ativo
            FROM {self._TABELA_WORKFLOW}
            WHERE Id_Workflow = :idWorkflow
            """
        )
        with GetSqlServerEngine().connect() as conexao:
            linha = conexao.execute(consulta, {"idWorkflow": int(idWorkflow)}).mappings().first()
            conexao.rollback()
        if not linha:
            return "MANUAL", {}, None, False
        return (
            str(linha["Tipo_Agendamento"] or "MANUAL"),
            self._desserializarJson(linha["Configuracao_Agendamento"]),
            int(linha["Intervalo_Minutos"]) if linha["Intervalo_Minutos"] is not None else None,
            bool(linha["Ativo"]),
        )

    def _normalizarConfiguracaoAgendamento(
        self,
        tipoAgendamento: str,
        intervaloMinutos: int | None,
        horarioExecucao: str,
        dataExecucaoEspecifica: str,
    ) -> tuple[dict[str, Any], int | None]:
        """Valida e normaliza a configuracao do agendamento."""
        if tipoAgendamento not in self._TIPOS_AGENDAMENTO:
            raise ValueError("Tipo de agendamento invalido.")
        if tipoAgendamento == "MANUAL":
            return {}, None
        if tipoAgendamento == "INTERVALO":
            if intervaloMinutos is None or intervaloMinutos < 1:
                raise ValueError("Informe um intervalo em minutos maior que zero.")
            return {"intervaloMinutos": int(intervaloMinutos)}, int(intervaloMinutos)
        if tipoAgendamento == "DIARIO":
            if not self._PADRAO_HORARIO.match(horarioExecucao):
                raise ValueError("Horario diario invalido. Use HH:MM.")
            return {"horarioExecucao": horarioExecucao}, None
        data_normalizada = self._normalizarDataIso(dataExecucaoEspecifica)
        return {"dataExecucaoEspecifica": data_normalizada.isoformat()}, None

    def _calcularProximaExecucao(
        self,
        baseUtc: datetime,
        tipoAgendamento: str,
        configuracaoAgendamento: dict[str, Any],
        intervaloMinutos: int | None,
        ativo: bool,
    ) -> datetime | None:
        """Calcula a proxima execucao prevista da tarefa."""
        if not ativo:
            return None
        if tipoAgendamento == "MANUAL":
            return None
        if tipoAgendamento == "INTERVALO":
            return baseUtc + timedelta(minutes=int(intervaloMinutos or 0)) if intervaloMinutos else None
        if tipoAgendamento == "DIARIO":
            horario = str(configuracaoAgendamento.get("horarioExecucao") or "").strip()
            if not self._PADRAO_HORARIO.match(horario):
                return None
            hora, minuto = horario.split(":")
            candidato = baseUtc.astimezone(timezone.utc).replace(hour=int(hora), minute=int(minuto), second=0, microsecond=0)
            if candidato <= baseUtc.astimezone(timezone.utc):
                candidato += timedelta(days=1)
            return candidato
        if tipoAgendamento == "DATA_ESPECIFICA":
            data_execucao = self._normalizarDataIso(str(configuracaoAgendamento.get("dataExecucaoEspecifica") or ""))
            return data_execucao if data_execucao > baseUtc.astimezone(timezone.utc) else None
        return None

    def _descreverAgendamento(self, tipoAgendamento: str, configuracaoAgendamento: dict[str, Any], intervaloMinutos: int | None) -> str:
        """Retorna descricao amigavel da agenda configurada."""
        if tipoAgendamento == "INTERVALO" and intervaloMinutos:
            return f"A cada {int(intervaloMinutos)} minuto(s)"
        if tipoAgendamento == "DIARIO":
            return f"Todos os dias as {configuracaoAgendamento.get('horarioExecucao', '--:--')}"
        if tipoAgendamento == "DATA_ESPECIFICA":
            return f"Execucao unica em {configuracaoAgendamento.get('dataExecucaoEspecifica', '')}"
        return "Manual"

    def _validarQueryLeitura(self, query: str) -> str:
        """Garante que a query de origem seja somente leitura e retorna a query sanitizada sem ponto e virgula final."""
        consulta_limpa = str(query or "").strip().rstrip(";").strip()
        consulta_normalizada = f" {consulta_limpa.lower()} "
        if not consulta_limpa.lower().startswith(("select", "with")):
            raise ValueError("A query de origem precisa iniciar com SELECT ou WITH.")
        for token in [" insert ", " update ", " delete ", " merge ", " drop ", " alter ", " truncate ", " grant ", " revoke "]:
            if token in consulta_normalizada:
                raise ValueError("A query de origem contem comandos nao permitidos para leitura.")
        return consulta_limpa

    def _validarIdentificador(self, valor: str, descricao: str) -> None:
        """Valida identificadores simples de schema, tabela ou coluna."""
        if not self._PADRAO_IDENTIFICADOR.match(str(valor or "").strip()):
            raise ValueError(f"Formato invalido para {descricao}.")

    def _inferirTipoValor(self, valor: Any) -> str:
        """Infere uma descricao textual simples do valor informado."""
        if valor is None:
            return "null"
        if isinstance(valor, bool):
            return "boolean"
        if isinstance(valor, int):
            return "integer"
        if isinstance(valor, (float, Decimal)):
            return "decimal"
        if isinstance(valor, datetime):
            return "datetime"
        return type(valor).__name__.lower()

    def _inferirTipoSqlAlchemy(self, valor: Any):
        """Infere o tipo SQLAlchemy mais adequado para criacao automatica."""
        if valor is None:
            return Text()
        if isinstance(valor, bool):
            return Boolean()
        if isinstance(valor, int):
            return Integer()
        if isinstance(valor, (float, Decimal)):
            return Numeric(18, 6)
        if isinstance(valor, datetime):
            return DateTime()
        return String(500)

    def _inferirTipoSqlTexto(self, valor: Any) -> str:
        """Infere o tipo textual do SQL para sugestao de DDL."""
        tipo_sqlalchemy = self._inferirTipoSqlAlchemy(valor)
        if isinstance(tipo_sqlalchemy, Boolean):
            return "BIT"
        if isinstance(tipo_sqlalchemy, Integer):
            return "INT"
        if isinstance(tipo_sqlalchemy, Numeric):
            return "DECIMAL(18,6)"
        if isinstance(tipo_sqlalchemy, DateTime):
            return "DATETIME2(0)"
        return "NVARCHAR(500)"

    def _serializarJson(self, valor: Any) -> str:
        """Serializa estruturas para JSON compacto."""
        return json.dumps(valor or {}, ensure_ascii=True, default=str, separators=(",", ":"))

    def _desserializarJson(self, valor: Any) -> dict[str, Any]:
        """Desserializa JSON quando o valor estiver presente."""
        if not valor:
            return {}
        try:
            retorno = json.loads(str(valor))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return retorno if isinstance(retorno, dict) else {}

    def _serializarValorPreview(self, valor: Any) -> Any:
        """Normaliza valores para resposta JSON de preview."""
        if isinstance(valor, datetime):
            return valor.isoformat()
        if isinstance(valor, Decimal):
            return str(valor)
        return valor

    def _normalizarDataIso(self, valorData: str) -> datetime:
        """Converte um texto ISO em datetime no fuso horario de Brasilia (UTC-3)."""
        valor_normalizado = str(valorData or "").strip().replace("Z", "-03:00")
        if not valor_normalizado:
            raise ValueError("Data invalida.")
        data_convertida = datetime.fromisoformat(valor_normalizado)
        if data_convertida.tzinfo is None:
            data_convertida = data_convertida.replace(tzinfo=FUSO_BRASILIA)
        return data_convertida.astimezone(FUSO_BRASILIA).replace(tzinfo=None)

    def _formatarData(self, valorData: Any) -> str:
        """Converte datetime em texto formatado no padrao de Brasilia (YYYY-MM-DD HH:MM:SS)."""
        if not valorData:
            return ""
        if isinstance(valorData, datetime):
            return valorData.strftime("%Y-%m-%d %H:%M:%S")
        return str(valorData)

    def processarWorkflowsAgendados(self) -> list[dict[str, Any]]:
        """Busca e executa tarefas ativas cujo horario agendado foi atingido."""
        try:
            if not self.obterDiagnosticoEstrutura().get("tabelaWorkflowExiste"):
                return []
        except Exception:
            return []

        agora = self._obterAgoraBrasilia()
        consulta = text(
            f"""
            SELECT Id_Workflow
            FROM {self._TABELA_WORKFLOW}
            WHERE Ativo = 1
              AND Tipo_Agendamento <> 'MANUAL'
              AND (Proxima_Execucao_Em IS NULL OR Proxima_Execucao_Em <= :agora)
            """
        )
        with GetSqlServerEngine().connect() as conexao:
            ids_devidos = conexao.execute(consulta, {"agora": agora}).scalars().all()
            conexao.rollback()

        resultados: list[dict[str, Any]] = []
        for id_wf in ids_devidos:
            try:
                res = self.executarProcedimento(int(id_wf), "AGENDADOR_AUTOMATICO")
                resultados.append(res)
            except Exception as erro:
                logger.exception("Falha na execução automática da tarefa #%s: %s", id_wf, erro)
        return resultados
