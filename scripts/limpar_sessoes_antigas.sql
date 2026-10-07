-- Limpeza NÃO destrutiva de sessões antigas (nada é apagado): rode no banco do ambiente (hml ou prod).
-- Serve para o "Ao vivo" e as análises de Auditoria não contarem sessões que já morreram.
--
-- 1) Rode o bloco "CONFERIR" e veja os números.
-- 2) Rode o bloco "APLICAR" (está em transação: confira o resultado e dê COMMIT; ou ROLLBACK para desistir).
--
-- Horários do core ficam em horário de Brasília (timestamp sem fuso).

-- ============================ CONFERIR ============================
SELECT
    count(*) FILTER (WHERE status = 'ATIVA')                                              AS ativas_no_banco,
    count(*) FILTER (WHERE status = 'ATIVA' AND expira_em < (now() AT TIME ZONE 'America/Sao_Paulo'))
                                                                                          AS ativas_ja_expiradas,
    count(*) FILTER (WHERE status = 'ATIVA' AND codigo_usuario IS NULL)                   AS ativas_de_visitantes,
    count(*) FILTER (WHERE status = 'ATIVA' AND user_agent IS NULL)                       AS ativas_sem_navegador
FROM core.tb_sessao;

-- ============================ APLICAR =============================
BEGIN;

-- Sessões "ATIVAS" cujo prazo já passou: encerra com o motivo de inatividade, na hora da última atividade.
UPDATE core.tb_sessao
   SET status = 'FINALIZADA',
       encerrada_em = LEAST(ultima_atividade, expira_em),
       motivo_encerramento = 'TIMEOUT_INATIVIDADE'
 WHERE status = 'ATIVA'
   AND expira_em < (now() AT TIME ZONE 'America/Sao_Paulo');

-- Visitantes (sem usuário) que ficaram ativos: não são logins; encerra para sair das contagens.
UPDATE core.tb_sessao
   SET status = 'FINALIZADA',
       encerrada_em = ultima_atividade,
       motivo_encerramento = 'LIMPEZA_VISITANTE'
 WHERE status = 'ATIVA'
   AND codigo_usuario IS NULL;

-- Quem aparece como online mas não tem nenhuma sessão ativa deixa de aparecer.
UPDATE core.tb_usuario u
   SET status_online = false,
       id_sessao_atual = NULL
 WHERE u.status_online = true
   AND NOT EXISTS (
        SELECT 1 FROM core.tb_sessao s
         WHERE s.codigo_usuario = u.codigo_usuario AND s.status = 'ATIVA'
   );

-- Confira de novo antes de confirmar:
SELECT status, count(*) FROM core.tb_sessao GROUP BY status ORDER BY status;
SELECT count(*) AS usuarios_online FROM core.tb_usuario WHERE status_online = true;

COMMIT;   -- troque por ROLLBACK; se algo não estiver como esperado
