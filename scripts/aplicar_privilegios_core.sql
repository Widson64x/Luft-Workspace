-- ==============================================================================
-- SCRIPT IDEMPOTENTE DE PRIVILEGIOS: SCHEMA CORE E WORKSPACE
-- Framework LuftBase / Luft-Workspace
-- ==============================================================================

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'luft_web' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado luft_web, recebido %', current_database();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'luft_core_preferences_rw') THEN
        CREATE ROLE luft_core_preferences_rw NOLOGIN;
    END IF;
END $$;

-- 1. Conceder USAGE no schema core
GRANT USAGE ON SCHEMA core TO
    luft_core_auth_ro,
    luft_core_audit_write,
    luft_core_notifications_rw,
    luft_core_publications_rw,
    luft_core_preferences_rw,
    luft_core_security_admin,
    luft_workspace_app;

-- 2. Privilegios por role funcional no schema core

-- Autenticacao / Seguranca (leitura)
GRANT SELECT ON
    core.tb_sistema,
    core.tb_permissao,
    core.tb_permissaogrupo,
    core.tb_permissaousuario,
    core.tb_usuario,
    core.tb_sessao
TO luft_core_auth_ro;

GRANT SELECT ON core.tb_revisaocache TO luft_core_auth_ro;

-- Preferencias visuais (armazenadas em tb_usuario)
GRANT SELECT, UPDATE (tema_preferido, modo_tema, idioma) ON core.tb_usuario
TO luft_core_preferences_rw;

-- Auditoria / Logs (escrita e leitura de logs)
GRANT SELECT, INSERT ON
    core.tb_logs,
    core.tb_logevento,
    core.tb_logdetalhe
TO luft_core_audit_write;

GRANT UPDATE (id_log) ON core.tb_logevento, core.tb_logdetalhe
TO luft_core_audit_write;

GRANT USAGE, SELECT ON
    core.tb_logs_id_log_seq,
    core.tb_logevento_id_logevento_seq,
    core.tb_logdetalhe_id_logdetalhe_seq
TO luft_core_audit_write;

-- Notificacoes
GRANT SELECT, INSERT, UPDATE, DELETE ON
    core.tb_notificacao,
    core.tb_notificacao_leitura
TO luft_core_notifications_rw;

GRANT USAGE, SELECT ON
    core.tb_notificacao_id_notificacao_seq
TO luft_core_notifications_rw;

-- Publicacoes e Notas
GRANT SELECT, INSERT, UPDATE, DELETE ON
    core.tb_publicacao,
    core.tb_publicacaogrupo,
    core.tb_publicacaoleitura,
    core.tb_publicacaonotificacao,
    core.tb_notaatualizacaoitem
TO luft_core_publications_rw;

GRANT USAGE, SELECT ON
    core.tb_publicacao_id_publicacao_seq,
    core.tb_publicacaonotificacao_id_vinculo_seq,
    core.tb_notaatualizacaoitem_id_item_seq
TO luft_core_publications_rw;

-- Seguranca e Administracao Geral do Core
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core TO luft_core_security_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA core TO luft_core_security_admin;

-- 3. Associar roles funcionais ao usuario de runtime da aplicacao
GRANT
    luft_core_auth_ro,
    luft_core_audit_write,
    luft_core_notifications_rw,
    luft_core_publications_rw,
    luft_core_preferences_rw,
    luft_core_security_admin
TO luft_workspace_app;

GRANT
    luft_core_auth_ro,
    luft_core_audit_write,
    luft_core_notifications_rw,
    luft_core_publications_rw,
    luft_core_preferences_rw
TO luft_connectair_app, luft_control_app, luft_docs_app, luft_integrador_app;

-- 4. Schema proprio da aplicacao (workspace)
CREATE SCHEMA IF NOT EXISTS workspace;
GRANT USAGE, CREATE ON SCHEMA workspace TO luft_workspace_app, luft_workspace_rw;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA workspace TO luft_workspace_app, luft_workspace_rw;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA workspace TO luft_workspace_app, luft_workspace_rw;

-- 5. Objetos futuros do core exigem GRANT explicito na propria migration.
-- Somente a role administrativa recebe defaults; roles funcionais nao devem
-- ganhar acesso acidental a uma nova tabela apenas por ela ter sido criada.
ALTER DEFAULT PRIVILEGES FOR ROLE admin IN SCHEMA core
    GRANT ALL PRIVILEGES ON TABLES TO luft_core_security_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE admin IN SCHEMA core
    GRANT ALL PRIVILEGES ON SEQUENCES TO luft_core_security_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE admin IN SCHEMA workspace
    GRANT ALL PRIVILEGES ON TABLES TO luft_workspace_app, luft_workspace_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE admin IN SCHEMA workspace
    GRANT ALL PRIVILEGES ON SEQUENCES TO luft_workspace_app, luft_workspace_rw;

-- 6. Default Privileges para criacoes futuras por luft_web_owner
ALTER DEFAULT PRIVILEGES FOR ROLE luft_web_owner IN SCHEMA core
    GRANT ALL PRIVILEGES ON TABLES TO luft_core_security_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE luft_web_owner IN SCHEMA workspace
    GRANT ALL PRIVILEGES ON TABLES TO luft_workspace_app, luft_workspace_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE luft_web_owner IN SCHEMA workspace
    GRANT ALL PRIVILEGES ON SEQUENCES TO luft_workspace_app, luft_workspace_rw;

COMMIT;
