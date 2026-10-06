\set ON_ERROR_STOP on

-- =============================================================================
-- REINICIALIZACAO CONTROLADA DO BANCO DE DESENVOLVIMENTO (LUFT_WEB)
--
-- Este script e idempotente e exclusivo para o ambiente local de desenvolvimento.
-- Nunca execute em homologacao, producao ou contra servidores externos.
-- =============================================================================

BEGIN;

-- 1. Trava transacional para execucao exclusiva
SELECT pg_advisory_xact_lock(hashtext('luftbase:desenvolvimento:reinicializacao'));

-- 2. Validacoes estritas de seguranca de ambiente
DO $$
DECLARE
    v_versao text;
BEGIN
    IF current_database() <> 'luft_web' THEN
        RAISE EXCEPTION 'Abortando: banco atual e %, esperado estritamente luft_web', current_database();
    END IF;
    IF current_user <> 'admin' THEN
        RAISE EXCEPTION 'Abortando: usuario atual e %, esperado estritamente admin', current_user;
    END IF;
    SELECT version_num INTO v_versao FROM core.alembic_version;
    IF v_versao <> '20260922_0009' THEN
        RAISE EXCEPTION 'Abortando: migracao 20260922_0009 precisa estar aplicada antes da reinicializacao (versao atual: %)', v_versao;
    END IF;
END $$;

-- 3. Limpeza de dados preservando integridade referencial
-- Remove todos os sistemas (o que cascateia para modulos, permissoes e concessoes)
DELETE FROM core.tb_sistema;

-- 4. Cadastro unico do Luft-Workspace (id_sistema = 0)
INSERT INTO core.tb_sistema (
    id_sistema,
    nome_sistema,
    descricao_sistema,
    categoria,
    ativo,
    em_manutencao,
    ordem_exibicao,
    icone,
    link
) VALUES (
    0,
    'Luft-Workspace',
    'Hub central da plataforma web Luft.',
    'HUB',
    true,
    false,
    0,
    'ph-bold ph-squares-four',
    '/'
) ON CONFLICT (id_sistema) DO UPDATE SET
    nome_sistema = EXCLUDED.nome_sistema,
    descricao_sistema = EXCLUDED.descricao_sistema,
    categoria = EXCLUDED.categoria,
    ativo = EXCLUDED.ativo,
    em_manutencao = EXCLUDED.em_manutencao,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    icone = EXCLUDED.icone,
    link = EXCLUDED.link;

-- 5. Cadastro dos modulos padronizados do LuftBase
INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'PLATAFORMA', 'Plataforma', 'Acesso e administracao global.', 'ph-cube', 10, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'INICIO', 'Inicio', 'Pagina inicial e indicadores.', 'ph-house', 20, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'CONFIGURACOES', 'Configuracoes', 'Catalogo e configuracoes operacionais.', 'ph-gear', 30, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'SEGURANCA', 'Seguranca', 'Permissoes e sessoes.', 'ph-shield-check', 40, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'OBSERVABILIDADE', 'Observabilidade', 'Auditoria e diagnosticos.', 'ph-chart-line', 50, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'AMBIENTE', 'Ambiente', 'Variaveis e servicos.', 'ph-terminal-window', 60, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'CONTEUDO', 'Conteudo', 'Comunicados e atualizacoes.', 'ph-megaphone', 70, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'NOTIFICACOES', 'Notificacoes', 'Central de notificacoes.', 'ph-bell', 80, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO core.tb_modulo (id_sistema, codigo_modulo, nome_modulo, descricao_modulo, icone, ordem_exibicao, ativo)
VALUES (0, 'DESENVOLVIMENTO', 'Desenvolvimento', 'Ferramentas exclusivas de desenvolvimento.', 'ph-code', 90, true)
ON CONFLICT (id_sistema, codigo_modulo) DO UPDATE SET
    nome_modulo = EXCLUDED.nome_modulo,
    descricao_modulo = EXCLUDED.descricao_modulo,
    icone = EXCLUDED.icone,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

