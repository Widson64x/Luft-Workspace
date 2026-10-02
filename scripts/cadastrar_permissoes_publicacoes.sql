-- ==============================================================================
-- SCRIPT IDEMPOTENTE: CADASTRO DE PERMISSOES DE COMUNICADOS E ATUALIZACOES
-- Banco: luft_web (PostgreSQL)
-- Schema: core
-- Escopo: id_sistema = 0 (Global / Luft Workspace)
-- ==============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'luft_web' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado luft_web, recebido %', current_database();
    END IF;
END $$;

-- 1. Inserir ou atualizar catálogo de permissões no schema core
INSERT INTO core.tb_permissao (chave_permissao, descricao_permissao, categoria_permissao, id_sistema)
VALUES
    ('ADMIN.COMUNICADOS.VISUALIZAR', 'Visualizar a administracao de comunicados.', 'COMUNICADOS', 0),
    ('ADMIN.COMUNICADOS.CRIAR', 'Criar rascunhos de comunicados.', 'COMUNICADOS', 0),
    ('ADMIN.COMUNICADOS.EDITAR', 'Editar comunicados em rascunho ou agendados.', 'COMUNICADOS', 0),
    ('ADMIN.COMUNICADOS.PUBLICAR', 'Publicar ou agendar comunicados e gerar notificacoes.', 'COMUNICADOS', 0),
    ('ADMIN.COMUNICADOS.ARQUIVAR', 'Arquivar comunicados e encerrar suas notificacoes.', 'COMUNICADOS', 0),
    ('ADMIN.COMUNICADOS.SINCRONIZAR_GMAIL', 'Sincronizar comunicados recebidos pela API do Gmail.', 'COMUNICADOS', 0),
    ('ADMIN.ATUALIZACOES.VISUALIZAR', 'Visualizar a administracao das notas de atualizacao.', 'ATUALIZACOES', 0),
    ('ADMIN.ATUALIZACOES.CRIAR', 'Criar rascunhos de notas de atualizacao.', 'ATUALIZACOES', 0),
    ('ADMIN.ATUALIZACOES.EDITAR', 'Editar notas de atualizacao em rascunho ou agendadas.', 'ATUALIZACOES', 0),
    ('ADMIN.ATUALIZACOES.PUBLICAR', 'Publicar ou agendar notas de atualizacao.', 'ATUALIZACOES', 0),
    ('ADMIN.ATUALIZACOES.ARQUIVAR', 'Arquivar notas de atualizacao e encerrar suas notificacoes.', 'ATUALIZACOES', 0)
ON CONFLICT (chave_permissao, id_sistema) DO UPDATE
SET descricao_permissao = EXCLUDED.descricao_permissao,
    categoria_permissao = EXCLUDED.categoria_permissao;

-- 2. Conceder as permissões ao Grupo TI (codigo_usuariogrupo = 6)
INSERT INTO core.tb_permissaogrupo (codigo_usuariogrupo, id_permissao)
SELECT 6, p.id_permissao
FROM core.tb_permissao p
WHERE p.id_sistema = 0
  AND p.chave_permissao IN (
      'ADMIN.COMUNICADOS.VISUALIZAR',
      'ADMIN.COMUNICADOS.CRIAR',
      'ADMIN.COMUNICADOS.EDITAR',
      'ADMIN.COMUNICADOS.PUBLICAR',
      'ADMIN.COMUNICADOS.ARQUIVAR',
      'ADMIN.COMUNICADOS.SINCRONIZAR_GMAIL',
      'ADMIN.ATUALIZACOES.VISUALIZAR',
      'ADMIN.ATUALIZACOES.CRIAR',
      'ADMIN.ATUALIZACOES.EDITAR',
      'ADMIN.ATUALIZACOES.PUBLICAR',
      'ADMIN.ATUALIZACOES.ARQUIVAR'
  )
ON CONFLICT (codigo_usuariogrupo, id_permissao) DO NOTHING;

COMMIT;

