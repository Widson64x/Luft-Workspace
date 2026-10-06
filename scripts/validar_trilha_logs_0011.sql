\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    acesso bigint;
    detalhe bigint;
    alteracao bigint;
    outro_sistema integer;
BEGIN
    IF current_database() NOT IN ('luft_web_logs_a21_teste', 'luft_web') THEN
        RAISE EXCEPTION 'Banco inesperado para validacao: %', current_database();
    END IF;

    INSERT INTO core.tb_logacesso (
        id_sistema,
        rota_acessada,
        metodo_http,
        id_correlacao,
        duracao_ms,
        status_http
    )
    VALUES (0, '/teste-cadeia', 'POST', 'teste-correlacao-0011', 12, 200)
    RETURNING id_logacesso INTO acesso;

    INSERT INTO core.tb_logdetalhe (
        id_sistema,
        id_logacesso,
        acao,
        recurso,
        descricao,
        id_correlacao
    )
    VALUES (
        0,
        acesso,
        'ATUALIZAR',
        'TESTE',
        'Detalhe de teste',
        'teste-correlacao-0011'
    )
    RETURNING id_logdetalhe INTO detalhe;

    INSERT INTO core.tb_logs (
        id_logdetalhe,
        tipo_alteracao,
        campos_alterados_json,
        dados_anteriores_json,
        dados_novos_json
    )
    VALUES (
        detalhe,
        'ALTERACAO',
        '["status"]',
        '{"status":"A"}',
        '{"status":"B"}'
    )
    RETURNING id_logalteracao INTO alteracao;

    IF alteracao IS NULL THEN
        RAISE EXCEPTION 'A alteracao filha nao foi criada.';
    END IF;

    SELECT id_sistema
      INTO outro_sistema
      FROM core.tb_sistema
     WHERE id_sistema <> 0
     ORDER BY id_sistema
     LIMIT 1;

    IF outro_sistema IS NOT NULL THEN
        BEGIN
            INSERT INTO core.tb_logdetalhe (
                id_sistema,
                id_logacesso,
                acao,
                recurso,
                descricao
            )
            VALUES (
                outro_sistema,
                acesso,
                'TESTAR',
                'TESTE',
                'Vinculo invalido entre sistemas'
            );
            RAISE EXCEPTION 'A FK composta aceitou sistemas diferentes.';
        EXCEPTION
            WHEN foreign_key_violation THEN
                NULL;
        END;
    END IF;

    DELETE FROM core.tb_logacesso WHERE id_logacesso = acesso;

    IF EXISTS (
        SELECT 1 FROM core.tb_logdetalhe WHERE id_logdetalhe = detalhe
    ) OR EXISTS (
        SELECT 1 FROM core.tb_logs WHERE id_logalteracao = alteracao
    ) THEN
        RAISE EXCEPTION 'A cascata nao removeu todos os filhos.';
    END IF;
END $$;

ROLLBACK;
