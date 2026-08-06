USE Luftinforma;
GO

-- 1. DELETA A TABELA (E SEUS ÍNDICES)
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'ContaPagarFixo' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    DROP TABLE dbo.ContaPagarFixo;
    PRINT 'Tabela ContaPagarFixo antiga removida com sucesso!';
END
GO

-- 2. CRIA A TABELA PADRONIZADA COM CAMPOS ESSENCIAIS DO PROTHEUS
CREATE TABLE dbo.ContaPagarFixo (
    Codigo_ContaPagarFixo INT IDENTITY(1,1) NOT NULL,
    Codigo_Empresa INT NULL,           
    Codigo_EmpresaMatriz INT NOT NULL,
    Codigo_Fornecedor INT NULL,        
    Codigo_ContaContabil NUMERIC(15,0) NULL, 
    Codigo_CentroCusto NUMERIC(10,0) NULL,
    Opcao_TipoDocumento VARCHAR(10) NULL,
    Numero_Contrato VARCHAR(30) NOT NULL,
    Sequencia_Item VARCHAR(10) NOT NULL,
    Codigo_Item VARCHAR(30) NULL,
    Descricao_Item VARCHAR(255) NULL,
    Unidade_Medida VARCHAR(10) NULL,
    Codigo_Almoxarifado VARCHAR(10) NULL,
    
    Data_Emissao_Contrato DATETIME NULL,
    Data_Inicio_Vigencia DATETIME NULL,
    Data_Fim_Vigencia DATETIME NULL,
    Data_Aprovacao DATETIME NULL,
    
    Preco_Unitario DECIMAL(18, 4) NULL,
    Valor_Total_Contrato DECIMAL(18, 4) NULL,
    Qtd_Total_Contratada DECIMAL(18, 4) NULL,
    Qtd_Ja_Executada DECIMAL(18, 4) NULL,
    Saldo_Disponivel DECIMAL(18, 4) NULL,
    
    Codigo_Status_SCR VARCHAR(10) NULL,
    Status_Bloqueio_Protheus VARCHAR(5) NULL,
    Situacao_Contrato VARCHAR(100) NULL,
    
    Codigo_UltimoAprovador VARCHAR(30) NULL,
    Login_UltimoAprovador VARCHAR(100) NULL,
    Nome_UltimoAprovador VARCHAR(150) NULL,
    
    Codigo_UsuarioCriador VARCHAR(30) NULL,
    Login_UsuarioCriador VARCHAR(100) NULL,
    Nome_UsuarioCriador VARCHAR(150) NULL,
    
    Numero_Contrato_Juridico VARCHAR(120) NULL,
    Codigo_Gestor VARCHAR(30) NULL,
    Nome_Gestor VARCHAR(100) NULL,
    Codigo_Solicitante VARCHAR(30) NULL,
    Nome_Solicitante VARCHAR(100) NULL,
    Dia_Vencimento_NF VARCHAR(10) NULL,
    
    Codigo_CondicaoPagamento VARCHAR(10) NULL,
    DescricaoCondicaoPagamento VARCHAR(150) NULL,
    Observacao VARCHAR(MAX) NULL,
    Data_Importacao DATETIME CONSTRAINT DF_ContaPagarFixo_DataImportacao DEFAULT GETDATE(),

    CONSTRAINT PK_ContaPagarFixo PRIMARY KEY CLUSTERED (Codigo_ContaPagarFixo ASC)
);
GO

-- 3. ÍNDICES DE PERFORMANCE CORRIGIDOS

-- Índice Único cobrindo a chave tríplice exata do MERGE
CREATE UNIQUE NONCLUSTERED INDEX IX_ContaPagarFixo_ChaveMerge
ON dbo.ContaPagarFixo (Codigo_EmpresaMatriz, Numero_Contrato, Sequencia_Item)
INCLUDE (Codigo_Empresa, Codigo_Fornecedor, Codigo_ContaContabil, Codigo_CentroCusto, Valor_Total_Contrato, Saldo_Disponivel);

CREATE NONCLUSTERED INDEX IX_ContaPagarFixo_Fornecedor
ON dbo.ContaPagarFixo (Codigo_Fornecedor) INCLUDE (Codigo_Empresa, Valor_Total_Contrato, Saldo_Disponivel);

CREATE NONCLUSTERED INDEX IX_ContaPagarFixo_DataEmissao
ON dbo.ContaPagarFixo (Data_Emissao_Contrato DESC);

CREATE NONCLUSTERED INDEX IX_ContaPagarFixo_Empresa_CC
ON dbo.ContaPagarFixo (Codigo_Empresa, Codigo_CentroCusto);

PRINT 'Tabela ContaPagarFixo e Índices atualizados com sucesso!';
GO
