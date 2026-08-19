/*
    Estrutura da central de notificacoes e trilha de auditoria.
    As tabelas ficam em intec.dbo e suportam:
    - Notificacoes sistemicas e por usuario
    - Eventos de auditoria com snapshots before/after
    - Indices otimizados para consultas frequentes
    
    Autor: LuftCore Framework
    Data: 2026-08-17
*/

-- ============================================================
-- 1. TABELA DE NOTIFICACOES
-- ============================================================

IF OBJECT_ID('intec.dbo.Tb_Notificacao', 'U') IS NULL
BEGIN
    CREATE TABLE intec.dbo.Tb_Notificacao
    (
        Id_Notificacao      BIGINT IDENTITY(1,1)  NOT NULL PRIMARY KEY,
        Id_Sistema          INT                   NULL,
        Id_Usuario_Destino  INT                   NULL,
        Tipo                NVARCHAR(20)          NOT NULL CONSTRAINT DF_Tb_Notificacao_Tipo DEFAULT ('INFO'),
        Categoria           NVARCHAR(50)          NOT NULL CONSTRAINT DF_Tb_Notificacao_Categoria DEFAULT ('GERAL'),
        Titulo              NVARCHAR(200)         NOT NULL,
        Mensagem            NVARCHAR(MAX)         NOT NULL,
        Icone               NVARCHAR(100)         NULL,
        Lida                BIT                   NOT NULL CONSTRAINT DF_Tb_Notificacao_Lida DEFAULT (0),
        Data_Criacao        DATETIME2(0)          NOT NULL CONSTRAINT DF_Tb_Notificacao_DataCriacao DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Data_Leitura        DATETIME2(0)          NULL,
        Criado_Por          NVARCHAR(150)         NOT NULL CONSTRAINT DF_Tb_Notificacao_CriadoPor DEFAULT ('SISTEMA'),
        Metadados_Json      NVARCHAR(MAX)         NULL,
        Expira_Em           DATETIME2(0)          NULL,

        CONSTRAINT FK_Tb_Notificacao_Sistema FOREIGN KEY (Id_Sistema)
            REFERENCES intec.dbo.Tb_Sistema(Id_Sistema),

        CONSTRAINT CK_Tb_Notificacao_Tipo CHECK (Tipo IN ('SISTEMA', 'ALERTA', 'INFO', 'SUCESSO', 'ERRO')),
        CONSTRAINT CK_Tb_Notificacao_Categoria CHECK (Categoria IN ('ETL', 'SEGURANCA', 'BANCO', 'SERVICO', 'GERAL', 'USUARIO', 'CONFIGURACAO', 'INTEGRACAO'))
    );

    PRINT 'Tabela intec.dbo.Tb_Notificacao criada com sucesso.';
END
ELSE
BEGIN
    PRINT 'Tabela intec.dbo.Tb_Notificacao ja existe.';
END
GO

-- Indice principal: busca de notificacoes por usuario, status de leitura e data
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_Notificacao_Usuario_Lida_Data' AND object_id = OBJECT_ID('intec.dbo.Tb_Notificacao'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_Notificacao_Usuario_Lida_Data
    ON intec.dbo.Tb_Notificacao (Id_Usuario_Destino, Lida, Data_Criacao DESC)
    INCLUDE (Tipo, Categoria, Titulo, Icone);
    
    PRINT 'Indice IX_Tb_Notificacao_Usuario_Lida_Data criado.';
END
GO

-- Indice para limpeza de notificacoes expiradas
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_Notificacao_Expiracao' AND object_id = OBJECT_ID('intec.dbo.Tb_Notificacao'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_Notificacao_Expiracao
    ON intec.dbo.Tb_Notificacao (Expira_Em)
    WHERE Expira_Em IS NOT NULL;
    
    PRINT 'Indice IX_Tb_Notificacao_Expiracao criado.';
END
GO

-- Indice para filtro por sistema
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_Notificacao_Sistema' AND object_id = OBJECT_ID('intec.dbo.Tb_Notificacao'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_Notificacao_Sistema
    ON intec.dbo.Tb_Notificacao (Id_Sistema, Data_Criacao DESC);
    
    PRINT 'Indice IX_Tb_Notificacao_Sistema criado.';
END
GO


-- ============================================================
-- 2. TABELA DE AUDITORIA (AUDIT TRAIL)
-- ============================================================

