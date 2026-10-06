# Documentacao do Luft Workspace

[Voltar ao indice mestre](../../../Documentacao-Web/README.md)

## Finalidade

O Workspace e o portal raiz das ferramentas web da Luft. Ele autentica o
usuario, apresenta os sistemas autorizados e consome os recursos corporativos
do LuftBase. Nginx, NSSM/systemd e Vault continuam sendo componentes externos.

## Componentes

| Componente | Papel |
|---|---|
| `App/__init__.py` | factory Flask e composicao do LuftBase |
| `App/Routes/Autenticacao.py` | login LDAP e logout global |
| `App/Routes/Principal.py` | pagina inicial e catalogo de sistemas |
| `App/Routes/Publicacoes.py` | paginas HTML de publicacoes |
| `App/Routes/Configuracoes.py` | metadados operacionais nao sensiveis |
| `App/Services/Admin/SistemasHubService.py` | consulta otimizada do menu no `core` |
| `App/Templates` | telas especificas que estendem `luftbase/base.html` |
| `scripts/migrar_core_postgresql.py` | migrador historico, com origem SQL Server protegida |
| `scripts/provisionar_postgresql_vault.py` | provisionamento protegido das credenciais PostgreSQL no Vault |

## Dados e infraestrutura

- SQL Server: consulta de usuarios e grupos apenas; a fronteira do LuftBase
  rejeita escrita.
- PostgreSQL: tabelas sistemicas fixas no schema `core` e dados particulares no
  schema indicado pelo segredo da aplicacao.
- Redis: sessoes compartilhadas, revogacao, cache e sinalizacao de conteudo.
- Vault: unico local para credenciais; valores secretos nao aparecem no painel,
  health check ou logs.

## Ambientes

| Item | Homologacao | Producao |
|---|---|---|
| URL | `http://172.16.201.14/` | `http://b2bi-apps.luftfarma.com.br/` |
| Servico | `luft-workspace.service` | `Luft-Workspace` |
| Diretorio | `/home/suporte/Mirror_Python_80/ProjetosPython/Luft-Workspace` | `C:\ProjetosPython\Luft-Workspace` |
| Branch | `homologacao` | `main` |
| Sistema global | `LUFT_SISTEMA_ID=0` | `LUFT_SISTEMA_ID=0` |

## Operacao segura

Antes de liberar um ambiente, confira os tres segredos derivados, a role
PostgreSQL nao administrativa, as permissoes `HOME.VISUALIZAR` e
`ADMIN.CONFIGURACOES.VISUALIZAR`, e os endpoints `/_luftbase/saude` e
`/_luftbase/prontidao`. Os endpoints nunca substituem a verificacao de logs do
servico e do proxy reverso.

## Guias relacionados

- [Piloto M10: migracao para LuftBase](MIGRACAO-LUFTBASE.md)
- [Migracao do nucleo sistemico para PostgreSQL](MIGRACAO-CORE-POSTGRESQL.md)
