WITH 
ContratosCombinados AS (
    SELECT 
        1 AS Codigo_EmpresaMatriz, '1' AS Prefixo_Integracao,
        C3_FILIAL, C3_NUM, C3_FORNECE, C3_LOJA, C3_ITEM, C3_PRODUTO,
        C3_QUANT, C3_PRECO, C3_TOTAL, C3_DATPRI AS Data_Inicio_Vigencia,
        C3_DATPRF AS Data_Fim_Vigencia, C3_EMISSAO, C3_CC, C3_USER, C3_OBS, C3_MSBLQL, C3_COND,
        C3_QUJE, D_E_L_E_T_
    FROM U_C1JTKS_PR.SC3120
    WHERE D_E_L_E_T_ <> '*' 
      -- AND C3_EMISSAO >= TO_CHAR(SYSDATE - 365, 'YYYYMMDD') 
      -- AND C3_EMISSAO <= TO_CHAR(SYSDATE, 'YYYYMMDD')
    UNION ALL
    SELECT 
        2 AS Codigo_EmpresaMatriz, '2' AS Prefixo_Integracao,
        C3_FILIAL, C3_NUM, C3_FORNECE, C3_LOJA, C3_ITEM, C3_PRODUTO,
        C3_QUANT, C3_PRECO, C3_TOTAL, C3_DATPRI AS Data_Inicio_Vigencia,
        C3_DATPRF AS Data_Fim_Vigencia, C3_EMISSAO, C3_CC, C3_USER, C3_OBS, C3_MSBLQL, C3_COND,
        C3_QUJE, D_E_L_E_T_
    FROM U_C1JTKS_PR.SC3170
    WHERE D_E_L_E_T_ <> '*'
      -- AND C3_EMISSAO >= TO_CHAR(SYSDATE - 365, 'YYYYMMDD') 
      -- AND C3_EMISSAO <= TO_CHAR(SYSDATE, 'YYYYMMDD')
),
ContratosRanqueados AS (
    SELECT cc.*, ROW_NUMBER() OVER (PARTITION BY Codigo_EmpresaMatriz, C3_NUM, C3_ITEM ORDER BY C3_EMISSAO DESC) AS LinhaSequencial
    FROM ContratosCombinados cc
),
Aprovacoes AS (
    SELECT 1 AS Codigo_EmpresaMatriz, CR_FILIAL, CR_NUM, CR_TIPO, CR_USERLIB, CR_DATALIB, CR_STATUS, R_E_C_N_O_ FROM U_C1JTKS_PR.SCR120 WHERE CR_TIPO = 'AE' AND D_E_L_E_T_ <> '*'
    UNION ALL
    SELECT 2 AS Codigo_EmpresaMatriz, CR_FILIAL, CR_NUM, CR_TIPO, CR_USERLIB, CR_DATALIB, CR_STATUS, R_E_C_N_O_ FROM U_C1JTKS_PR.SCR170 WHERE CR_TIPO = 'AE' AND D_E_L_E_T_ <> '*'
),
ContratosComAprovacao AS (
    SELECT cr.*, a.CR_TIPO, a.CR_USERLIB, a.CR_DATALIB, a.CR_STATUS,
        ROW_NUMBER() OVER (PARTITION BY cr.Codigo_EmpresaMatriz, cr.C3_FILIAL, cr.C3_NUM, cr.C3_ITEM ORDER BY a.R_E_C_N_O_ DESC) AS LinhaAprovacao
    FROM ContratosRanqueados cr
    LEFT JOIN Aprovacoes a ON a.Codigo_EmpresaMatriz = cr.Codigo_EmpresaMatriz AND a.CR_FILIAL = cr.C3_FILIAL AND a.CR_NUM = cr.C3_NUM
          AND (a.CR_DATALIB >= TO_CHAR(SYSDATE - 730, 'YYYYMMDD') OR TRIM(a.CR_DATALIB) IS NULL)
    WHERE cr.LinhaSequencial = 1 
),
UsuariosNomes AS (
    SELECT TRIM(USR_ID) AS Codigo_Usuario, TRIM(USR_CODIGO) AS Login_Usuario, TRIM(USR_NOME) AS Nome_Usuario FROM U_C1JTKS_PR.SYS_USR WHERE D_E_L_E_T_ <> '*'
)
-- ============================================================================
-- SELECT PRINCIPAL (ORDENADO CONFORME NOVA TABELA)
-- ============================================================================
SELECT 
    TRIM(ca.C3_FILIAL) AS Codigo_Empresa,
    ca.Codigo_EmpresaMatriz,
    ca.C3_FORNECE AS Codigo_Fornecedor,
    ca.C3_LOJA AS Loja_Fornecedor,
    ca.Prefixo_Integracao || TRIM(ca.C3_FORNECE) || TRIM(ca.C3_LOJA) AS Codigo_Integracao,
    
    CASE WHEN TRIM(sb.B1_CONTA) IS NULL OR TRIM(sb.B1_CONTA) = '' THEN '1' ELSE TRIM(sb.B1_CONTA) END AS Codigo_ContaContabil, 
    CASE WHEN TRIM(ca.C3_CC) IS NULL OR TRIM(ca.C3_CC) = '' THEN NULL ELSE TRIM(ca.C3_CC) END AS Codigo_CentroCusto,
    
    ca.CR_TIPO AS Opcao_TipoDocumento,
    ca.C3_NUM AS Numero_Contrato,
    ca.C3_ITEM AS Sequencia_Item,
    TRIM(ca.C3_PRODUTO) AS Codigo_Item,
    TRIM(sb.B1_DESC) AS Descricao_Item,
    
    CASE WHEN TRIM(ca.C3_EMISSAO) IS NULL OR LENGTH(TRIM(ca.C3_EMISSAO)) < 8 THEN NULL ELSE SUBSTR(ca.C3_EMISSAO, 1, 4) || '-' || SUBSTR(ca.C3_EMISSAO, 5, 2) || '-' || SUBSTR(ca.C3_EMISSAO, 7, 2) || ' 00:00:00.000' END AS Data_Emissao_Contrato,
    CASE WHEN TRIM(ca.CR_DATALIB) IS NULL OR LENGTH(TRIM(ca.CR_DATALIB)) < 8 THEN NULL ELSE SUBSTR(ca.CR_DATALIB, 1, 4) || '-' || SUBSTR(ca.CR_DATALIB, 5, 2) || '-' || SUBSTR(ca.CR_DATALIB, 7, 2) || ' 00:00:00.000' END AS Data_Aprovacao,
    
    ca.C3_TOTAL AS Valor_Total_Contrato,
    ca.C3_QUANT AS Qtd_Total_Contratada,
    ca.C3_QUJE AS Qtd_Ja_Executada,
    (ca.C3_QUANT - ca.C3_QUJE) AS Saldo_Disponivel,
    
    ca.CR_STATUS AS Codigo_Status_SCR,
    ca.C3_MSBLQL AS Status_Bloqueio_Protheus,
    CASE 
        WHEN ca.C3_MSBLQL = '1' AND ca.CR_STATUS IN ('01', '02', '04') THEN 'PENDENTE DE APROVAÇÃO'
        WHEN ca.C3_MSBLQL = '1' AND ca.CR_STATUS IN ('06', '07') THEN 'REJEITADO / BLOQUEADO'
        WHEN ca.C3_MSBLQL = '2' AND ca.CR_STATUS = '03' THEN 'LIBERADO'
        WHEN ca.C3_MSBLQL = '2' AND ca.CR_STATUS = '05' THEN 'LIBERADO (OUTRO APROV. / SISTEMA)'
        WHEN ca.C3_MSBLQL = '2' THEN 'LIBERADO (DIRETO / SEM ALÇADA)'
        WHEN ca.C3_MSBLQL = '1' THEN 'BLOQUEADO'
        ELSE 'SITUAÇÃO DESCONHECIDA'
    END AS Situacao_Contrato,
    
    TRIM(ca.CR_USERLIB) AS Codigo_UltimoAprovador,
    uap.Login_Usuario AS Login_UltimoAprovador,
    CASE 
        WHEN TRIM(ca.CR_USERLIB) IS NOT NULL AND uap.Nome_Usuario IS NOT NULL THEN uap.Nome_Usuario
        WHEN ca.C3_MSBLQL = '1' THEN 'AGUARDANDO APROVAÇÃO'
        ELSE 'APROVAÇÃO AUTOMÁTICA/SISTEMA'
    END AS Nome_UltimoAprovador,
    
    ca.C3_USER AS Codigo_UsuarioCriador,
    uc.Login_Usuario AS Login_UsuarioCriador,
    uc.Nome_Usuario AS Nome_UsuarioCriador,
    
    ca.C3_COND AS Codigo_CondicaoPagamento,
    s.E4_DESCRI AS DescricaoCondicaoPagamento,
    ca.C3_OBS AS Observacao

FROM ContratosComAprovacao ca
LEFT JOIN U_C1JTKS_PR.SB1010 sb ON sb.B1_COD = ca.C3_PRODUTO AND sb.D_E_L_E_T_ <> '*'
LEFT JOIN U_C1JTKS_PR.SE4010 s ON s.E4_CODIGO = ca.C3_COND AND s.D_E_L_E_T_ <> '*'
LEFT JOIN UsuariosNomes uc ON uc.Codigo_Usuario = TRIM(ca.C3_USER)
LEFT JOIN UsuariosNomes uap ON uap.Codigo_Usuario = TRIM(ca.CR_USERLIB)
WHERE ca.LinhaAprovacao = 1
ORDER BY ca.C3_EMISSAO DESC, ca.C3_NUM DESC