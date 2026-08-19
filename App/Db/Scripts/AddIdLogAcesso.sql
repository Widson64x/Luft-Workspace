/*
    Adiciona a coluna Id_LogAcesso na Tb_AuditoriaEvento
    para vincular a auditoria ao Log de Acessos (Tb_LogAcesso).
    
    Autor: LuftCore Framework
    Data: 2026-08-17
*/

IF NOT EXISTS (
    SELECT 1 
    FROM intec.sys.columns 
    WHERE object_id = OBJECT_ID('intec.dbo.Tb_AuditoriaEvento') 
      AND name = 'Id_LogAcesso'
)
BEGIN
    ALTER TABLE intec.dbo.Tb_AuditoriaEvento
    ADD Id_LogAcesso INT NULL;

    PRINT 'Coluna Id_LogAcesso adicionada na Tb_AuditoriaEvento.';
    
    -- Criar a constraint de chave estrangeira
    ALTER TABLE intec.dbo.Tb_AuditoriaEvento
    ADD CONSTRAINT FK_Tb_AuditoriaEvento_LogAcesso FOREIGN KEY (Id_LogAcesso)
    REFERENCES intec.dbo.Tb_LogAcesso(Id_Log);
    
    PRINT 'Chave Estrangeira FK_Tb_AuditoriaEvento_LogAcesso criada.';
END
ELSE
BEGIN
    PRINT 'A coluna Id_LogAcesso ja existe na Tb_AuditoriaEvento.';
END
GO
