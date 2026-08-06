    /*
    Estrutura da central de orquestração de bancos de dados.
    As tabelas de metadados ficam em intec.dbo e suportam:
    - conexões multi-banco
    - tarefas de origem/destino heterogêneos
    - mapeamento de campos e transformações
    - histórico detalhado de execução com logs por etapa
    */

    IF OBJECT_ID('intec.dbo.Tb_BancoExecucaoLog', 'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoExecucaoLog;
    GO

    IF OBJECT_ID('intec.dbo.Tb_BancoExecucao', 'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoExecucao;
    GO

    IF OBJECT_ID('intec.dbo.Tb_BancoTarefaCampo', 'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoTarefaCampo;
    GO

    IF OBJECT_ID('intec.dbo.Tb_BancoTarefa', 'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoTarefa;
    GO

    IF OBJECT_ID('intec.dbo.Tb_BancoConexao', 'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoConexao;
    GO

    CREATE TABLE intec.dbo.Tb_BancoConexao
    (
        Id_Conexao INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Nome_Conexao NVARCHAR(160) NOT NULL,
        Tipo_Banco VARCHAR(24) NOT NULL,
        Caminho_Segredo_Vault NVARCHAR(260) NOT NULL,
        Driver_Banco NVARCHAR(160) NULL,
        Schema_Padrao NVARCHAR(120) NULL,
        Parametros_Conexao_Json NVARCHAR(2000) NULL,
        Ativo BIT NOT NULL CONSTRAINT DF_Tb_BancoConexao_Ativo DEFAULT (1),
        Observacao NVARCHAR(600) NULL,
        Criado_Em DATETIME2(0) NOT NULL CONSTRAINT DF_Tb_BancoConexao_CriadoEm DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Atualizado_Em DATETIME2(0) NOT NULL CONSTRAINT DF_Tb_BancoConexao_AtualizadoEm DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Criado_Por NVARCHAR(160) NULL,
        Atualizado_Por NVARCHAR(160) NULL,
        CONSTRAINT UQ_Tb_BancoConexao_Nome UNIQUE (Nome_Conexao),
        CONSTRAINT CK_Tb_BancoConexao_TipoBanco CHECK (Tipo_Banco IN ('MSSQL', 'ORACLE', 'POSTGRESQL'))
    );
    GO

    CREATE TABLE intec.dbo.Tb_BancoTarefa
    (
        Id_Workflow INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Nome_Workflow NVARCHAR(180) NOT NULL,
        Descricao_Workflow NVARCHAR(700) NULL,
        Id_Conexao_Origem INT NOT NULL,
        Id_Conexao_Destino INT NOT NULL,
        Query_Origem NVARCHAR(MAX) NOT NULL,
        Modo_Destino VARCHAR(32) NOT NULL,
        Query_Destino NVARCHAR(MAX) NULL,
        Schema_Destino NVARCHAR(120) NULL,
        Tabela_Destino NVARCHAR(180) NULL,
        Modo_Carga VARCHAR(24) NOT NULL,
        Criar_Tabela_Automaticamente BIT NOT NULL CONSTRAINT DF_Tb_BancoTarefa_CriarTabela DEFAULT (1),
        Tipo_Agendamento VARCHAR(24) NOT NULL,
        Configuracao_Agendamento NVARCHAR(1200) NULL,
        Intervalo_Minutos INT NULL,
        Timeout_Segundos INT NOT NULL CONSTRAINT DF_Tb_BancoTarefa_Timeout DEFAULT (1800),
        Lote_Linhas INT NOT NULL CONSTRAINT DF_Tb_BancoTarefa_LoteLinhas DEFAULT (1000),
        Ativo BIT NOT NULL CONSTRAINT DF_Tb_BancoTarefa_Ativo DEFAULT (1),
        Ultima_Execucao_Em DATETIME2(0) NULL,
        Proxima_Execucao_Em DATETIME2(0) NULL,
        Duracao_Ultima_Execucao_Ms INT NULL,
        Status_Ultima_Execucao VARCHAR(24) NOT NULL CONSTRAINT DF_Tb_BancoTarefa_StatusUltima DEFAULT ('NUNCA_EXECUTADO'),
        Total_Linhas_Ultima_Execucao INT NULL,
        Mensagem_Ultima_Execucao NVARCHAR(1000) NULL,
        Criado_Em DATETIME2(0) NOT NULL CONSTRAINT DF_Tb_BancoTarefa_CriadoEm DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Atualizado_Em DATETIME2(0) NOT NULL CONSTRAINT DF_Tb_BancoTarefa_AtualizadoEm DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Criado_Por NVARCHAR(160) NULL,
        Atualizado_Por NVARCHAR(160) NULL,
        CONSTRAINT UQ_Tb_BancoTarefa_Nome UNIQUE (Nome_Workflow),
        CONSTRAINT FK_Tb_BancoTarefa_ConexaoOrigem FOREIGN KEY (Id_Conexao_Origem) REFERENCES intec.dbo.Tb_BancoConexao (Id_Conexao),
        CONSTRAINT FK_Tb_BancoTarefa_ConexaoDestino FOREIGN KEY (Id_Conexao_Destino) REFERENCES intec.dbo.Tb_BancoConexao (Id_Conexao),
        CONSTRAINT CK_Tb_BancoTarefa_ModoDestino CHECK (Modo_Destino IN ('TABELA_ALVO', 'QUERY_DESTINO')),
        CONSTRAINT CK_Tb_BancoTarefa_ModoCarga CHECK (Modo_Carga IN ('APPEND', 'TRUNCATE_APPEND')),
        CONSTRAINT CK_Tb_BancoTarefa_TipoAgendamento CHECK (Tipo_Agendamento IN ('MANUAL', 'INTERVALO', 'DIARIO', 'DATA_ESPECIFICA'))
    );
    GO

    CREATE TABLE intec.dbo.Tb_BancoTarefaCampo
    (
        Id_Workflow_Campo INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Id_Workflow INT NOT NULL,
        Ordem_Execucao INT NOT NULL,
        Nome_Campo_Origem NVARCHAR(180) NULL,
        Nome_Campo_Destino NVARCHAR(180) NOT NULL,
        Tipo_Transformacao VARCHAR(32) NOT NULL,
        Expressao_Transformacao NVARCHAR(1000) NULL,
        Valor_Padrao NVARCHAR(500) NULL,
        Ativo BIT NOT NULL CONSTRAINT DF_Tb_BancoTarefaCampo_Ativo DEFAULT (1),
        E_Chave BIT NOT NULL CONSTRAINT DF_Tb_BancoTarefaCampo_EChave DEFAULT (0),
        Ultimo_Valor_Sequencial INT NULL CONSTRAINT DF_Tb_BancoTarefaCampo_UltimoSeq DEFAULT (0),
        CONSTRAINT FK_Tb_BancoTarefaCampo_Tarefa FOREIGN KEY (Id_Workflow) REFERENCES intec.dbo.Tb_BancoTarefa (Id_Workflow),
        CONSTRAINT CK_Tb_BancoTarefaCampo_Transformacao CHECK (Tipo_Transformacao IN ('DIRETO', 'TEXTO_MAIUSCULO', 'TEXTO_MINUSCULO', 'TRIM', 'INTEGER', 'DECIMAL', 'BOOLEANO', 'DATA_ISO', 'TEMPLATE', 'VALOR_PADRAO', 'AUTO_SEQUENCIAL'))
    );
    GO

    CREATE TABLE intec.dbo.Tb_BancoExecucao
    (
        Id_Execucao INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Id_Workflow INT NOT NULL,
        Data_Inicio DATETIME2(0) NOT NULL CONSTRAINT DF_Tb_BancoExecucao_DataInicio DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Data_Fim DATETIME2(0) NULL,
        Duracao_Ms INT NULL,
        Status_Execucao VARCHAR(24) NOT NULL,
        Total_Linhas_Origem INT NULL,
        Total_Linhas_Processadas INT NULL,
        Total_Linhas_Escritas INT NULL,
        Mensagem_Resumo NVARCHAR(2000) NULL,
        Erro_Stack NVARCHAR(MAX) NULL,
        Executado_Por NVARCHAR(160) NULL,
        CONSTRAINT FK_Tb_BancoExecucao_Tarefa FOREIGN KEY (Id_Workflow) REFERENCES intec.dbo.Tb_BancoTarefa (Id_Workflow),
        CONSTRAINT CK_Tb_BancoExecucao_Status CHECK (Status_Execucao IN ('EM_EXECUCAO', 'SUCESSO', 'ERRO', 'CANCELADO'))
    );
    GO

    CREATE TABLE intec.dbo.Tb_BancoExecucaoLog
    (
        Id_Execucao_Log INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Id_Execucao INT NOT NULL,
        Etapa_Log NVARCHAR(120) NOT NULL,
        Nivel_Log VARCHAR(24) NOT NULL,
        Mensagem_Log NVARCHAR(2000) NOT NULL,
        Payload_Log NVARCHAR(MAX) NULL,
        Criado_Em DATETIME2(0) NOT NULL CONSTRAINT DF_Tb_BancoExecucaoLog_CriadoEm DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        CONSTRAINT FK_Tb_BancoExecucaoLog_Execucao FOREIGN KEY (Id_Execucao) REFERENCES intec.dbo.Tb_BancoExecucao (Id_Execucao),
        CONSTRAINT CK_Tb_BancoExecucaoLog_Nivel CHECK (Nivel_Log IN ('INFO', 'WARN', 'ERROR', 'DEBUG'))
    );
    GO

    CREATE INDEX IX_Tb_BancoTarefa_Execucao ON intec.dbo.Tb_BancoTarefa (Ativo, Proxima_Execucao_Em);
    CREATE INDEX IX_Tb_BancoTarefaCampo_Tarefa ON intec.dbo.Tb_BancoTarefaCampo (Id_Workflow, Ordem_Execucao);
    CREATE INDEX IX_Tb_BancoExecucao_Tarefa ON intec.dbo.Tb_BancoExecucao (Id_Workflow, Data_Inicio DESC);
    CREATE INDEX IX_Tb_BancoExecucaoLog_Execucao ON intec.dbo.Tb_BancoExecucaoLog (Id_Execucao, Id_Execucao_Log ASC);
    GO
