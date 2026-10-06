BEGIN;

ALTER TABLE core.tb_sistema
    DROP CONSTRAINT IF EXISTS uq_core_sistema_identificador_aplicacao;

ALTER TABLE core.tb_sistema
    DROP COLUMN IF EXISTS identificador_aplicacao;

UPDATE core.alembic_version
SET version_num = '20260917_0007'
WHERE version_num = '20260917_0006';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM core.alembic_version
        WHERE version_num = '20260917_0007'
    ) THEN
        RAISE EXCEPTION 'Versao anterior inesperada; nenhuma alteracao deve ser confirmada.';
    END IF;
END
$$;

COMMIT;
