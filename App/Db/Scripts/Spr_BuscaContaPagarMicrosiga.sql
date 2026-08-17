CREATE  procedure [dbo].[Spr_BuscaContaPagarMicrosiga]  
/*    
  Criado: Spr_BuscaContaPagarMicrosiga    
  Versão: 1.13    
    
  Nome.....: Spr_BuscaContaPagarMicrosiga    
   Objetivo: Procudure criada para buscar despesas no Microsiga e alimentar a tabela ContaPagar    
  Autor             Data       Versão Nº.SS Descrição     
  ----------------- ---------- ------ ----- -----------------------------------------------------------    
  Israel            26/11/2015 1.00         - Criação da procedure.    
  Israel            14/12/2015 1.01         - Ajuste para caso não encontre o item do budget para o fornecedor, amarreo pelo menos a um budget para a     
                                              empresa/filial e para a conta contábil.    
  Israel            28/12/2015 1.02         - Ajuste na procedure para incluir algumas campos a mais e buscar a aprovação do PC/AE da forma correta.                                                  
  Israel            19/01/2016 1.03         - Melhoria na procedure em virtude de melhorias na estrutura do cadastro de fornecedor em relação ao código de integração entre sistemas.    
  Israel            01/02/2016 1.04         - Ajuste na procedure para buscar e as despesas com base na ultima data importada -30.    
  Israel            15/02/2016 1.05         - Ajuste na procedure para usar sempre a data de digitação da nota fiscal para o Data_Digitacao, mesmo sendo um PC, somente irá utilizar a mesma    
                                              data de emissão do PC quando o mesmo ainda não tiver nota fiscal digitada.    
  Israel            02/03/2016 1.06         - Ajuste na procedure em virtude de alteração na estrutura da table ContaPagar e da criação da tabela ContaPagarNotaFiscal.    
  Israel            19/05/2016 1.07         - Ajuste na procedure para alterar o cadastro do fornecedor trocando o nome do mesmo para "PJ" quando a despesa importada for da conta contábil "60301020279"    
                                              e a descrição do item for "ASSESSORIA OPERACIONAL 2%", conforme solicitado pelo Francisco Miranda e pelo Flávio Barbosa.    
  Israel            23/05/2016 1.08         - Ajuste na procedure, retirado alteração realizada na versão anterior 1.07. A troca do nome do fornecedor para "PJ" deve ser apenas na visualização na tela de BudGet    
                                              quando "60301020279" e a descrição do item for "ASSESSORIA OPERACIONAL 2%", conforme solicitado pelo Flávio Barbosa.    
  Israel            07/06/2016 1.09         - Ajuste na procedure, incluído a importação do código do produto do microsiga.     
  Leandro(LCS)      21/02/2017 1.09         - Foi incluido campos de Codigo de condição de pagamento e descrição de condição de pagamento, solicitado pelo Flavio da controladoria.    
  Israel            27/07/2017 1.10         - Ajustado query para não trazer os PC e AE sem fornecedor.    
  Israel            17/10/2017 1.11         - Trocado o campo AL_NOME pelo campo AL_DESC.    
  Israel            02/01/2019 1.12         - Incluído validação para não trazer contas que não tenham o código da empresa identificado corretamente.  
  Widson            11/05/2026 1.13         - Incluído o campo c7_obs (Observacao) do Oracle para a tabela ContaPagar.  
*/  
  
