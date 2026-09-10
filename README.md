# Luft Workspace

O **Luft Workspace** e o portal central e a plataforma base do ecossistema Luft. Ele fornece autenticacao unificada, administracao dos sistemas e suporte a microservicos como **Luft-Control**, **Luft-ConnectAir**, **Luft-Docs**, **Luft-Integrador**, entre outros.

---

## Arquitetura e Modulos Principais

### 1. Seguranca e Permissoes (RBAC)
- **LuftSecurity & LuftPermissionService:** Controle granular de acesso baseado em permissoes especificas por perfil e recurso.
- **Sessao Compartilhada:** Cookie de sessao unico para navegacao transparente entre o Hub e os microservicos cadastrados.

### 2. Operacoes de Ambiente & Diagnostico
- **Gerenciador de `.env`:** Leitura e atualizacao parametrizada de variaveis de ambiente de projetos vinculados.
- **Diagnostico Automatizado:** Script de migracao e verificacao dinamica da estrutura de tabelas no banco de dados.
- **Painel Centralizado:** Permissoes, aplicacoes e ambiente sao administrados pelas abas da rota `/configuracoes`, fornecida pelo LuftCore.

### Extensoes futuras do Painel de Controle

O template `App/Templates/Pages/Configs/Configuracoes.html` herda o painel do LuftCore sem alterar seu conteudo. Particularidades futuras do Workspace podem ser adicionadas pelos blocos de extensao `extra_tabs`, `extra_cards_configuracoes`, `config_custom` e `extra_tab_panels`.

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
- **Drivers:** ODBC Driver 17 for SQL Server.
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
