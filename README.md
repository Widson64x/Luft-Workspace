# Luft Workspace

Portal central das aplicacoes web da Luft e projeto piloto do LuftBase. O
Workspace usa o framework para identidade LDAP, sessao compartilhada, RBAC,
PostgreSQL `core`, notificacoes, publicacoes, auditoria, observabilidade e temas.

## Arquitetura do piloto M10

| Responsabilidade | Implementacao |
|---|---|
| Inicializacao Flask | `PlataformaLuft` em `CriarApp()` (`App/__init__.py`) |
| Login e logout global | identidade e sessao Redis do LuftBase |
| Permissoes | decorators e consultas em lote do LuftBase |
| Sistemas do Hub | consulta unica ao PostgreSQL `core` |
| Publicacoes | servico, REST e SSE do LuftBase |
| Interface e temas | template base, tokens e preferencia do LuftBase |
| SQL Server | diretorio de usuarios/grupos, estritamente somente leitura |
| Banco da aplicacao | schema informado no segredo PostgreSQL do Workspace |

Nao existem models sistemicos, gerenciadores de sessao SQLAlchemy nem injecao de
models no Workspace. Esses contratos pertencem ao LuftBase.

## Configuracao

Copie `.env.example` para `.env` e informe somente a identidade da aplicacao,
Vault, LDAP, politica de sessao e opcoes proprias do processo. Caminhos completos
de banco nao ficam no `.env`.

O LuftBase deriva automaticamente:

```text
luft/{ambiente}/sqlserver
luft/{ambiente}/bancos/postgresql/conexoes/luft-web
luft/{ambiente}/bancos/postgresql/sistemas/0
luft/{ambiente}/redis/sessoes
```

O segredo PostgreSQL precisa conter `host`, `porta`, `nome_banco`, `esquema`,
`usuario`, `senha` e `tipo_banco=postgresql`. Use uma role dedicada, nunca
`admin`, `postgres` ou `sa`. Ela deve acessar seu proprio schema e os objetos
necessarios do schema `core`.

O Workspace usa somente `LUFT_SISTEMA_ID=0` no bootstrap. O segredo do sistema
informa conexao, schema, identificador e role; zero representa o escopo global e
passa pelas mesmas regras de autorizacao, sem liberar permissoes automaticamente.

## Instalacao local

Use Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python App.py     # desenvolvimento (depurador e recarga automatica)
python Wsgi.py    # producao (Waitress)
```

## Estrutura

O Workspace segue o padrao de projeto das aplicacoes Luft (LuftBase, ADR-017), igual ao
Luft-ConnectAir: `App/__init__.py` (fabrica `CriarApp`), `Catalogo.py`, `Conexoes.py`,
`Configuracoes.py`, `Models/POSTGRES/`, `Routes/`, `Services/`, `Static/`, `Templates/` e
`Utils/`, mais `App.py` (desenvolvimento) e `Wsgi.py` (producao) na raiz. O que e particular do
Hub (catalogo de sistemas, nomes de servicos do Windows) fica no fim dos arquivos.

O wheel do LuftBase usado pelo piloto esta em `vendor/`, permitindo que os
deploys Windows e Linux instalem a mesma versao sem depender de um checkout
irmao. Para desenvolver simultaneamente o framework, use temporariamente:

```powershell
python -m pip install --no-deps -e ..\LuftBase
```

## Verificacao

```powershell
python -m pytest tests
python -m ruff check --ignore N999 App App.py Wsgi.py scripts tests
python -m compileall -q App App.py Wsgi.py
```

Os testes e a factory de teste nao acessam Vault, Redis, LDAP ou bancos reais.

## Documentacao

- [Migracao do Workspace para LuftBase](docs/MIGRACAO-LUFTBASE.md)
- [Migracao das tabelas sistemicas](docs/MIGRACAO-CORE-POSTGRESQL.md)
- [Indice tecnico do Workspace](docs/README.md)
