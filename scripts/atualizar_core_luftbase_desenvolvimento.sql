\set ON_ERROR_STOP on

-- Somente para a adocao controlada do banco local de desenvolvimento.
-- Homologacao e producao devem usar a CLI Alembic com credencial de deploy.
BEGIN;

SELECT pg_advisory_xact_lock(hashtext('luftbase:core:migracoes'));

DO $$
DECLARE
    tabela text;
    tabelas_base text[] := ARRAY[
        'tb_sistema', 'tb_permissao', 'tb_permissaogrupo', 'tb_permissaousuario',
        'tb_logacesso', 'tb_logdetalhe', 'tb_notificacao', 'tb_notificacao_leitura',
        'tb_publicacao', 'tb_publicacaogrupo', 'tb_publicacaoleitura',
        'tb_publicacaonotificacao', 'tb_notaatualizacaoitem'
    ];
BEGIN
    IF current_database() <> 'luft_web' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado luft_web, recebido %', current_database();
    END IF;
    IF to_regclass('core.alembic_version') IS NOT NULL THEN
        RAISE EXCEPTION 'core.alembic_version ja existe; use a CLI Alembic';
    END IF;
    FOREACH tabela IN ARRAY tabelas_base LOOP
        IF to_regclass(format('core.%I', tabela)) IS NULL THEN
            RAISE EXCEPTION 'Baseline incompleta: core.% nao existe', tabela;
        END IF;
    END LOOP;
END $$;

CREATE TABLE core.tb_preferenciausuario (
    id_usuario integer NOT NULL,
    tema varchar(50) DEFAULT 'luft' NOT NULL,
    modo_tema varchar(10) DEFAULT 'SISTEMA' NOT NULL,
    idioma varchar(10) DEFAULT 'pt-BR' NOT NULL,
    configuracoes_json text,
    data_atualizacao timestamp(3) without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo') NOT NULL,
    CONSTRAINT pk_core_preferenciausuario PRIMARY KEY (id_usuario),
    CONSTRAINT ck_core_preferenciausuario_modo_tema
        CHECK (modo_tema IN ('CLARO', 'ESCURO', 'SISTEMA'))
);

CREATE TABLE core.tb_revisaocache (
    namespace varchar(100) NOT NULL,
    revisao bigint DEFAULT 0 NOT NULL,
    data_atualizacao timestamp(3) without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo') NOT NULL,
    CONSTRAINT pk_core_revisaocache PRIMARY KEY (namespace),
    CONSTRAINT ck_core_revisaocache_nao_negativa CHECK (revisao >= 0)
);

INSERT INTO core.tb_revisaocache (namespace, revisao)
VALUES ('autorizacao', 0);

CREATE FUNCTION core.fn_incrementar_revisao_autorizacao()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO core.tb_revisaocache (namespace, revisao, data_atualizacao)
    VALUES ('autorizacao', 1, CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')
    ON CONFLICT (namespace) DO UPDATE
    SET revisao = core.tb_revisaocache.revisao + 1,
        data_atualizacao = EXCLUDED.data_atualizacao;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_revisao_autorizacao_tb_sistema
AFTER INSERT OR UPDATE OR DELETE ON core.tb_sistema
FOR EACH STATEMENT EXECUTE FUNCTION core.fn_incrementar_revisao_autorizacao();
CREATE TRIGGER trg_revisao_autorizacao_tb_permissao
AFTER INSERT OR UPDATE OR DELETE ON core.tb_permissao
FOR EACH STATEMENT EXECUTE FUNCTION core.fn_incrementar_revisao_autorizacao();
CREATE TRIGGER trg_revisao_autorizacao_tb_permissaogrupo
AFTER INSERT OR UPDATE OR DELETE ON core.tb_permissaogrupo
FOR EACH STATEMENT EXECUTE FUNCTION core.fn_incrementar_revisao_autorizacao();
CREATE TRIGGER trg_revisao_autorizacao_tb_permissaousuario
AFTER INSERT OR UPDATE OR DELETE ON core.tb_permissaousuario
FOR EACH STATEMENT EXECUTE FUNCTION core.fn_incrementar_revisao_autorizacao();

ALTER TABLE core.tb_logacesso ADD COLUMN id_correlacao varchar(64);
ALTER TABLE core.tb_logacesso ADD COLUMN duracao_ms integer;
ALTER TABLE core.tb_logacesso ADD COLUMN status_http smallint;
ALTER TABLE core.tb_logacesso ADD CONSTRAINT ck_core_logacesso_duracao
    CHECK (duracao_ms IS NULL OR duracao_ms >= 0);
ALTER TABLE core.tb_logacesso ADD CONSTRAINT ck_core_logacesso_status_http
    CHECK (status_http IS NULL OR status_http BETWEEN 100 AND 599);
CREATE INDEX ix_core_logacesso_correlacao ON core.tb_logacesso (id_correlacao);

ALTER TABLE core.tb_logdetalhe ADD COLUMN id_correlacao varchar(64);
CREATE INDEX ix_core_logdetalhe_correlacao ON core.tb_logdetalhe (id_correlacao);

CREATE INDEX ix_core_notificacao_sistema_cursor
    ON core.tb_notificacao (id_sistema, id_notificacao);
CREATE INDEX ix_core_notificacao_usuario_cursor
    ON core.tb_notificacao (id_usuario_destino, id_notificacao);
CREATE INDEX ix_core_notificacao_grupo_cursor
    ON core.tb_notificacao (id_grupo_destino, id_notificacao);
CREATE INDEX ix_core_publicacao_sistema_status_cursor
    ON core.tb_publicacao (id_sistema, status_publicacao, id_publicacao);

CREATE TABLE core.alembic_version (
    version_num varchar(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO core.alembic_version (version_num) VALUES ('20260916_0005');

COMMIT;
