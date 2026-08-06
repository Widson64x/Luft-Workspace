WITH PedidosCombinados AS (
    SELECT 
        1 AS Codigo_EmpresaMatriz, 
        C3_FILIAL, C3_NUM, C3_FORNECE, C3_LOJA, C3_ITEM, C3_PRODUTO,
        C3_QUANT, C3_PRECO, C3_TOTAL, 
        C3_DATPRI AS Data_Inicio_Vigencia,
        C3_DATPRF AS Data_Fim_Vigencia,
        C3_EMISSAO, C3_CC, C3_USER, C3_OBS, C3_MSBLQL, C3_COND,
        C3_QUJE, D_E_L_E_T_
    FROM U_C1JTKS_PR.SC3120
    WHERE D_E_L_E_T_ <> '*' 
      AND C3_EMISSAO >= TO_CHAR(SYSDATE - 365, 'YYYYMMDD')
      AND C3_EMISSAO <= TO_CHAR(SYSDATE, 'YYYYMMDD')
      
    UNION ALL
    
    SELECT 
        2 AS Codigo_EmpresaMatriz, 
        C3_FILIAL, C3_NUM, C3_FORNECE, C3_LOJA, C3_ITEM, C3_PRODUTO,
        C3_QUANT, C3_PRECO, C3_TOTAL, 
        C3_DATPRI AS Data_Inicio_Vigencia,
        C3_DATPRF AS Data_Fim_Vigencia,
        C3_EMISSAO, C3_CC, C3_USER, C3_OBS, C3_MSBLQL, C3_COND,
        C3_QUJE, D_E_L_E_T_
    FROM U_C1JTKS_PR.SC3170
    WHERE D_E_L_E_T_ <> '*'
      AND C3_EMISSAO >= TO_CHAR(SYSDATE - 365, 'YYYYMMDD')
      AND C3_EMISSAO <= TO_CHAR(SYSDATE, 'YYYYMMDD')
),
PedidosRanqueados AS (
    SELECT 
        pc.*,
        ROW_NUMBER() OVER (
            PARTITION BY Codigo_EmpresaMatriz, C3_NUM, C3_ITEM 
            ORDER BY C3_EMISSAO DESC
        ) AS LinhaSequencial
    FROM PedidosCombinados pc
),
Aprovacoes AS (
    SELECT 
        1 AS Codigo_EmpresaMatriz, CR_FILIAL, CR_NUM, CR_USERLIB, CR_DATALIB, CR_STATUS, R_E_C_N_O_
    FROM U_C1JTKS_PR.SCR120 
    WHERE CR_TIPO = 'AE' AND D_E_L_E_T_ <> '*'
    
    UNION ALL
    
    SELECT 
        2 AS Codigo_EmpresaMatriz, CR_FILIAL, CR_NUM, CR_USERLIB, CR_DATALIB, CR_STATUS, R_E_C_N_O_
    FROM U_C1JTKS_PR.SCR170 
    WHERE CR_TIPO = 'AE' AND D_E_L_E_T_ <> '*'
),
PedidosComAprovacao AS (
    SELECT 
        p.*,
        a.CR_USERLIB,
        a.CR_DATALIB,
        ROW_NUMBER() OVER (
            PARTITION BY p.Codigo_EmpresaMatriz, p.C3_FILIAL, p.C3_NUM, p.C3_ITEM 
            ORDER BY a.R_E_C_N_O_ DESC
        ) AS LinhaAprovacao
    FROM PedidosRanqueados p
    LEFT JOIN Aprovacoes a 
           ON a.Codigo_EmpresaMatriz = p.Codigo_EmpresaMatriz 
          AND a.CR_FILIAL = p.C3_FILIAL 
          AND a.CR_NUM = p.C3_NUM
          /* Aceita apenas aprovacoes dos ultimos 2 anos (730 dias) para ignorar numeracoes recicladas antigas */
          AND (a.CR_DATALIB >= TO_CHAR(SYSDATE - 730, 'YYYYMMDD') OR TRIM(a.CR_DATALIB) IS NULL)
    WHERE p.LinhaSequencial = 1 
      AND p.C3_MSBLQL = '2'
),
UsuariosNomes AS (
    SELECT TRIM(USR_ID) AS Codigo_Usuario, TRIM(USR_CODIGO) AS Login_Usuario, TRIM(USR_NOME) AS Nome_Usuario
    FROM U_C1JTKS_PR.SYS_USR WHERE D_E_L_E_T_ <> '*'
)
SELECT 
    pa.Codigo_EmpresaMatriz,
    pa.C3_FILIAL AS Codigo_Empresa,
    
    -- Chave de Integração (Empresa + Fornecedor + Loja) para busca do Fornecedor real no destino
    CAST(pa.Codigo_EmpresaMatriz AS VARCHAR(1)) || TRIM(pa.C3_FORNECE) || TRIM(pa.C3_LOJA) AS Codigo_Integracao,
    
    TRIM(sb.B1_CONTA) AS Codigo_ContaContabil, 
    pa.C3_CC AS Codigo_CentroCusto,
    'AE' AS Opcao_TipoDocumento, 
    pa.C3_NUM AS Numero_Contrato,
    pa.C3_ITEM AS Sequencia_Item,
    TRIM(sb.B1_DESC) AS Descricao_Item,
    
    pa.C3_MSBLQL AS Status,
    pa.C3_USER AS Codigo_UsuarioCriador,
    uc.Login_Usuario AS Login_UsuarioCriador,
    uc.Nome_Usuario AS Nome_UsuarioCriador,
    
    CAST(TRIM(pa.CR_USERLIB) AS INT) AS Codigo_UltimoAprovador,
    uap.Login_Usuario AS Login_UltimoAprovador,
    uap.Nome_Usuario AS Nome_UltimoAprovador,
    
    CASE WHEN TRIM(pa.CR_DATALIB) IS NULL OR LENGTH(TRIM(pa.CR_DATALIB)) < 8 THEN NULL
         ELSE SUBSTR(pa.CR_DATALIB, 1, 4) || '-' || SUBSTR(pa.CR_DATALIB, 5, 2) || '-' || SUBSTR(pa.CR_DATALIB, 7, 2) || ' 00:00:00.000' END AS Data_Aprovacao,
    
    CASE WHEN TRIM(pa.C3_EMISSAO) IS NULL OR LENGTH(TRIM(pa.C3_EMISSAO)) < 8 THEN NULL
         ELSE SUBSTR(pa.C3_EMISSAO, 1, 4) || '-' || SUBSTR(pa.C3_EMISSAO, 5, 2) || '-' || SUBSTR(pa.C3_EMISSAO, 7, 2) || ' 00:00:00.000' END AS Data_Emissao_Contrato,
    
    pa.C3_TOTAL AS Valor_Total_Contrato,
    pa.C3_QUANT AS Qtd_Total_Contratada,
    pa.C3_QUJE AS Qtd_Ja_Executada,
    (pa.C3_QUANT - pa.C3_QUJE) AS Saldo_Disponivel,
    
    pa.C3_COND AS Codigo_CondicaoPagamento,
    s.E4_DESCRI AS Condicao_Descricao,
    pa.C3_OBS AS Observacao
FROM PedidosComAprovacao pa
LEFT JOIN U_C1JTKS_PR.SB1010 sb ON TRIM(sb.B1_COD) = TRIM(pa.C3_PRODUTO) AND sb.D_E_L_E_T_ <> '*'
LEFT JOIN U_C1JTKS_PR.SE4010 s ON s.E4_CODIGO = pa.C3_COND AND s.D_E_L_E_T_ <> '*'
LEFT JOIN UsuariosNomes uc ON uc.Codigo_Usuario = TRIM(pa.C3_USER)
LEFT JOIN UsuariosNomes uap ON uap.Codigo_Usuario = TRIM(pa.CR_USERLIB)
WHERE pa.LinhaAprovacao = 1
ORDER BY pa.C3_EMISSAO DESC, pa.C3_NUM DESC;
