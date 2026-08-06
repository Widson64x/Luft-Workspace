# Luft Workspace

O **Luft Workspace** e o portal central, plataforma base e motor de integracao do ecossistema Luft. Ele fornece a infraestrutura foundational, autenticacao unificada, motor de ETL/orquestracao de dados e suporte a microservicos como **Luft-Control**, **Luft-ConnectAir**, **Luft-Docs**, **Luft-Integrador**, entre outros.

---

## Arquitetura e Modulos Principais

### 1. Orquestracao de Bancos de Dados (Motor ETL)
- **Execucao Multi-Banco:** Integracao direta entre SQL Server, Oracle e PostgreSQL sem dependencia de Linked Servers.
- **Mapeamento Inteligente de Campos:** Interface visual com suporte a transformacoes dinamicas (Trim, Maiusculas, Formatação de Data, Template, Valores Padrao, Auto-Sequencial).
- **Preview em Tempo Real & Teste de Query:** Editor SQL com destaque de sintaxe e autocomplete de variaveis e colunas da origem.
- **Carga Flexivel:** Modos `APPEND`, `TRUNCATE_APPEND` e `QUERY_DESTINO` customizada com comando `MERGE INTO`.
- **Agendamento Monitorado:** Agendamentos periodicos, diarios ou sob demanda com historico detalhado de execucoes.

### 2. Gestao de Credenciais & HashiCorp Vault
- **Conexoes Reutilizaveis:** Armazenamento seguro de segredos de banco de dados diretamente no HashiCorp Vault.
- **Abstracao de Conexao:** Centralizacao do ciclo de vida das credenciais compartilhadas pelo ecossistema.

### 3. Seguranca e Permissoes (RBAC)
- **LuftSecurity & LuftPermissionService:** Controle granular de acesso baseado em permissoes especificas por perfil e recurso.
- **Sessao Compartilhada:** Cookie de sessao unico para navegacao transparente entre o Hub e os microservicos cadastrados.

### 4. Operacoes de Ambiente & Diagnostico
- **Gerenciador de `.env`:** Leitura e atualizacao parametrizada de variaveis de ambiente de projetos vinculados.
- **Diagnostico Automatizado:** Script de migracao e verificacao dinamica da estrutura de tabelas no banco de dados.

---

## Modulos em Desenvolvimento (Roadmap)

### 1. Controle de APIs (API Management)
- Gateway centralizado de APIs do ecossistema.
- Aplicacao de limites de requisicao (*rate limiting*).
- Proxy de autenticacao e auditoria de chamadas externas.

### 2. Gestao de Rotas (Route Management)
- Roteamento dinamico de requisicoes para os microservicos ativos.
- Regras parametrizadas de proxy reverso e redirecionamento.

### 3. Observabilidade e Telemetria
- Centralizacao de logs de execucao e metricas de performance.
- Alertas em tempo real para falhas de integracao e timeouts.

---

## Guia de Desenvolvimento

### Requisitos Tecnicos
- **Python:** 3.10 ou superior.
- **Banco de Dados:** Microsoft SQL Server (instancia de homologacao/producao).
- **Drivers:** ODBC Driver 17 for SQL Server, Oracle Instant Client (quando aplicavel ao ecossistema).
- **Vault:** Acesso configurado ao servidor HashiCorp Vault da organizacao.

### Configuracao e Execucao Local

1. **Clonar o Repositorio:**
   ```powershell
   git clone <URL_DO_REPOSITORIO>
   cd LuftIntegrador
   ```

2. **Ambiente Virtual e Dependencias:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Variaveis de Ambiente (`.env`):**
   Crie o arquivo `.env` na raiz do projeto contendo as definicoes de banco e seguranca:
   ```env
   APP_NAME=Luft Workspace
   APP_ENV=development
   HOST=127.0.0.1
   PORT=9000
   ```

4. **Executar a Aplicacao:**
   ```powershell
   py .\Wsgi.py
   ```
   Acesse a aplicacao em `http://127.0.0.1:9000`.

---

## Padroes de Codigo do Projeto

- **Nomenclatura Python:** Estritamente em `snake_case` para funcoes, metodos e variaveis; `PascalCase` para classes.
- **Nomenclatura JavaScript:** Estritamente em `camelCase` para variaveis e funcoes; `PascalCase` para classes.
- **Nomenclatura SQL:** Palavras-chave em `UPPER_CASE` e tabelas/colunas em `PascalCase` ou `snake_case` padronizado.
- **Dominio em PT-BR:** Nomes de classes, metodos e variaveis de negocio devem ser redigidos em Portugues do Brasil.
- **Documentacao:** Docstrings obrigatorias detalhando proposito, parametros (`params`) e retorno (`returns`).

---

## Fluxo de Trabalho Git (Homologacao)

1. **Criar a branch de trabalho:**
   ```powershell
   git checkout -b feature/nome-da-sua-feature
   ```

2. **Adicionar alteracoes e realizar commit:**
   ```powershell
   git add .
   git commit -m "feat: descricao objetiva da alteracao"
   ```

3. **Enviar a branch para o remoto:**
   ```powershell
   git push -u origin feature/nome-da-sua-feature
   ```

4. **Abrir Pull Request (PR):**
   - No GitHub, abra a solicitacao de merge.
   - **ATENCAO:** Altere a branch de destino (*base branch*) de `main` para `homologacao`.