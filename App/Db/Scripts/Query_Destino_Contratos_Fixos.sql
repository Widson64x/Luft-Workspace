MERGE INTO Luftinforma.dbo.ContaPagarFixo AS Destino

USING (
    SELECT 
        (SELECT TOP 1 Codigo_Empresa FROM LuftInforma.dbo.Empresa 
         WHERE Codigo_Integracao = @{Codigo_Empresa} 
           AND (Codigo_EmpresaMatriz = @{Codigo_EmpresaMatriz} OR Codigo_Empresa = @{Codigo_EmpresaMatriz})) AS Codigo_Empresa,
           
        @{Codigo_EmpresaMatriz} AS Codigo_EmpresaMatriz,
        
        (SELECT TOP 1 Codigo_Fornecedor FROM LuftInforma.dbo.FornecedorIntegracaoSistema
         WHERE Codigo_Integracao = @{Codigo_Integracao} 
           AND Nome_SistemaOrigem = 'MICROSIGA') AS Codigo_Fornecedor,
           
        (SELECT TOP 1 ISNULL(Codigo_ContaContabilPai, Codigo_ContaContabil) 
         FROM LuftInforma.dbo.PlanoConta 
         WHERE Codigo_ContaContabil = TRY_CAST(@{Codigo_ContaContabil} AS NUMERIC(15,0))) AS Codigo_ContaContabil,
         
        (SELECT TOP 1 Codigo_CentroCusto FROM LuftInforma.dbo.CentroCusto 
         WHERE Codigo_CentroCusto = TRY_CAST(@{Codigo_CentroCusto} AS NUMERIC(10,0))) AS Codigo_CentroCusto,
         
        @{Opcao_TipoDocumento} AS Opcao_TipoDocumento,
        @{Numero_Contrato} AS Numero_Contrato,
        @{Sequencia_Item} AS Sequencia_Item,
        @{Codigo_Item} AS Codigo_Item,
        @{Descricao_Item} AS Descricao_Item,
        @{Data_Emissao_Contrato} AS Data_Emissao_Contrato,
        @{Data_Aprovacao} AS Data_Aprovacao,
        @{Valor_Total_Contrato} AS Valor_Total_Contrato,
        @{Qtd_Total_Contratada} AS Qtd_Total_Contratada,
        @{Qtd_Ja_Executada} AS Qtd_Ja_Executada,
        @{Saldo_Disponivel} AS Saldo_Disponivel,
        @{Codigo_Status_SCR} AS Codigo_Status_SCR,
        @{Status_Bloqueio_Protheus} AS Status_Bloqueio_Protheus,
        @{Situacao_Contrato} AS Situacao_Contrato,
        @{Codigo_UltimoAprovador} AS Codigo_UltimoAprovador,
        @{Login_UltimoAprovador} AS Login_UltimoAprovador,
        @{Nome_UltimoAprovador} AS Nome_UltimoAprovador,
        @{Codigo_UsuarioCriador} AS Codigo_UsuarioCriador,
        @{Login_UsuarioCriador} AS Login_UsuarioCriador,
        @{Nome_UsuarioCriador} AS Nome_UsuarioCriador,
        @{Codigo_CondicaoPagamento} AS Codigo_CondicaoPagamento,
        @{DescricaoCondicaoPagamento} AS DescricaoCondicaoPagamento,
        @{Observacao} AS Observacao
) AS Origem 

ON (
    Destino.Codigo_EmpresaMatriz = Origem.Codigo_EmpresaMatriz AND 
    Destino.Numero_Contrato = Origem.Numero_Contrato AND
    Destino.Sequencia_Item = Origem.Sequencia_Item 
)