IF OBJECT_ID('intec.dbo.Tb_AuditoriaEvento', 'U') IS NULL
BEGIN
    CREATE TABLE intec.dbo.Tb_AuditoriaEvento
    (
        Id_Evento               BIGINT IDENTITY(1,1)  NOT NULL PRIMARY KEY,
        Id_Sistema              INT                   NOT NULL,
        Id_LogAcesso            INT                   NULL,
        Id_Usuario              INT                   NULL,
        Nome_Usuario            NVARCHAR(150)         NULL,
        Acao                    NVARCHAR(30)          NOT NULL,
        Recurso                 NVARCHAR(80)          NOT NULL,
        Id_Recurso              NVARCHAR(100)         NULL,
        Descricao               NVARCHAR(500)         NOT NULL,
        Dados_Anteriores_Json   NVARCHAR(MAX)         NULL,
        Dados_Novos_Json        NVARCHAR(MAX)         NULL,
        Ip_Origem               NVARCHAR(50)          NULL,
        User_Agent              NVARCHAR(500)         NULL,
        Data_Hora               DATETIME2(0)          NOT NULL CONSTRAINT DF_Tb_AuditoriaEvento_DataHora DEFAULT (DATEADD(hour, -3, SYSUTCDATETIME())),
        Severidade              NVARCHAR(20)          NOT NULL CONSTRAINT DF_Tb_AuditoriaEvento_Severidade DEFAULT ('BAIXA'),

        CONSTRAINT FK_Tb_AuditoriaEvento_Sistema FOREIGN KEY (Id_Sistema)
            REFERENCES intec.dbo.Tb_Sistema(Id_Sistema),
            
        CONSTRAINT FK_Tb_AuditoriaEvento_LogAcesso FOREIGN KEY (Id_LogAcesso)
            REFERENCES intec.dbo.Tb_LogAcesso(Id_Log),

        CONSTRAINT CK_Tb_AuditoriaEvento_Acao CHECK (Acao IN ('CRIAR', 'EDITAR', 'EXCLUIR', 'EXECUTAR', 'CONFIGURAR', 'LOGIN', 'LOGOUT', 'IMPORTAR', 'EXPORTAR')),
        CONSTRAINT CK_Tb_AuditoriaEvento_Severidade CHECK (Severidade IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA'))
    );

    PRINT 'Tabela intec.dbo.Tb_AuditoriaEvento criada com sucesso.';
END
ELSE
BEGIN
    PRINT 'Tabela intec.dbo.Tb_AuditoriaEvento ja existe.';
END
GO

-- Indice principal: busca por sistema e data
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_AuditoriaEvento_Sistema_Data' AND object_id = OBJECT_ID('intec.dbo.Tb_AuditoriaEvento'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_AuditoriaEvento_Sistema_Data
    ON intec.dbo.Tb_AuditoriaEvento (Id_Sistema, Data_Hora DESC)
    INCLUDE (Acao, Recurso, Nome_Usuario, Severidade);
    
    PRINT 'Indice IX_Tb_AuditoriaEvento_Sistema_Data criado.';
END
GO

-- Indice para timeline de recurso especifico
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_AuditoriaEvento_Recurso' AND object_id = OBJECT_ID('intec.dbo.Tb_AuditoriaEvento'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_AuditoriaEvento_Recurso
    ON intec.dbo.Tb_AuditoriaEvento (Recurso, Id_Recurso, Data_Hora DESC);
    
    PRINT 'Indice IX_Tb_AuditoriaEvento_Recurso criado.';
END
GO

-- Indice para filtro por usuario
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_AuditoriaEvento_Usuario' AND object_id = OBJECT_ID('intec.dbo.Tb_AuditoriaEvento'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_AuditoriaEvento_Usuario
    ON intec.dbo.Tb_AuditoriaEvento (Id_Usuario, Data_Hora DESC);
    
    PRINT 'Indice IX_Tb_AuditoriaEvento_Usuario criado.';
END
GO

-- Indice para filtro por severidade
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Tb_AuditoriaEvento_Severidade' AND object_id = OBJECT_ID('intec.dbo.Tb_AuditoriaEvento'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_Tb_AuditoriaEvento_Severidade
    ON intec.dbo.Tb_AuditoriaEvento (Severidade, Data_Hora DESC)
    WHERE Severidade IN ('ALTA', 'CRITICA');
    
    PRINT 'Indice IX_Tb_AuditoriaEvento_Severidade criado.';
END
GO


-- ============================================================
-- 3. PERMISSOES DE NOTIFICACOES E AUDITORIA
--    Reutiliza os slots reservados (IDs 12, 13, 14)
-- ============================================================

-- ID 12: Notificacoes — Visualizar (era ADMIN.RESERVA.SET_12)
UPDATE intec.dbo.Tb_Permissao
SET Chave_Permissao     = 'ADMIN.NOTIFICACOES.VISUALIZAR',
    Descricao_Permissao = 'Visualizar o painel de notificacoes sistemicas do ecossistema.',
    Categoria_Permissao = 'ADMINISTRACAO'
WHERE Id_Permissao = 12
  AND Chave_Permissao = 'ADMIN.RESERVA.SET_12';

IF @@ROWCOUNT > 0
    PRINT 'Permissao ID 12 atualizada: ADMIN.NOTIFICACOES.VISUALIZAR';
ELSE
    PRINT 'Permissao ID 12 ja foi atualizada ou nao encontrada.';
GO

-- ID 13: Auditoria — Visualizar (era ADMIN.RESERVA.SET_13)
UPDATE intec.dbo.Tb_Permissao
SET Chave_Permissao     = 'ADMIN.AUDITORIA.VISUALIZAR',
    Descricao_Permissao = 'Visualizar a trilha de auditoria de todos os sistemas do ecossistema.',
    Categoria_Permissao = 'ADMINISTRACAO'
WHERE Id_Permissao = 13
  AND Chave_Permissao = 'ADMIN.RESERVA.SET_13';

IF @@ROWCOUNT > 0
    PRINT 'Permissao ID 13 atualizada: ADMIN.AUDITORIA.VISUALIZAR';
ELSE
    PRINT 'Permissao ID 13 ja foi atualizada ou nao encontrada.';
GO

-- ID 14: Auditoria — Exportar (era ADMIN.RESERVA.SET_14)
UPDATE intec.dbo.Tb_Permissao
SET Chave_Permissao     = 'ADMIN.AUDITORIA.EXPORTAR',
    Descricao_Permissao = 'Exportar logs da trilha de auditoria em formato CSV ou JSON.',
    Categoria_Permissao = 'ADMINISTRACAO'
WHERE Id_Permissao = 14
  AND Chave_Permissao = 'ADMIN.RESERVA.SET_14';

IF @@ROWCOUNT > 0
    PRINT 'Permissao ID 14 atualizada: ADMIN.AUDITORIA.EXPORTAR';
ELSE
    PRINT 'Permissao ID 14 ja foi atualizada ou nao encontrada.';
GO


PRINT '';
PRINT '====================================================';
PRINT '  Estrutura de Notificacoes e Auditoria concluida!  ';
PRINT '====================================================';
GO
