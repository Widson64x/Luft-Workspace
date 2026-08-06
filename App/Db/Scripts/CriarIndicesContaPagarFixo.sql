-- ============================================================================
-- SCRIPT DE CRIAÇÃO DE ÍNDICES DE ALTA PERFORMANCE PARA ContaPagarFixo
-- Banco de Dados: LuftInforma (SQL Server)
-- Objetivo: Acelerar a execução do MERGE e otimizar pesquisas no dashboard
-- ============================================================================

USE LuftInforma;
GO

-- 1. Índice único de busca cobrindo a chave da cláusula ON do MERGE
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_ContaPagarFixo_ChaveMerge' AND object_id = OBJECT_ID('LuftInforma.dbo.ContaPagarFixo'))
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_ContaPagarFixo_ChaveMerge
    ON LuftInforma.dbo.ContaPagarFixo (Codigo_EmpresaMatriz, Numero_Contrato, Sequencia_Item)
    INCLUDE (
        Codigo_Empresa, 
        Codigo_Fornecedor, 
        Codigo_ContaContabil, 
        Codigo_CentroCusto, 
        Valor_Total_Contrato, 
        Saldo_Disponivel, 
        Data_Emissao_Contrato, 
        Data_Importacao
    );
    PRINT 'Índice UX_ContaPagarFixo_ChaveMerge criado com sucesso.';
END;
GO

-- 2. Índice secundário para pesquisas operacionais por Fornecedor e Empresa
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ContaPagarFixo_FornecedorEmpresa' AND object_id = OBJECT_ID('LuftInforma.dbo.ContaPagarFixo'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_ContaPagarFixo_FornecedorEmpresa
    ON LuftInforma.dbo.ContaPagarFixo (Codigo_Fornecedor, Codigo_Empresa)
    INCLUDE (Numero_Contrato, Sequencia_Item, Valor_Total_Contrato, Situacao_Contrato);
    PRINT 'Índice IX_ContaPagarFixo_FornecedorEmpresa criado com sucesso.';
END;
GO
