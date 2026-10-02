\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    revisao_atual text;
BEGIN
    SELECT version_num INTO revisao_atual FROM core.alembic_version;
    IF revisao_atual <> '20260916_0005' THEN
        RAISE EXCEPTION
            'Revisao esperada 20260916_0005, encontrada %.',
            COALESCE(revisao_atual, '<ausente>');
    END IF;
END
$$;

ALTER TABLE core.tb_sistema
    ADD COLUMN identificador_aplicacao varchar(80);

UPDATE core.tb_sistema
SET identificador_aplicacao = CASE id_sistema
    WHEN 0 THEN 'luft-workspace'
    WHEN 1 THEN 'luft-connectair'
    WHEN 2 THEN 'luft-control'
    WHEN 3 THEN 'luft-integrador'
    WHEN 4 THEN 'luft-monitor-rdp'
    WHEN 5 THEN 'luft-docs'
END;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM core.tb_sistema
        WHERE identificador_aplicacao IS NULL
    ) THEN
        RAISE EXCEPTION
            'Existem sistemas sem identificador_aplicacao; a transacao sera revertida.';
    END IF;
END
$$;

ALTER TABLE core.tb_sistema
    ALTER COLUMN identificador_aplicacao SET NOT NULL;

ALTER TABLE core.tb_sistema
    ADD CONSTRAINT uq_core_sistema_identificador_aplicacao
    UNIQUE (identificador_aplicacao);

UPDATE core.alembic_version
SET version_num = '20260917_0006'
WHERE version_num = '20260916_0005';

COMMIT;
