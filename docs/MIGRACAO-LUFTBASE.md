# M10 - Migracao do Luft Workspace para LuftBase

## Resultado esperado

O Workspace deve iniciar por uma unica factory, sem importar LuftCore e sem
criar conexoes, models ou sessao de banco proprios para recursos sistemicos.
SQL Server permanece somente leitura. PostgreSQL e Redis sao resolvidos pelo
Vault e pertencem ao ciclo de vida do LuftBase.

## O que mudou

- `LuftCore` foi removido das dependencias e da `.venv`.
- O wheel reproduzivel do LuftBase foi incluido em `vendor/`.
- A factory usa `PlataformaLuft` e registra apenas blueprints especificos do Hub.
- Models locais de permissao, usuario e log foram eliminados.
- Conexao e teardown SQLAlchemy locais foram eliminados.
- Login, logout, sessao, autorizacao, auditoria, metricas, temas, notificacoes e
  publicacoes usam contratos fixos do LuftBase.
- O catalogo de sistemas faz uma consulta PostgreSQL em lote e respeita grupo,
  concessao individual e negacao individual.
- Publicacoes usam o feed REST e o canal SSE do LuftBase.
- A `.env` passou a usar somente chaves canonicas `LUFT_*`; uma copia local
  recuperavel foi criada como `.env.pre-luftbase` e permanece ignorada pelo Git.
- Scripts SQL legados capazes de alterar o SQL Server foram removidos da arvore
  da aplicacao.

## Contrato do Vault

Para `LUFT_SISTEMA_ID=0`, o framework calcula:

| Recurso | Caminho |
|---|---|
| Diretorio SQL Server | `luft/{ambiente}/sqlserver` |
| PostgreSQL Aplicacao | `luft/{ambiente}/bancos/postgresql/sistemas/0` |
| PostgreSQL Conexao | `luft/{ambiente}/bancos/postgresql/conexoes/luft-web` |
| Sessoes Redis | `luft/{ambiente}/redis/sessoes` |

O segredo canonico informa `identificador`, `sistema_id`, conexao, schema e usuario. Depois da conexao,
o metadado oficial (`nome`, `descricao`, `ativo`, `em_manutencao`, `icone`, `link`) e carregado
diretamente de `core.tb_sistema`. Assim, `LUFT_APLICACAO_ID` e `LUFT_APLICACAO_NOME` nao pertencem ao `.env`; somente `LUFT_SISTEMA_ID` identifica a aplicacao no bootstrap.

Exemplo estrutural da credencial composta no Vault:

1. Conexao compartilhada (`.../conexoes/luft-web`):
```json
{
  "host": "<host>",
  "porta": "5432",
  "nome_banco": "luft_web",
  "sslmode": "prefer",
  "tipo_banco": "postgresql"
}
```

2. Credencial canonica do sistema (`.../sistemas/0`):
```json
{
  "conexao": "luft-web",
  "identificador": "luft-workspace",
  "sistema_id": 0,
  "esquema": "workspace",
  "usuario": "luft_workspace_app",
  "senha": "<segredo>"
}
```

A role de runtime nao pode ser administrativa. Ela precisa de `CONNECT` no
banco, `USAGE` no schema `core`, permissoes compativeis com os servicos do
LuftBase no `core`, e propriedade ou privilegios no schema particular. A
definicao exata deve ser revisada pelo DBA antes da homologacao.

## Sequencia de liberacao

1. Criar ou revisar os segredos dos tres ambientes sem alterar o SQL Server.
2. Confirmar que a role PostgreSQL nao e `admin`, `postgres` ou `sa`.
3. Instalar `requirements.txt` em uma nova `.venv` de homologacao.
4. Executar testes e `compileall` antes de reiniciar o servico.
5. Subir somente em homologacao e validar login, logout entre aplicacoes,
   catalogo, temas, publicacoes e autorizacao negativa.
6. Observar saude, prontidao, metricas e logs durante a janela do piloto.
7. Liberar producao apenas depois da aprovacao funcional e operacional.

Nenhuma etapa deste guia autoriza executar o migrador novamente. A migracao de
dados possui seu proprio procedimento e confirmacoes em
`MIGRACAO-CORE-POSTGRESQL.md`.

## Rollback

Antes do deploy, preserve o artefato e a `.venv` da versao anterior. Se o piloto
falhar:

1. pare o servico;
2. restaure o checkout/artefato anterior;
3. restaure a `.env` anterior a partir do cofre operacional ou da copia local
   protegida;
4. reinstale as dependencias da versao restaurada em uma `.venv` limpa;
5. reinicie e valide login, pagina inicial e logs.

O rollback da aplicacao nao deve apagar tabelas, schemas, segredos ou dados do
PostgreSQL. Mudancas de banco exigem procedimento separado e aprovacao do DBA.

## Criterios de aceite do piloto

- zero imports ou templates dependentes de LuftCore;
- nenhuma escrita possivel pela fronteira SQL Server;
- sistema global `0` consulta permissoes e continua negando por padrao;
- uma unica consulta para montar o catalogo de sistemas;
- logout revoga a sessao compartilhada;
- endpoints operacionais nao revelam host, usuario, senha ou erro de driver;
- pacote identico instalado em Windows e Linux;
- testes automatizados e compilacao aprovados;
- teste manual concluido em homologacao antes de producao.