-- 6. Cadastro do catalogo padronizado de permissoes com heranca
INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'PLATAFORMA'), NULL, 'PLATAFORMA.SISTEMA.ADMINISTRAR', 'SISTEMA', 'ADMINISTRAR',
    'Administrar todos os recursos do sistema.', true, true, false, 10
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'PLATAFORMA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'PLATAFORMA.SISTEMA.ACESSAR', 'SISTEMA', 'ACESSAR',
    'Acessar o sistema pelo Hub.', true, false, true, 20
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'INICIO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'INICIO.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar o modulo Inicio.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'INICIO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'INICIO.MODULO.GERENCIAR'), 'INICIO.PAINEL.VISUALIZAR', 'PAINEL', 'VISUALIZAR',
    'Visualizar a pagina inicial.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'CONFIGURACOES.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar todas as configuracoes.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.MODULO.GERENCIAR'), 'CONFIGURACOES.PAINEL.VISUALIZAR', 'PAINEL', 'VISUALIZAR',
    'Visualizar o painel de configuracoes.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.MODULO.GERENCIAR'), 'CONFIGURACOES.SISTEMAS.GERENCIAR', 'SISTEMAS', 'GERENCIAR',
    'Gerenciar o catalogo de sistemas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.SISTEMAS.GERENCIAR'), 'CONFIGURACOES.SISTEMAS.VISUALIZAR', 'SISTEMAS', 'VISUALIZAR',
    'Visualizar sistemas.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.SISTEMAS.GERENCIAR'), 'CONFIGURACOES.SISTEMAS.CRIAR', 'SISTEMAS', 'CRIAR',
    'Cadastrar sistemas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.SISTEMAS.GERENCIAR'), 'CONFIGURACOES.SISTEMAS.EDITAR', 'SISTEMAS', 'EDITAR',
    'Editar sistemas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.SISTEMAS.GERENCIAR'), 'CONFIGURACOES.SISTEMAS.EXCLUIR', 'SISTEMAS', 'EXCLUIR',
    'Excluir sistemas e seus dados vinculados.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.MODULO.GERENCIAR'), 'CONFIGURACOES.MANUTENCAO.GERENCIAR', 'MANUTENCAO', 'GERENCIAR',
    'Gerenciar o modo de manutencao.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONFIGURACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONFIGURACOES.MODULO.GERENCIAR'), 'CONFIGURACOES.MANUTENCAO.IGNORAR', 'MANUTENCAO', 'IGNORAR',
    'Ignorar o modo de manutencao.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'SEGURANCA.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar todo o modulo de seguranca.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.MODULO.GERENCIAR'), 'SEGURANCA.PERMISSOES.GERENCIAR', 'PERMISSOES', 'GERENCIAR',
    'Gerenciar regras de acesso.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.PERMISSOES.GERENCIAR'), 'SEGURANCA.PERMISSOES.VISUALIZAR', 'PERMISSOES', 'VISUALIZAR',
    'Visualizar regras de acesso.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.PERMISSOES.GERENCIAR'), 'SEGURANCA.PERMISSOES.CRIAR', 'PERMISSOES', 'CRIAR',
    'Criar modulos e permissoes.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.PERMISSOES.GERENCIAR'), 'SEGURANCA.PERMISSOES.CONCEDER', 'PERMISSOES', 'CONCEDER',
    'Conceder, negar e restaurar permissoes.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.MODULO.GERENCIAR'), 'SEGURANCA.SESSOES.GERENCIAR', 'SESSOES', 'GERENCIAR',
    'Gerenciar sessoes autenticadas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.SESSOES.GERENCIAR'), 'SEGURANCA.SESSOES.VISUALIZAR', 'SESSOES', 'VISUALIZAR',
    'Visualizar sessoes autenticadas.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'SEGURANCA'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'SEGURANCA.SESSOES.GERENCIAR'), 'SEGURANCA.SESSOES.REVOGAR', 'SESSOES', 'REVOGAR',
    'Revogar sessoes autenticadas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'OBSERVABILIDADE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'OBSERVABILIDADE.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar observabilidade e auditoria.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'OBSERVABILIDADE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'OBSERVABILIDADE.MODULO.GERENCIAR'), 'OBSERVABILIDADE.AUDITORIA.VISUALIZAR', 'AUDITORIA', 'VISUALIZAR',
    'Visualizar a trilha de auditoria.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'OBSERVABILIDADE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'OBSERVABILIDADE.MODULO.GERENCIAR'), 'OBSERVABILIDADE.AUDITORIA.EXPORTAR', 'AUDITORIA', 'EXPORTAR',
    'Exportar a trilha de auditoria.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'AMBIENTE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'AMBIENTE.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar recursos do ambiente.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'AMBIENTE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'AMBIENTE.MODULO.GERENCIAR'), 'AMBIENTE.VARIAVEIS.VISUALIZAR', 'VARIAVEIS', 'VISUALIZAR',
    'Visualizar variaveis nao secretas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'AMBIENTE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'AMBIENTE.MODULO.GERENCIAR'), 'AMBIENTE.VARIAVEIS.EDITAR', 'VARIAVEIS', 'EDITAR',
    'Editar variaveis autorizadas.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'AMBIENTE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'AMBIENTE.MODULO.GERENCIAR'), 'AMBIENTE.SERVICOS.VISUALIZAR', 'SERVICOS', 'VISUALIZAR',
    'Visualizar servicos do ambiente.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'AMBIENTE'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'AMBIENTE.MODULO.GERENCIAR'), 'AMBIENTE.SERVICOS.EXECUTAR', 'SERVICOS', 'EXECUTAR',
    'Executar comandos de servico autorizados.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'CONTEUDO.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar todo o conteudo corporativo.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.MODULO.GERENCIAR'), 'CONTEUDO.COMUNICADOS.GERENCIAR', 'COMUNICADOS', 'GERENCIAR',
    'Gerenciar comunicados.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.COMUNICADOS.GERENCIAR'), 'CONTEUDO.COMUNICADOS.VISUALIZAR', 'COMUNICADOS', 'VISUALIZAR',
    'Visualizar a administracao de comunicados.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.COMUNICADOS.GERENCIAR'), 'CONTEUDO.COMUNICADOS.CRIAR', 'COMUNICADOS', 'CRIAR',
    'Criar comunicados.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.COMUNICADOS.GERENCIAR'), 'CONTEUDO.COMUNICADOS.EDITAR', 'COMUNICADOS', 'EDITAR',
    'Editar comunicados.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.COMUNICADOS.GERENCIAR'), 'CONTEUDO.COMUNICADOS.PUBLICAR', 'COMUNICADOS', 'PUBLICAR',
    'Publicar ou agendar comunicados.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.COMUNICADOS.GERENCIAR'), 'CONTEUDO.COMUNICADOS.ARQUIVAR', 'COMUNICADOS', 'ARQUIVAR',
    'Arquivar comunicados.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.COMUNICADOS.GERENCIAR'), 'CONTEUDO.COMUNICADOS.SINCRONIZAR', 'COMUNICADOS', 'SINCRONIZAR',
    'Sincronizar comunicados externos.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.MODULO.GERENCIAR'), 'CONTEUDO.ATUALIZACOES.GERENCIAR', 'ATUALIZACOES', 'GERENCIAR',
    'Gerenciar notas de atualizacao.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.ATUALIZACOES.GERENCIAR'), 'CONTEUDO.ATUALIZACOES.VISUALIZAR', 'ATUALIZACOES', 'VISUALIZAR',
    'Visualizar a administracao das notas de atualizacao.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.ATUALIZACOES.GERENCIAR'), 'CONTEUDO.ATUALIZACOES.CRIAR', 'ATUALIZACOES', 'CRIAR',
    'Criar notas de atualizacao.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.ATUALIZACOES.GERENCIAR'), 'CONTEUDO.ATUALIZACOES.EDITAR', 'ATUALIZACOES', 'EDITAR',
    'Editar notas de atualizacao.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.ATUALIZACOES.GERENCIAR'), 'CONTEUDO.ATUALIZACOES.PUBLICAR', 'ATUALIZACOES', 'PUBLICAR',
    'Publicar ou agendar notas de atualizacao.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'CONTEUDO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'CONTEUDO.ATUALIZACOES.GERENCIAR'), 'CONTEUDO.ATUALIZACOES.ARQUIVAR', 'ATUALIZACOES', 'ARQUIVAR',
    'Arquivar notas de atualizacao.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'NOTIFICACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'NOTIFICACOES.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Gerenciar notificacoes.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'NOTIFICACOES'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'NOTIFICACOES.MODULO.GERENCIAR'), 'NOTIFICACOES.PAINEL.VISUALIZAR', 'PAINEL', 'VISUALIZAR',
    'Visualizar o painel de notificacoes.', true, false, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'DESENVOLVIMENTO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'PLATAFORMA.SISTEMA.ADMINISTRAR'), 'DESENVOLVIMENTO.MODULO.GERENCIAR', 'MODULO', 'GERENCIAR',
    'Executar ferramentas de desenvolvimento.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'DESENVOLVIMENTO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'DESENVOLVIMENTO.MODULO.GERENCIAR'), 'DESENVOLVIMENTO.NOTIFICACOES.EXECUTAR', 'NOTIFICACOES', 'EXECUTAR',
    'Executar testes de notificacoes.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

