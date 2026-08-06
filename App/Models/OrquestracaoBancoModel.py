"""Modelos estruturais da central de orquestração de bancos de dados.

Este modulo concentra as tabelas de metadados da central de tarefas
e orquestracao entre bancos de dados, permitindo fontes e destinos
heterogêneos, mapeamento de campos, testes prévios e trilha completa de execução.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, NVARCHAR, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def MontarNomeTabelaQualificada(nomeTabela: str) -> str:
    """Monta o nome totalmente qualificado da tabela no SQL Server.

    Parametros:
    nomeTabela: Nome fisico da tabela sem banco/schema.

    Retorno:
    str: Nome no formato banco.schema.tabela.
    """
    return f"intec.dbo.{nomeTabela}"


class BaseModelHub(DeclarativeBase):
    """Classe base declarativa para os modelos internos do Hub."""


class TbBancoConexao(BaseModelHub):
    """Representa uma conexão reutilizável da central de orquestração.

    Cada registro descreve um endpoint de banco de dados e como o Hub
    deve buscar suas credenciais, priorizando segredos no Vault.
    """

    __tablename__ = "Tb_BancoConexao"
    __table_args__ = {"schema": "dbo"}

    NOME_TABELA_QUALIFICADA = MontarNomeTabelaQualificada(__tablename__)

    Id_Conexao: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Nome_Conexao: Mapped[str] = mapped_column(NVARCHAR(160), nullable=False)
    Tipo_Banco: Mapped[str] = mapped_column(String(24), nullable=False)
    Caminho_Segredo_Vault: Mapped[str] = mapped_column(NVARCHAR(260), nullable=False)
    Driver_Banco: Mapped[str | None] = mapped_column(NVARCHAR(160), nullable=True)
    Schema_Padrao: Mapped[str | None] = mapped_column(NVARCHAR(120), nullable=True)
    Parametros_Conexao_Json: Mapped[str | None] = mapped_column(NVARCHAR(2000), nullable=True)
    Ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    Observacao: Mapped[str | None] = mapped_column(NVARCHAR(600), nullable=True)
    Criado_Em: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Atualizado_Em: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Criado_Por: Mapped[str | None] = mapped_column(NVARCHAR(160), nullable=True)
    Atualizado_Por: Mapped[str | None] = mapped_column(NVARCHAR(160), nullable=True)


class TbBancoTarefa(BaseModelHub):
    """Representa uma tarefa de orquestração de banco configurável.

    A tarefa une uma conexão de origem, uma conexão de destino e a
    estratégia de transformação/escrita aplicada entre elas.
    """

    __tablename__ = "Tb_BancoTarefa"
    __table_args__ = {"schema": "dbo"}

    NOME_TABELA_QUALIFICADA = MontarNomeTabelaQualificada(__tablename__)

    Id_Workflow: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Nome_Workflow: Mapped[str] = mapped_column(NVARCHAR(180), nullable=False)
    Descricao_Workflow: Mapped[str | None] = mapped_column(NVARCHAR(700), nullable=True)
    Id_Conexao_Origem: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.Tb_BancoConexao.Id_Conexao"), nullable=False)
    Id_Conexao_Destino: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.Tb_BancoConexao.Id_Conexao"), nullable=False)
    Query_Origem: Mapped[str] = mapped_column(Text, nullable=False)
    Modo_Destino: Mapped[str] = mapped_column(String(32), nullable=False)
    Query_Destino: Mapped[str | None] = mapped_column(Text, nullable=True)
    Schema_Destino: Mapped[str | None] = mapped_column(NVARCHAR(120), nullable=True)
    Tabela_Destino: Mapped[str | None] = mapped_column(NVARCHAR(180), nullable=True)
    Modo_Carga: Mapped[str] = mapped_column(String(24), nullable=False)
    Criar_Tabela_Automaticamente: Mapped[bool] = mapped_column(Boolean, nullable=False)
    Tipo_Agendamento: Mapped[str] = mapped_column(String(24), nullable=False)
    Configuracao_Agendamento: Mapped[str | None] = mapped_column(NVARCHAR(1200), nullable=True)
    Intervalo_Minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Timeout_Segundos: Mapped[int] = mapped_column(Integer, nullable=False)
    Lote_Linhas: Mapped[int] = mapped_column(Integer, nullable=False)
    Ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    Ultima_Execucao_Em: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    Proxima_Execucao_Em: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    Duracao_Ultima_Execucao_Ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Status_Ultima_Execucao: Mapped[str] = mapped_column(String(24), nullable=False)
    Total_Linhas_Ultima_Execucao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Mensagem_Ultima_Execucao: Mapped[str | None] = mapped_column(NVARCHAR(1000), nullable=True)
    Criado_Em: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Atualizado_Em: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Criado_Por: Mapped[str | None] = mapped_column(NVARCHAR(160), nullable=True)
    Atualizado_Por: Mapped[str | None] = mapped_column(NVARCHAR(160), nullable=True)


class TbBancoTarefaCampo(BaseModelHub):
    """Representa o mapeamento de um campo dentro de uma tarefa de orquestração.

    Cada registro descreve de onde o dado vem, para onde vai e qual
    transformação deve ser aplicada antes da escrita no destino.
    """

    __tablename__ = "Tb_BancoTarefaCampo"
    __table_args__ = {"schema": "dbo"}

    NOME_TABELA_QUALIFICADA = MontarNomeTabelaQualificada(__tablename__)

    Id_Workflow_Campo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Workflow: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.Tb_BancoTarefa.Id_Workflow"), nullable=False)
    Ordem_Execucao: Mapped[int] = mapped_column(Integer, nullable=False)
    Nome_Campo_Origem: Mapped[str | None] = mapped_column(NVARCHAR(180), nullable=True)
    Nome_Campo_Destino: Mapped[str] = mapped_column(NVARCHAR(180), nullable=False)
    Tipo_Transformacao: Mapped[str] = mapped_column(String(32), nullable=False)
    Expressao_Transformacao: Mapped[str | None] = mapped_column(NVARCHAR(1000), nullable=True)
    Valor_Padrao: Mapped[str | None] = mapped_column(NVARCHAR(500), nullable=True)
    Ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    E_Chave: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Ultimo_Valor_Sequencial: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)


class TbBancoExecucao(BaseModelHub):
    """Representa uma execução concreta de uma tarefa de orquestração."""

    __tablename__ = "Tb_BancoExecucao"
    __table_args__ = {"schema": "dbo"}

    NOME_TABELA_QUALIFICADA = MontarNomeTabelaQualificada(__tablename__)

    Id_Execucao: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Workflow: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.Tb_BancoTarefa.Id_Workflow"), nullable=False)
    Data_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Data_Fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    Duracao_Ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Status_Execucao: Mapped[str] = mapped_column(String(24), nullable=False)
    Total_Linhas_Origem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Total_Linhas_Processadas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Total_Linhas_Escritas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Mensagem_Resumo: Mapped[str | None] = mapped_column(NVARCHAR(2000), nullable=True)
    Erro_Stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    Executado_Por: Mapped[str | None] = mapped_column(NVARCHAR(160), nullable=True)


class TbBancoExecucaoLog(BaseModelHub):
    """Representa eventos detalhados ocorridos durante uma execução."""

    __tablename__ = "Tb_BancoExecucaoLog"
    __table_args__ = {"schema": "dbo"}

    NOME_TABELA_QUALIFICADA = MontarNomeTabelaQualificada(__tablename__)

    Id_Execucao_Log: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Execucao: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.Tb_BancoExecucao.Id_Execucao"), nullable=False)
    Etapa_Log: Mapped[str] = mapped_column(NVARCHAR(120), nullable=False)
    Nivel_Log: Mapped[str] = mapped_column(String(24), nullable=False)
    Mensagem_Log: Mapped[str] = mapped_column(NVARCHAR(2000), nullable=False)
    Payload_Log: Mapped[str | None] = mapped_column(Text, nullable=True)
    Criado_Em: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
