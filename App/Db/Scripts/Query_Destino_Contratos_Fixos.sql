MERGE INTO Luftinforma.dbo.ContaPagarFixo AS Destino

USING (
    SELECT * FROM (
        SELECT 
            ISNULL(emp.Codigo_Empresa, ISNULL(TRY_CAST(p.Codigo_Empresa_Param AS INT), 0)) AS Codigo_Empresa,
            p.Codigo_EmpresaMatriz AS Codigo_EmpresaMatriz,
            forn.Codigo_Fornecedor AS Codigo_Fornecedor,
            ISNULL(pc.Codigo_ContaContabilPai, pc.Codigo_ContaContabil) AS Codigo_ContaContabil,
            cc.Codigo_CentroCusto AS Codigo_CentroCusto,
            LEFT(p.Opcao_TipoDocumento, 10) AS Opcao_TipoDocumento,
            LEFT(p.Numero_Contrato, 30) AS Numero_Contrato,
            LEFT(p.Sequencia_Item, 10) AS Sequencia_Item,
            LEFT(p.Codigo_Item, 30) AS Codigo_Item,
            LEFT(p.Descricao_Item, 255) AS Descricao_Item,
            LEFT(p.Unidade_Medida, 10) AS Unidade_Medida,
            LEFT(p.Codigo_Almoxarifado, 10) AS Codigo_Almoxarifado,
            
            TRY_CAST(p.Data_Emissao_Contrato AS DATETIME) AS Data_Emissao_Contrato,
            TRY_CAST(p.Data_Inicio_Vigencia AS DATETIME) AS Data_Inicio_Vigencia,
            TRY_CAST(p.Data_Fim_Vigencia AS DATETIME) AS Data_Fim_Vigencia,
            TRY_CAST(p.Data_Aprovacao AS DATETIME) AS Data_Aprovacao,
            
            TRY_CAST(p.Preco_Unitario AS DECIMAL(18, 4)) AS Preco_Unitario,
            TRY_CAST(p.Valor_Total_Contrato AS DECIMAL(18, 4)) AS Valor_Total_Contrato,
            TRY_CAST(p.Qtd_Total_Contratada AS DECIMAL(18, 4)) AS Qtd_Total_Contratada,
            TRY_CAST(p.Qtd_Ja_Executada AS DECIMAL(18, 4)) AS Qtd_Ja_Executada,
            TRY_CAST(p.Saldo_Disponivel AS DECIMAL(18, 4)) AS Saldo_Disponivel,
            
            LEFT(p.Codigo_Status_SCR, 10) AS Codigo_Status_SCR,
            LEFT(p.Status_Bloqueio_Protheus, 5) AS Status_Bloqueio_Protheus,
            LEFT(p.Situacao_Contrato, 100) AS Situacao_Contrato,
            
            LEFT(p.Codigo_UltimoAprovador, 30) AS Codigo_UltimoAprovador,
            LEFT(p.Login_UltimoAprovador, 100) AS Login_UltimoAprovador,
            LEFT(p.Nome_UltimoAprovador, 150) AS Nome_UltimoAprovador,
            
            LEFT(p.Codigo_UsuarioCriador, 30) AS Codigo_UsuarioCriador,
            LEFT(p.Login_UsuarioCriador, 100) AS Login_UsuarioCriador,
            LEFT(p.Nome_UsuarioCriador, 150) AS Nome_UsuarioCriador,
            
            LEFT(p.Numero_Contrato_Juridico, 120) AS Numero_Contrato_Juridico,
            LEFT(p.Codigo_Gestor, 30) AS Codigo_Gestor,
            LEFT(p.Nome_Gestor, 100) AS Nome_Gestor,
            LEFT(p.Codigo_Solicitante, 30) AS Codigo_Solicitante,
            LEFT(p.Nome_Solicitante, 100) AS Nome_Solicitante,
            LEFT(p.Dia_Vencimento_NF, 10) AS Dia_Vencimento_NF,
            
            LEFT(p.Codigo_CondicaoPagamento, 10) AS Codigo_CondicaoPagamento,
            LEFT(p.DescricaoCondicaoPagamento, 150) AS DescricaoCondicaoPagamento,
            p.Observacao,
            ROW_NUMBER() OVER (
                PARTITION BY p.Codigo_EmpresaMatriz, p.Numero_Contrato, p.Sequencia_Item 
                ORDER BY p.Data_Emissao_Contrato DESC
            ) AS RowNum_Dedup
        FROM (
            SELECT 
                @{Codigo_Empresa} AS Codigo_Empresa_Param,
                @{Codigo_EmpresaMatriz} AS Codigo_EmpresaMatriz,
                @{Codigo_Integracao} AS Codigo_Integracao,
                @{Codigo_ContaContabil} AS Codigo_ContaContabil_Param,
                @{Codigo_CentroCusto} AS Codigo_CentroCusto_Param,
                @{Opcao_TipoDocumento} AS Opcao_TipoDocumento,
                @{Numero_Contrato} AS Numero_Contrato,
                @{Sequencia_Item} AS Sequencia_Item,
                @{Codigo_Item} AS Codigo_Item,
                @{Descricao_Item} AS Descricao_Item,
                @{Unidade_Medida} AS Unidade_Medida,
                @{Codigo_Almoxarifado} AS Codigo_Almoxarifado,
                @{Data_Emissao_Contrato} AS Data_Emissao_Contrato,
                @{Data_Inicio_Vigencia} AS Data_Inicio_Vigencia,
                @{Data_Fim_Vigencia} AS Data_Fim_Vigencia,
                @{Data_Aprovacao} AS Data_Aprovacao,
                @{Preco_Unitario} AS Preco_Unitario,
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
                @{Numero_Contrato_Juridico} AS Numero_Contrato_Juridico,
                @{Codigo_Gestor} AS Codigo_Gestor,
                @{Nome_Gestor} AS Nome_Gestor,
                @{Codigo_Solicitante} AS Codigo_Solicitante,
                @{Nome_Solicitante} AS Nome_Solicitante,
                @{Dia_Vencimento_NF} AS Dia_Vencimento_NF,
                @{Codigo_CondicaoPagamento} AS Codigo_CondicaoPagamento,
                @{DescricaoCondicaoPagamento} AS DescricaoCondicaoPagamento,
                @{Observacao} AS Observacao
        ) p
        OUTER APPLY (
            SELECT TOP 1 Codigo_Empresa 
            FROM LuftInforma.dbo.Empresa 
            WHERE Codigo_Integracao = p.Codigo_Empresa_Param 
              AND (Codigo_EmpresaMatriz = p.Codigo_EmpresaMatriz OR Codigo_Empresa = p.Codigo_EmpresaMatriz)
        ) emp
        OUTER APPLY (
            SELECT TOP 1 Codigo_Fornecedor 
            FROM LuftInforma.dbo.FornecedorIntegracaoSistema
            WHERE Codigo_Integracao = p.Codigo_Integracao 
              AND Nome_SistemaOrigem = 'MICROSIGA'
        ) forn
        OUTER APPLY (
            SELECT TOP 1 Codigo_ContaContabilPai, Codigo_ContaContabil 
            FROM LuftInforma.dbo.PlanoConta 
            WHERE Codigo_ContaContabil = TRY_CAST(p.Codigo_ContaContabil_Param AS NUMERIC(15,0))
        ) pc
        OUTER APPLY (
            SELECT TOP 1 Codigo_CentroCusto 
            FROM LuftInforma.dbo.CentroCusto 
            WHERE Codigo_CentroCusto = TRY_CAST(p.Codigo_CentroCusto_Param AS NUMERIC(10,0))
        ) cc
    ) sub
    WHERE sub.RowNum_Dedup = 1
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
        Destino.Unidade_Medida = Origem.Unidade_Medida,
        Destino.Codigo_Almoxarifado = Origem.Codigo_Almoxarifado,
        Destino.Data_Emissao_Contrato = Origem.Data_Emissao_Contrato,
        Destino.Data_Inicio_Vigencia = Origem.Data_Inicio_Vigencia,
        Destino.Data_Fim_Vigencia = Origem.Data_Fim_Vigencia,
        Destino.Data_Aprovacao = Origem.Data_Aprovacao,
        Destino.Preco_Unitario = Origem.Preco_Unitario,
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
        Destino.Numero_Contrato_Juridico = Origem.Numero_Contrato_Juridico,
        Destino.Codigo_Gestor = Origem.Codigo_Gestor,
        Destino.Nome_Gestor = Origem.Nome_Gestor,
        Destino.Codigo_Solicitante = Origem.Codigo_Solicitante,
        Destino.Nome_Solicitante = Origem.Nome_Solicitante,
        Destino.Dia_Vencimento_NF = Origem.Dia_Vencimento_NF,
        Destino.Codigo_CondicaoPagamento = Origem.Codigo_CondicaoPagamento,
        Destino.DescricaoCondicaoPagamento = Origem.DescricaoCondicaoPagamento,
        Destino.Observacao = Origem.Observacao,
        Destino.Data_Importacao = GETDATE()

WHEN NOT MATCHED THEN
    INSERT (
        Codigo_Empresa, Codigo_EmpresaMatriz, Codigo_Fornecedor, Codigo_ContaContabil, Codigo_CentroCusto, 
        Opcao_TipoDocumento, Numero_Contrato, Sequencia_Item, Codigo_Item, Descricao_Item, Unidade_Medida, Codigo_Almoxarifado,
        Data_Emissao_Contrato, Data_Inicio_Vigencia, Data_Fim_Vigencia, Data_Aprovacao,
        Preco_Unitario, Valor_Total_Contrato, Qtd_Total_Contratada, Qtd_Ja_Executada, Saldo_Disponivel,
        Codigo_Status_SCR, Status_Bloqueio_Protheus, Situacao_Contrato,
        Codigo_UltimoAprovador, Login_UltimoAprovador, Nome_UltimoAprovador,
        Codigo_UsuarioCriador, Login_UsuarioCriador, Nome_UsuarioCriador,
        Numero_Contrato_Juridico, Codigo_Gestor, Nome_Gestor, Codigo_Solicitante, Nome_Solicitante, Dia_Vencimento_NF,
        Codigo_CondicaoPagamento, DescricaoCondicaoPagamento, Observacao
    ) VALUES (
        Origem.Codigo_Empresa, Origem.Codigo_EmpresaMatriz, Origem.Codigo_Fornecedor, Origem.Codigo_ContaContabil, Origem.Codigo_CentroCusto, 
        Origem.Opcao_TipoDocumento, Origem.Numero_Contrato, Origem.Sequencia_Item, Origem.Codigo_Item, Origem.Descricao_Item, Origem.Unidade_Medida, Origem.Codigo_Almoxarifado,
        Origem.Data_Emissao_Contrato, Origem.Data_Inicio_Vigencia, Origem.Data_Fim_Vigencia, Origem.Data_Aprovacao,
        Origem.Preco_Unitario, Origem.Valor_Total_Contrato, Origem.Qtd_Total_Contratada, Origem.Qtd_Ja_Executada, Origem.Saldo_Disponivel,
        Origem.Codigo_Status_SCR, Origem.Status_Bloqueio_Protheus, Origem.Situacao_Contrato,
        Origem.Codigo_UltimoAprovador, Origem.Login_UltimoAprovador, Origem.Nome_UltimoAprovador,
        Origem.Codigo_UsuarioCriador, Origem.Login_UsuarioCriador, Origem.Nome_UsuarioCriador,
        Origem.Numero_Contrato_Juridico, Origem.Codigo_Gestor, Origem.Nome_Gestor, Origem.Codigo_Solicitante, Origem.Nome_Solicitante, Origem.Dia_Vencimento_NF,
        Origem.Codigo_CondicaoPagamento, Origem.DescricaoCondicaoPagamento, Origem.Observacao
    );