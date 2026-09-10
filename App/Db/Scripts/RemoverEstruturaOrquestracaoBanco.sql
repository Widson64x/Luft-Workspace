/*
    Remove definitivamente a estrutura descontinuada de orquestração de bancos.

    ATENÇÃO: todos os cadastros, mapeamentos, históricos e logs dessas tabelas
    serão perdidos. Faça backup antes de executar este script, se necessário.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    -- A ordem respeita as chaves estrangeiras da estrutura.
    IF OBJECT_ID(N'intec.dbo.Tb_BancoExecucaoLog', N'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoExecucaoLog;

    IF OBJECT_ID(N'intec.dbo.Tb_BancoExecucao', N'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoExecucao;

    IF OBJECT_ID(N'intec.dbo.Tb_BancoTarefaCampo', N'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoTarefaCampo;

    IF OBJECT_ID(N'intec.dbo.Tb_BancoTarefa', N'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoTarefa;

    IF OBJECT_ID(N'intec.dbo.Tb_BancoConexao', N'U') IS NOT NULL
        DROP TABLE intec.dbo.Tb_BancoConexao;

    COMMIT TRANSACTION;
    PRINT N'Estrutura de orquestração de bancos removida com sucesso.';
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
