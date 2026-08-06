import re

query_destino_sql = """-- O comando MERGE junta INSERT e UPDATE em uma única execução.
-- Ele verifica se a linha existe (via chave primária). Se sim, atualiza. Se não, insere.        

-- [ BLOCO 1: O ALVO ]
-- Qual tabela vai receber os dados?

MERGE INTO Luftinforma.dbo.ContaPagarFixo AS Destino
"""

query_limpa = re.sub(r'(--[^\n]*\n|/\*.*?\*/)', '', query_destino_sql, flags=re.DOTALL).strip()
print(repr(query_limpa))
print("Startswith MERGE:", query_limpa.upper().startswith("MERGE"))

query_sem_comentarios = re.sub(r'/\*.*?\*/', '', query_destino_sql, flags=re.DOTALL)
query_sem_comentarios = re.sub(r'--.*', '', query_sem_comentarios).strip()
print(repr(query_sem_comentarios))
print("Startswith MERGE 2:", query_sem_comentarios.upper().startswith("MERGE"))