INSERT INTO core.tb_permissao (
    id_sistema, id_modulo, id_permissao_pai, chave_permissao, recurso, acao,
    descricao_permissao, ativo, sensivel, eh_acesso_sistema, ordem_exibicao
) VALUES (
    0, (SELECT id_modulo FROM core.tb_modulo WHERE id_sistema = 0 AND codigo_modulo = 'DESENVOLVIMENTO'), (SELECT id_permissao FROM core.tb_permissao WHERE id_sistema = 0 AND chave_permissao = 'DESENVOLVIMENTO.MODULO.GERENCIAR'), 'DESENVOLVIMENTO.PUBLICACOES.EXECUTAR', 'PUBLICACOES', 'EXECUTAR',
    'Executar testes de publicacoes.', true, true, false, 0
) ON CONFLICT (id_sistema, chave_permissao) DO UPDATE SET
    id_modulo = EXCLUDED.id_modulo,
    id_permissao_pai = EXCLUDED.id_permissao_pai,
    recurso = EXCLUDED.recurso,
    acao = EXCLUDED.acao,
    descricao_permissao = EXCLUDED.descricao_permissao,
    sensivel = EXCLUDED.sensivel,
    eh_acesso_sistema = EXCLUDED.eh_acesso_sistema,
    ordem_exibicao = EXCLUDED.ordem_exibicao;

