-- O comando MERGE junta INSERT e UPDATE em uma única execução.
-- Ele verifica se a linha existe (via chave primária). Se sim, atualiza. Se não, insere.

-- [ BLOCO 1: O ALVO ]
-- Qual tabela vai receber os dados?

MERGE INTO Luftinforma.dbo.ContaPagarFixo AS Destino

-- [ BLOCO 2: A ORIGEM ]
-- Variáveis @{...} trazem os valores da query de origem.

USING (
    SELECT 
        @{Codigo_EmpresaMatriz} AS Codigo_EmpresaMatriz,
        @{Codigo_Empresa} AS Codigo_Empresa,
        
        -- TRATATIVA: O 'Codigo_Integracao' (Empresa+Forn+Loja) vem da origem.
        -- Usamos ele para buscar o codigo real do fornecedor na base de destino.
        (SELECT TOP 1 Codigo_Fornecedor FROM LuftInforma.dbo.FornecedorIntegracaoSistema
         WHERE Codigo_Integracao = @{Codigo_Integracao}) AS Codigo_Fornecedor,
         
        @{Codigo_ContaContabil} AS Codigo_ContaContabil,
        @{Codigo_CentroCusto} AS Codigo_CentroCusto,
        @{Opcao_TipoDocumento} AS Opcao_TipoDocumento,
        @{Numero_Contrato} AS Numero_Contrato,
        @{Sequencia_Item} AS Sequencia_Item,
        @{Descricao_Item} AS Descricao_Item,
        @{Status} AS Status,
        @{Codigo_UsuarioCriador} AS Codigo_UsuarioCriador,
        @{Login_UsuarioCriador} AS Login_UsuarioCriador,
        @{Nome_UsuarioCriador} AS Nome_UsuarioCriador,
        @{Codigo_UltimoAprovador} AS Codigo_UltimoAprovador,
        @{Login_UltimoAprovador} AS Login_UltimoAprovador,
        @{Nome_UltimoAprovador} AS Nome_UltimoAprovador,
        @{Data_Aprovacao} AS Data_Aprovacao,
        @{Data_Emissao_Contrato} AS Data_Emissao_Contrato,
        @{Valor_Total_Contrato} AS Valor_Total_Contrato,
        @{Qtd_Total_Contratada} AS Qtd_Total_Contratada,
        @{Qtd_Ja_Executada} AS Qtd_Ja_Executada,
        @{Saldo_Disponivel} AS Saldo_Disponivel,
        @{Codigo_CondicaoPagamento} AS Codigo_CondicaoPagamento,
        @{Condicao_Descricao} AS Condicao_Descricao,
        @{Observacao} AS Observacao
) AS Origem 

-- [ BLOCO 3: A CHAVE DE COMPARAÇÃO ]
-- ON: Como sabemos se a linha já existe? Cruzando as chaves primárias.

ON (
    Destino.Codigo_ContaContabil = Origem.Codigo_ContaContabil AND 
    Destino.Numero_Contrato = Origem.Numero_Contrato AND
    Destino.Sequencia_Item = Origem.Sequencia_Item AND
    Destino.Opcao_TipoDocumento = Origem.Opcao_TipoDocumento
)

-- [ BLOCO 4: O QUE FAZER SE JÁ EXISTE (UPDATE) ]
-- WHEN MATCHED THEN: As chaves bateram. Vamos apenas atualizar os dados alteráveis.

WHEN MATCHED THEN 
    UPDATE SET 
        Destino.Codigo_EmpresaMatriz = Origem.Codigo_EmpresaMatriz,
        Destino.Codigo_Empresa = Origem.Codigo_Empresa,
        Destino.Codigo_Fornecedor = Origem.Codigo_Fornecedor,
        Destino.Codigo_CentroCusto = Origem.Codigo_CentroCusto,
        Destino.Descricao_Item = Origem.Descricao_Item,
        Destino.Status = Origem.Status,
        Destino.Codigo_UsuarioCriador = Origem.Codigo_UsuarioCriador,
        Destino.Login_UsuarioCriador = Origem.Login_UsuarioCriador,
        Destino.Nome_UsuarioCriador = Origem.Nome_UsuarioCriador,
        Destino.Codigo_UltimoAprovador = Origem.Codigo_UltimoAprovador,
        Destino.Login_UltimoAprovador = Origem.Login_UltimoAprovador,
        Destino.Nome_UltimoAprovador = Origem.Nome_UltimoAprovador,
        Destino.Data_Aprovacao = Origem.Data_Aprovacao,
        Destino.Data_Emissao_Contrato = Origem.Data_Emissao_Contrato,
        Destino.Valor_Total_Contrato = Origem.Valor_Total_Contrato,
        Destino.Qtd_Total_Contratada = Origem.Qtd_Total_Contratada,
        Destino.Qtd_Ja_Executada = Origem.Qtd_Ja_Executada,
        Destino.Saldo_Disponivel = Origem.Saldo_Disponivel,
        Destino.Codigo_CondicaoPagamento = Origem.Codigo_CondicaoPagamento,
        Destino.Condicao_Descricao = Origem.Condicao_Descricao,
        Destino.Observacao = Origem.Observacao

-- [ BLOCO 5: O QUE FAZER SE FOR NOVO (INSERT) ]
-- WHEN NOT MATCHED THEN: As chaves não bateram. Criamos um registro novo.

WHEN NOT MATCHED THEN
    INSERT (
        Codigo_EmpresaMatriz, Codigo_Empresa, Codigo_Fornecedor, Codigo_ContaContabil,
        Codigo_CentroCusto, Opcao_TipoDocumento, Numero_Contrato, Sequencia_Item, Descricao_Item,
        Status, Codigo_UsuarioCriador, Login_UsuarioCriador, Nome_UsuarioCriador,
        Codigo_UltimoAprovador, Login_UltimoAprovador, Nome_UltimoAprovador, Data_Aprovacao,
        Data_Emissao_Contrato, Valor_Total_Contrato, Qtd_Total_Contratada, Qtd_Ja_Executada,
        Saldo_Disponivel, Codigo_CondicaoPagamento, Condicao_Descricao, Observacao
    ) VALUES (
        Origem.Codigo_EmpresaMatriz, Origem.Codigo_Empresa, Origem.Codigo_Fornecedor, Origem.Codigo_ContaContabil,
        Origem.Codigo_CentroCusto, Origem.Opcao_TipoDocumento, Origem.Numero_Contrato, Origem.Sequencia_Item, Origem.Descricao_Item,
        Origem.Status, Origem.Codigo_UsuarioCriador, Origem.Login_UsuarioCriador, Origem.Nome_UsuarioCriador,
        Origem.Codigo_UltimoAprovador, Origem.Login_UltimoAprovador, Origem.Nome_UltimoAprovador, Origem.Data_Aprovacao,
        Origem.Data_Emissao_Contrato, Origem.Valor_Total_Contrato, Origem.Qtd_Total_Contratada, Origem.Qtd_Ja_Executada,
        Origem.Saldo_Disponivel, Origem.Codigo_CondicaoPagamento, Origem.Condicao_Descricao, Origem.Observacao
    );