as  
begin  
  
    set nocount on;  
  
    truncate table [dbo].[ContaPagarTempB];  
  
    declare @DataInicial varchar(008)  
        = isnull(convert(varchar(008)  
                       , (  
                             select max([cp].[Data_Digitacao] - 60)  
                             from [dbo].[ContaPagar] as cp ( nolock )  
                         )  
                       , 112  
                        )  
               , '20151001'  
                );  
    declare @DataFinal varchar(008) = convert(varchar(008), getdate(), 112);  
    declare @Str_Query varchar(max);  
  
  
    set @Str_Query  
        = 'insert into ContaPagarTempB  
 (Empresa,Filial,Fornecedor,ContaContabil,CentroCusto,TipoDocumento,NumeroDocumento,SeqItem,CodItem,DescItem,DataEmissao,DataDigitacao,DataAprovacao,ValorPagar,Status,CodigContaPagarNotaFiscaloUltimoAprovador,NomeUltimoAprovador,CodigoCondicaoPagamento,De
scricaoCondicaoPagamento,Observacao)  
   SELECT CAST(Empresa AS INT) Empresa,    
      CAST(Filial AS VARCHAR(002)) Filial,    
      CAST(Fornecedor AS VARCHAR(010)) Fornecedor,    
      CAST(ContaContabil AS NUMERIC(015)) ContaContabil,    
      CAST(CentroCusto AS NUMERIC(010)) CentroCusto,    
      CAST(TipoDocumento AS VARCHAR(002)) TipoDocumento,    
      CAST(NumeroDocumento AS VARCHAR(018)) NumeroDocumento,    
      LTRIM(RTRIM(CAST(SeqItem AS VARCHAR(004)))) SeqItem,    
      LTRIM(RTRIM(CAST(CodItem AS VARCHAR(012)))) CodItem,    
      LTRIM(RTRIM(CAST(DescItem AS VARCHAR(100)))) DescItem,    
      CAST(DataEmissao AS DATETIME) DataEmissao,    
      CAST(DataDigitacao AS DATETIME) DataDigitacao,    
      CAST(DataAprovacao AS DATETIME) DataAprovacao,    
      CAST(ValorPagar AS MONEY) ValorPagar,    
      CAST(Status AS INT) Status,    
      CAST(CodigoUltimoAprovador AS INT) CodigContaPagarNotaFiscaloUltimoAprovador,    
      CAST(NomeUltimoAprovador AS VARCHAR(050)) NomeUltimoAprovador,    
      CAST(CodigoCondicaoPagamento AS VARCHAR(004)) CodigoCondicaoPagamento,    
      LTRIM(RTRIM(CAST(DescricaoCondicaoPagamento AS VARCHAR(100)))) DescricaoCondicaoPagamento,  
      LTRIM(RTRIM(CAST(Observacao AS VARCHAR(500)))) Observacao  
    FROM    OPENQUERY(LS_ORACLE_EZ,    
          ''SELECT  x.Empresa,    
           x.Filial,    
           x.Fornecedor,    
           x.ContaContabil,    
           x.CentroCusto,    
           x.TipoDocumento,    
           x.NumeroDocumento,    
           x.SeqItem,    
           x.CodItem,    
           x.DescItem,    
           x.DataEmissao,    
           x.DataDigitacao,    
           x.DataAprovacao,    
           x.ValorPagar,    
           x.Status,    
           x.CodigoUltimoAprovador,    
           x.NomeUltimoAprovador,    
           x.CodigoCondicaoPagamento,    
           x.DescricaoCondicaoPagamento,  
           x.Observacao    
         FROM    ( SELECT    1 Empresa,    
              pc.c7_filial Filial,    
              ''''1'''' || pc.c7_fornece || pc.c7_loja Fornecedor,    
              CASE WHEN pc.c7_conta = '''' '''' THEN ''''1''''    
                ELSE pc.c7_conta    
              END ContaContabil,    
              CASE WHEN pc.c7_cc = '''' '''' THEN NULL    
                ELSE pc.c7_cc    
              END CentroCusto,    
              CASE WHEN pc.c7_tipo = 1 THEN ''''PC''''    
                ELSE ''''AE''''    
              END TipoDocumento,    
              pc.c7_num NumeroDocumento,    
              pc.c7_item SeqItem,    
              pc.c7_produto CodItem,    
              pc.c7_descri DescItem,    
              pc.c7_emissao DataEmissao,    
              pc.c7_emissao DataDigitacao,    
              NULL DataAprovacao,    
              pc.c7_total ValorPagar,    
              NULL Status,    
              NULL CodigoUltimoAprovador,    
              NULL NomeUltimoAprovador,    
              e4.e4_codigo CodigoCondicaoPagamento,    
              e4.e4_descri DescricaoCondicaoPagamento,  
              pc.c7_obs Observacao    
             FROM      U_C1JTKS_PR.SC7120 pc inner join U_C1JTKS_PR.se4010 e4 on pc.c7_cond = e4.e4_codigo    
                WHERE     pc.d_e_l_e_t_ <> ''''*''''    
              AND pc.c7_emissao BETWEEN ''''' + @DataInicial + ''''' and ''''' + @DataFinal  
          + '''''    
             UNION ALL    
             SELECT    2 Empresa,    
              pc.c7_filial Filial,    
              ''''2'''' || pc.c7_fornece || pc.c7_loja Fornecedor,    
              CASE WHEN pc.c7_conta = '''' '''' THEN ''''1''''    
                ELSE pc.c7_conta    
              END ContaContabil,    
              CASE WHEN pc.c7_cc = '''' '''' THEN NULL    
                ELSE pc.c7_cc    
              END CentroCusto,    
              CASE WHEN pc.c7_tipo = 1 THEN ''''PC''''    
                ELSE ''''AE''''    
              END TipoDocumento,    
              pc.c7_num NumeroDocumento,    
              pc.c7_item SeqItem,    
              pc.c7_produto CodItem,    
              pc.c7_descri DescItem,    
              pc.c7_emissao DataEmissao,    
              pc.c7_emissao DataDigitacao,    
              NULL DataAprovacao,    
              pc.c7_total ValorPagar,    
              NULL Status,    
              NULL CodigoUltimoAprovador,    
              NULL NomeUltimoAprovador,    
              e4.e4_codigo CodigoCondicaoPagamento,    
              e4.e4_descri DescricaoCondicaoPagamento,  
              pc.c7_obs Observacao    
             FROM      U_C1JTKS_PR.SC7170 pc inner join U_C1JTKS_PR.se4010 e4 on pc.c7_cond = e4.e4_codigo    
             WHERE     pc.d_e_l_e_t_ <> ''''*''''    
              AND pc.c7_emissao BETWEEN ''''' + @DataInicial + ''''' and ''''' + @DataFinal  
          + '''''    
           ) x    
         ORDER BY x.DataDigitacao,    
           x.NumeroDocumento,    
           x.SeqItem'')';  
  
    exec ( @Str_Query );  
  
    -- ... [Resto da procedure de processamento]
end;