-- 7. Concessao de permissao raiz e de administracao ao grupo 6
INSERT INTO core.tb_permissaogrupo (codigo_usuariogrupo, id_permissao, conceder)
SELECT 6, id_permissao, true
FROM core.tb_permissao
WHERE id_sistema = 0 AND chave_permissao IN ('PLATAFORMA.SISTEMA.ADMINISTRAR', 'PLATAFORMA.SISTEMA.ACESSAR')
ON CONFLICT (codigo_usuariogrupo, id_permissao) DO UPDATE SET conceder = true;

-- 8. Invalidacao de cache de autorizacao
INSERT INTO core.tb_revisaocache (namespace, revisao, data_atualizacao)
VALUES ('autorizacao', 1, CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo')
ON CONFLICT (namespace) DO UPDATE
SET revisao = core.tb_revisaocache.revisao + 1,
    data_atualizacao = EXCLUDED.data_atualizacao;

-- 9. Verificacao de integridade e totais esperados
DO $$
DECLARE
    v_sistemas int;
    v_modulos int;
    v_permissoes int;
    v_grupo6 int;
BEGIN
    SELECT count(*) INTO v_sistemas FROM core.tb_sistema;
    IF v_sistemas <> 1 THEN
        RAISE EXCEPTION 'Falha de verificacao: esperado 1 sistema, encontrado %', v_sistemas;
    END IF;
    SELECT count(*) INTO v_modulos FROM core.tb_modulo;
    IF v_modulos <> 9 THEN
        RAISE EXCEPTION 'Falha de verificacao: esperado 9 modulos, encontrado %', v_modulos;
    END IF;
    SELECT count(*) INTO v_permissoes FROM core.tb_permissao;
    IF v_permissoes <> 48 THEN
        RAISE EXCEPTION 'Falha de verificacao: esperado 48 permissoes, encontrado %', v_permissoes;
    END IF;
    SELECT count(*) INTO v_grupo6 FROM core.tb_permissaogrupo WHERE codigo_usuariogrupo = 6;
    IF v_grupo6 < 1 THEN
        RAISE EXCEPTION 'Falha de verificacao: grupo 6 nao recebeu permissoes'; 
    END IF;
END $$;

COMMIT;

-- Concluido com sucesso.