WHEN MATCHED THEN 
    UPDATE SET 
        Destino.Codigo_Empresa = Origem.Codigo_Empresa,
        Destino.Codigo_Fornecedor = Origem.Codigo_Fornecedor,
        Destino.Codigo_ContaContabil = Origem.Codigo_ContaContabil,
        Destino.Codigo_CentroCusto = Origem.Codigo_CentroCusto,
        Destino.Opcao_TipoDocumento = Origem.Opcao_TipoDocumento,
        Destino.Codigo_Item = Origem.Codigo_Item,
        Destino.Descricao_Item = Origem.Descricao_Item,
        Destino.Data_Emissao_Contrato = Origem.Data_Emissao_Contrato,
        Destino.Data_Aprovacao = Origem.Data_Aprovacao,
        Destino.Valor_Total_Contrato = Origem.Valor_Total_Contrato,
        Destino.Qtd_Total_Contratada = Origem.Qtd_Total_Contratada,
        Destino.Qtd_Ja_Executada = Origem.Qtd_Ja_Executada,
        Destino.Saldo_Disponivel = Origem.Saldo_Disponivel,
        Destino.Codigo_Status_SCR = Origem.Codigo_Status_SCR,
        Destino.Status_Bloqueio_Protheus = Origem.Status_Bloqueio_Protheus,
        Destino.Situacao_Contrato = Origem.Situacao_Contrato,
        Destino.Codigo_UltimoAprovador = Origem.Codigo_UltimoAprovador,
        Destino.Login_UltimoAprovador = Origem.Login_UltimoAprovador,
        Destino.Nome_UltimoAprovador = Origem.Nome_UltimoAprovador,
        Destino.Codigo_UsuarioCriador = Origem.Codigo_UsuarioCriador,
        Destino.Login_UsuarioCriador = Origem.Login_UsuarioCriador,
        Destino.Nome_UsuarioCriador = Origem.Nome_UsuarioCriador,
        Destino.Codigo_CondicaoPagamento = Origem.Codigo_CondicaoPagamento,
        Destino.DescricaoCondicaoPagamento = Origem.DescricaoCondicaoPagamento,
        Destino.Observacao = Origem.Observacao,
        Destino.Data_Importacao = GETDATE()

WHEN NOT MATCHED THEN
    INSERT (
        Codigo_Empresa, Codigo_EmpresaMatriz, Codigo_Fornecedor, Codigo_ContaContabil, Codigo_CentroCusto, 
        Opcao_TipoDocumento, Numero_Contrato, Sequencia_Item, Codigo_Item, Descricao_Item,
        Data_Emissao_Contrato, Data_Aprovacao, Valor_Total_Contrato, Qtd_Total_Contratada, 
        Qtd_Ja_Executada, Saldo_Disponivel, Codigo_Status_SCR, Status_Bloqueio_Protheus, Situacao_Contrato,
        Codigo_UltimoAprovador, Login_UltimoAprovador, Nome_UltimoAprovador,
        Codigo_UsuarioCriador, Login_UsuarioCriador, Nome_UsuarioCriador, 
        Codigo_CondicaoPagamento, DescricaoCondicaoPagamento, Observacao
    ) VALUES (
        Origem.Codigo_Empresa, Origem.Codigo_EmpresaMatriz, Origem.Codigo_Fornecedor, Origem.Codigo_ContaContabil, Origem.Codigo_CentroCusto, 
        Origem.Opcao_TipoDocumento, Origem.Numero_Contrato, Origem.Sequencia_Item, Origem.Codigo_Item, Origem.Descricao_Item,
        Origem.Data_Emissao_Contrato, Origem.Data_Aprovacao, Origem.Valor_Total_Contrato, Origem.Qtd_Total_Contratada, 
        Origem.Qtd_Ja_Executada, Origem.Saldo_Disponivel, Origem.Codigo_Status_SCR, Origem.Status_Bloqueio_Protheus, Origem.Situacao_Contrato,
        Origem.Codigo_UltimoAprovador, Origem.Login_UltimoAprovador, Origem.Nome_UltimoAprovador,
        Origem.Codigo_UsuarioCriador, Origem.Login_UsuarioCriador, Origem.Nome_UsuarioCriador, 
        Origem.Codigo_CondicaoPagamento, Origem.DescricaoCondicaoPagamento, Origem.Observacao
    )