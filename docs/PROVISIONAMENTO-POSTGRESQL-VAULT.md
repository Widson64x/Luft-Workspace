# Provisionamento PostgreSQL e Vault

Este procedimento prepara as credenciais de runtime do banco local `luft_web`
sem alterar os segredos legados em `luft/desenvolvimento/postgresql`.

O LuftBase `0.1.0a3` consome a associacao canonica `sistemas/{id}`. Os caminhos
`aplicacoes/{slug}` permanecem preservados como origem da associacao e nao sao
sobrescritos ou removidos.

## Arvore nova e isolada

```text
luft/desenvolvimento/bancos/postgresql/
|-- conexoes/
|   `-- luft-web
`-- aplicacoes/
    |-- luft-connectair
    |-- luft-control
    |-- luft-docs
    |-- luft-integrador
    `-- luft-workspace
`-- sistemas/
    |-- 0
    |-- 1
    |-- 2
    |-- 3
    `-- 5
```

O caminho `conexoes/luft-web` contem apenas host, porta, banco, tipo e modo
SSL. Cada caminho em `aplicacoes/` contem o alias `luft-web`, o schema, o
usuario dedicado e sua senha. Assim, uma mudanca de servidor exige atualizar
uma unica conexao.

Cada `sistemas/{id}` referencia a mesma conexao e acrescenta `identificador` e
`sistema_id`. O runtime inicia somente por esse caminho, impedindo divergencia
entre slug e ID numerico.

## Situacao encontrada em 2026-09-16

- as roles `luft_*_app` existem e permitem login;
- nenhuma role de aplicacao possui senha configurada;
- cada role `luft_*_app` herda sua role `luft_*_rw`;
- nenhuma role de aplicacao estava conectada durante a auditoria;
- os schemas pertencem a `luft_web_owner`;
- apenas `luft_web_owner` pode criar objetos nos schemas de aplicacao;
- os privilegios padrao dos schemas de aplicacao estao configurados;
- as tabelas existentes no schema `core` ainda pertencem a `admin` e nao
  possuem GRANTs para as roles funcionais `luft_core_*`.

O ultimo item deve ser corrigido separadamente, com uma matriz de acesso por
servico. O provisionador nao concede privilegios e nao toca no SQL Server.

## Provisionamento concluido em 2026-09-16

O provisionamento foi executado com sucesso para as cinco aplicacoes. Uma
verificacao independente no PostgreSQL confirmou:

- `luft_connectair_app`, `luft_control_app`, `luft_docs_app`,
  `luft_integrador_app` e `luft_workspace_app` possuem senha configurada;
- os cinco verificadores usam `SCRAM-SHA-256`;
- nenhuma dessas roles possuia conexao ativa imediatamente apos a operacao;
- nenhum hash ou valor secreto foi exibido durante a verificacao.

O comando `provisionar` nao deve ser repetido. O CAS 0 e a verificacao de
senhas existentes devem recusar uma segunda execucao, preservando os valores
ja armazenados.

## Uso da CLI oficial

O script solicita de forma interativa:

- token de **operador** do Vault com acesso aos caminhos novos;
- senha administrativa do PostgreSQL local.

Nenhum dos dois valores deve ser informado em argumentos, `.env`, chat ou
arquivo. O token das aplicacoes nao deve ter permissao de escrita.

### 1. Auditoria sem escrita

```powershell
.\.venv\Scripts\python.exe -m luftbase vault postgresql auditar `
  --manifesto docs\manifesto-postgresql-desenvolvimento.json
```

### 2. Primeiro provisionamento

```powershell
.\.venv\Scripts\python.exe -m luftbase vault postgresql provisionar `
  --manifesto docs\manifesto-postgresql-desenvolvimento.json
```

Protecoes aplicadas:

- confirmacao textual obrigatoria;
- recusa roles ausentes, sem login, com senha ou em uso;
- KV v2 obrigatorio;
- `cas=0`, impedindo sobrescrita de qualquer segredo existente;
- uma senha aleatoria e diferente por aplicacao;
- envio ao PostgreSQL como verificador SCRAM-SHA-256, não como texto claro;
- nenhuma senha ou token e impresso.

### 3. Recuperacao de interrupcao

Se os segredos forem criados e a transacao PostgreSQL falhar, nao apague nem
recrie os caminhos. Corrija a conectividade ou permissao e execute:

```powershell
.\.venv\Scripts\python.exe -m luftbase vault postgresql aplicar-senhas-do-vault `
  --manifesto docs\manifesto-postgresql-desenvolvimento.json
```

### 4. Associar IDs de sistema sem sobrescrever segredos

Depois que os caminhos `aplicacoes/{slug}` existirem, execute uma unica vez:

```powershell
.\.venv\Scripts\python.exe -m luftbase vault postgresql associar-sistemas `
  --manifesto docs\manifesto-postgresql-desenvolvimento.json
```

O comando solicita somente o token de operador, pula destinos existentes e cria
os ausentes com CAS 0. Nao envie o token por argumento, arquivo, log ou chat.

Esse modo valida os campos dos segredos existentes e reaplica as senhas sem
mostrar seus valores.

## O que este procedimento nao faz

- nao sobrescreve `luft/desenvolvimento/postgresql`;
- nao reinicia, sela, configura ou move o Vault;
- nao apaga versoes ou metadados de segredos;
- nao altera schemas, tabelas, dados ou privilegios;
- nao altera o SQL Server;
- nao reinicia o Vault nem os servicos web.

Depois do provisionamento, devem ser executados testes de autenticação direta
para cada role e a matriz de privilegios do `core` deve ser implantada antes de
iniciar o Workspace com as novas credenciais.
