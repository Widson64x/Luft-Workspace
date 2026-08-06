(function InicializarCentralProcedimentos() {
    const endpointListarWorkflows = window.ProcedimentosEndpoints.listarWorkflows;
    const endpointDetalheWorkflow = window.ProcedimentosEndpoints.detalheWorkflow;
    const endpointHistoricoWorkflow = window.ProcedimentosEndpoints.historicoWorkflow;
    const endpointSalvarWorkflow = window.ProcedimentosEndpoints.salvarWorkflow;
    const endpointExecutarWorkflow = window.ProcedimentosEndpoints.executarWorkflow;
    const endpointListarConexoes = window.ProcedimentosEndpoints.listarConexoes;
    const endpointSalvarConexao = window.ProcedimentosEndpoints.salvarConexao;
    const endpointTestarConexao = window.ProcedimentosEndpoints.testarConexao;
    const endpointExcluirConexao = window.ProcedimentosEndpoints.excluirConexao;
    const endpointExcluirWorkflow = window.ProcedimentosEndpoints.excluirWorkflow;
    const endpointTestarOrigem = window.ProcedimentosEndpoints.testarOrigem;
    const endpointTestarWorkflow = window.ProcedimentosEndpoints.testarWorkflow;

    const dadosElemento = document.getElementById('procedimentosDados');
    const diagnosticoElemento = document.getElementById('procedimentosDiagnostico');
    const estruturaPronta = diagnosticoElemento?.dataset?.estruturaPronta === '1';
    const mensagemEstrutura = diagnosticoElemento?.dataset?.mensagem || 'Estrutura SQL não configurada.';

    const tabelaConexoesBody = document.querySelector('#tabelaConexoes tbody');
    const tabelaWorkflowsBody = document.querySelector('#tabelaWorkflows tbody');
    const listaHistorico = document.getElementById('listaHistoricoWorkflow');
    const historicoDescricao = document.getElementById('historicoDescricao');

    const filtroTextoWorkflow = document.getElementById('filtroTextoWorkflow');
    const filtroStatusWorkflow = document.getElementById('filtroStatusWorkflow');
    const filtroAtivoWorkflow = document.getElementById('filtroAtivoWorkflow');

    const btnNovaConexao = document.getElementById('btnNovaConexao');
    const btnSalvarConexaoModal = document.getElementById('btnSalvarConexaoModal');
    const btnAtualizarConexoes = document.getElementById('btnAtualizarConexoes');
    const btnNovoWorkflow = document.getElementById('btnNovoWorkflow');
    const btnSalvarWorkflowModal = document.getElementById('btnSalvarWorkflowModal');
    const btnAtualizarWorkflows = document.getElementById('btnAtualizarWorkflows');
    const btnTestarOrigem = document.getElementById('btnTestarOrigem');
    const btnAdicionarCampo = document.getElementById('btnAdicionarCampo');

    const previewCamposOrigem = document.getElementById('previewCamposOrigem');
    const tabelaMapaCamposBody = document.querySelector('#tabelaMapaCampos tbody');

    const seletorConexaoOrigem = document.getElementById('conexaoOrigemModal');
    const seletorConexaoDestino = document.getElementById('conexaoDestinoModal');
    const seletorModoDestino = document.getElementById('modoDestinoModal');
    const seletorTipoAgendamento = document.getElementById('tipoAgendamentoModal');

    // ==========================================
    // LOGICA DE ABAS PRINCIPAIS (MAIN TABS)
    // ==========================================
    const navMainTabs = document.getElementById('navMainTabs');
    if (navMainTabs) {
        navMainTabs.addEventListener('click', (evento) => {
            const btn = evento.target.closest('.hub-tab-btn');
            if (!btn) return;
            
            navMainTabs.querySelectorAll('.hub-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.hub-maintab-content').forEach(c => {
                c.classList.remove('active');
                c.style.display = 'none';
            });
            
            const tabId = btn.dataset.maintab;
            if (tabId) {
                const target = document.getElementById(tabId);
                if (target) {
                    target.style.display = 'block';
                    target.classList.add('active');
                }
            }
        });
    }
    let conexoes = [];
    let workflows = [];
    let idWorkflowHistorico = null;
    let mapaCamposAtual = [];
    let previewOrigemAtual = { colunas: [], amostras: [] };

    function escapeHtml(valor) {
        return String(valor || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function escapeHtmlCode(valor) {
        return String(valor || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;');
    }

    function destacarSintaxeSql(codigo) {
        let html = escapeHtmlCode(codigo || '');
        html = html.replace(/(\/\*[\s\S]*?\*\/|--.*$)/gm, '<span class="sql-comment">$1</span>');
        html = html.replace(/('(?:''|[^'])*')/g, '<span class="sql-string">$1</span>');
        html = html.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="sql-number">$1</span>');
        const keywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|AND|OR|WITH|AS|ORDER|BY|GROUP|HAVING|UNION|ALL|CASE|WHEN|THEN|ELSE|END|CAST|IN|NOT|NULL|IS|LIKE|ROW_NUMBER|OVER|PARTITION|INSERT|INTO|UPDATE|SET|DELETE|VALUES|TRUNCATE|DROP|ALTER|CREATE|TABLE)\b/gi;
        html = html.replace(keywords, (m) => `<span class="sql-keyword">${m.toUpperCase()}</span>`);
        const funcoes = /\b(TRIM|SUBSTR|SUBSTRING|LENGTH|COUNT|SUM|AVG|MAX|MIN|COALESCE|NVL|UPPER|LOWER|CONCAT|GETDATE|SYSDATETIME|SYSUTCDATETIME|DATEADD|DATEDIFF)\b/gi;
        html = html.replace(funcoes, (m) => `<span class="sql-function">${m.toUpperCase()}</span>`);
        return html;
    }

    function sincronizarHighlightSql(textarea, codeElement) {
        if (!textarea || !codeElement) return;
        
        let text = textarea.value;
        if (text.endsWith('\n')) {
            text += ' '; 
        }
        
        codeElement.innerHTML = destacarSintaxeSql(text);
        
        const pre = codeElement.parentElement;
        if (pre) {
            pre.scrollTop = textarea.scrollTop;
            pre.scrollLeft = textarea.scrollLeft;
        }
    }

    function ativarEditorSQL(idTextarea, idCode) {
        const textarea = document.getElementById(idTextarea);
        const codeElement = document.getElementById(idCode);
        if (!textarea || !codeElement) return;

        const syncFn = () => sincronizarHighlightSql(textarea, codeElement);

        textarea.addEventListener('input', syncFn);
        textarea.addEventListener('scroll', syncFn);
        
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                
                textarea.value = textarea.value.substring(0, start) + "    " + textarea.value.substring(end);
                textarea.selectionStart = textarea.selectionEnd = start + 4;
                syncFn();
            }
        });

        syncFn();
    }

    ativarEditorSQL('origemQueryModal', 'origemQueryCode');
    ativarEditorSQL('queryDestinoModal', 'queryDestinoCode');
    ativarEditorSQL('origemQueryExpandidaModal', 'origemQueryExpandidaCode');

    const SQL_KEYWORDS = [
        'SELECT', 'INSERT INTO', 'UPDATE', 'DELETE', 'MERGE INTO', 'USING', 'WHEN MATCHED THEN', 'WHEN NOT MATCHED THEN',
        'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'ON', 'GROUP BY', 'ORDER BY', 'HAVING',
        'AS', 'AND', 'OR', 'IS NULL', 'IS NOT NULL', 'COALESCE(', 'UPPER(', 'LOWER(', 'TRIM(', 'GETDATE()'
    ];

    function obterSugestoesAutocompleteDestino() {
        const itens = [];
        const conjunto = new Set();

        function adicionar(nome, tipo, detalhe = '') {
            if (!nome || conjunto.has(nome)) return;
            conjunto.add(nome);
            itens.push({ nome, tipo, detalhe });
        }

        coletarMapaCamposDaTabela();
        (mapaCamposAtual || []).forEach(c => {
            if (c.nomeCampoDestino) {
                adicionar(c.nomeCampoDestino, 'Campo Destino', c.nomeCampoOrigem ? `Origem: ${c.nomeCampoOrigem}` : 'Mapeado');
            }
        });

        (previewOrigemAtual?.colunas || []).forEach(col => {
            adicionar(col, 'Coluna Origem', 'Origem');
        });

        const sqlOrigem = document.getElementById('origemQueryModal')?.value || '';
        if (sqlOrigem) {
            const regexCte = /(?:WITH|,)\s*([A-Za-z0-9_]+)\s+AS\s*\(/gi;
            let match;
            while ((match = regexCte.exec(sqlOrigem)) !== null) {
                adicionar(match[1], 'CTE Origem', 'Tabela Temporária');
            }

            const regexTabelas = /(?:FROM|JOIN)\s+([A-Za-z0-9_\.]+)(?:\s+(?:AS\s+)?([A-Za-z0-9_]+))?/gi;
            while ((match = regexTabelas.exec(sqlOrigem)) !== null) {
                const tabela = match[1];
                const alias = match[2];
                const palReservadas = ['SELECT', 'WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'];
                if (!palReservadas.includes(tabela.toUpperCase())) {
                    adicionar(tabela, 'Tabela Origem', alias ? `Alias: ${alias}` : 'Tabela');
                    if (alias && !['ON', 'AND', 'OR', 'WHERE', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'JOIN', 'AS'].includes(alias.toUpperCase())) {
                        adicionar(alias, 'Alias Tabela', `Alias de ${tabela}`);
                    }
                }
            }
        }

        return itens;
    }

    function configurarAutocompleteSQL(textareaId, menuId) {
        const textarea = document.getElementById(textareaId);
        const menu = document.getElementById(menuId);
        if (!textarea || !menu) return;

        let indexSelecionado = -1;
        let listaFiltrada = [];
        let modoAtual = null;

        function fecharMenu() {
            menu.style.display = 'none';
            indexSelecionado = -1;
            listaFiltrada = [];
            modoAtual = null;
        }

        function renderizarMenu(termo, contexto) {
            const ehEditorExpandido = textareaId === 'origemQueryExpandidaModal';
            const ehQueryDestino = textarea.dataset.origemEditor === 'queryDestinoModal';
            
            if (ehEditorExpandido && contexto === 'variavel' && !ehQueryDestino) {
                fecharMenu();
                return;
            }

            modoAtual = contexto;
            const sugestoesBase = obterSugestoesAutocompleteDestino();
            let sugestoes = [];

            if (contexto === 'variavel') {
                sugestoes = sugestoesBase.filter(i => i.tipo.includes('Campo') || i.tipo.includes('Coluna'));
            } else {
                sugestoes = sugestoesBase.filter(i => !i.tipo.includes('Campo') && !i.tipo.includes('Coluna'));
                SQL_KEYWORDS.forEach(kw => {
                    sugestoes.push({ nome: kw, tipo: 'Keyword', detalhe: 'Comando SQL' });
                });
            }

            const termoLower = (termo || '').toLowerCase();
            listaFiltrada = sugestoes.filter(item => 
                item.nome.toLowerCase().includes(termoLower) || 
                item.tipo.toLowerCase().includes(termoLower)
            );

            if (listaFiltrada.length === 0) {
                fecharMenu();
                return;
            }

            if (indexSelecionado >= listaFiltrada.length) indexSelecionado = 0;
            if (indexSelecionado < 0) indexSelecionado = 0;

            menu.innerHTML = listaFiltrada.map((item, idx) => `
                <div class="proc-autocomplete-item ${idx === indexSelecionado ? 'ativo' : ''}" data-idx="${idx}">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.75rem;">
                        <strong>${contexto === 'variavel' ? '@' : ''}${escapeHtml(item.nome)}</strong>
                        <span style="font-size: 0.72rem; opacity: 0.85; border-radius: 4px; padding: 0.1rem 0.35rem; background: var(--hub-cor-fundo); border: 1px solid var(--hub-cor-borda);">${escapeHtml(item.tipo)}</span>
                    </div>
                    ${item.detalhe ? `<small style="display: block; font-size: 0.7rem; opacity: 0.7; margin-top: 0.15rem;">${escapeHtml(item.detalhe)}</small>` : ''}
                </div>
            `).join('');

            menu.style.display = 'block';

            menu.querySelectorAll('.proc-autocomplete-item').forEach(el => {
                el.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const idx = Number(el.dataset.idx);
                    if (listaFiltrada[idx]) {
                        inserirSugestao(listaFiltrada[idx]);
                    }
                });
            });
        }

        function inserirSugestao(item) {
            const val = textarea.value;
            const pos = textarea.selectionStart;
            const textoAntes = val.substring(0, pos);
            
            let indexMatch = -1;
            let valorInserido = "";

            if (modoAtual === 'variavel') {
                indexMatch = textoAntes.lastIndexOf('@');
                const ehVariavel = item.tipo.includes('Campo') || item.tipo.includes('Coluna');
                valorInserido = ehVariavel ? `@{${item.nome}}` : item.nome;
            } else {
                const matchPalavra = textoAntes.match(/(?:^|[^A-Za-z0-9_@])([A-Za-z_][A-Za-z0-9_]*)$/);
                if (matchPalavra) {
                    indexMatch = textoAntes.lastIndexOf(matchPalavra[1]);
                    valorInserido = item.nome;
                }
            }

            if (indexMatch >= 0) {
                const parteInicial = val.substring(0, indexMatch);
                const parteFinal = val.substring(pos);
                
                textarea.value = parteInicial + valorInserido + parteFinal;
                const novaPos = indexMatch + valorInserido.length;
                textarea.focus();
                textarea.setSelectionRange(novaPos, novaPos);

                const codeId = textareaId === 'origemQueryExpandidaModal' ? 'origemQueryExpandidaCode' : (textareaId === 'queryDestinoModal' ? 'queryDestinoCode' : 'origemQueryCode');
                const codeEl = document.getElementById(codeId);
                if (codeEl) sincronizarHighlightSql(textarea, codeEl);
            }
            fecharMenu();
        }

        function verificarTrigger() {
            const val = textarea.value;
            const pos = textarea.selectionStart;
            const textoAntes = val.substring(0, pos);
            
            const matchArroba = textoAntes.match(/@([A-Za-z0-9_]*)$/);
            if (matchArroba) {
                renderizarMenu(matchArroba[1], 'variavel');
                return true;
            }

            const matchPalavra = textoAntes.match(/(?:^|[^A-Za-z0-9_@])([A-Za-z_][A-Za-z0-9_]{1,})$/);
            if (matchPalavra) {
                renderizarMenu(matchPalavra[1], 'sql');
                return true;
            }
            
            return false;
        }

        textarea.addEventListener('keyup', (e) => {
            if (['ArrowUp', 'ArrowDown', 'Enter', 'Escape', 'Tab'].includes(e.key)) return;
            if (!verificarTrigger()) fecharMenu();
        });

        textarea.addEventListener('click', () => {
            if (!verificarTrigger()) fecharMenu();
        });

        textarea.addEventListener('keydown', (e) => {
            if (menu.style.display === 'block') {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    indexSelecionado = (indexSelecionado + 1) % listaFiltrada.length;
                    verificarTrigger();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    indexSelecionado = (indexSelecionado - 1 + listaFiltrada.length) % listaFiltrada.length;
                    verificarTrigger();
                } else if ((e.key === 'Enter' || e.key === 'Tab') && indexSelecionado >= 0 && listaFiltrada[indexSelecionado]) {
                    e.preventDefault();
                    inserirSugestao(listaFiltrada[indexSelecionado]);
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    e.stopPropagation();
                    fecharMenu();
                }
            }
        });

        document.addEventListener('click', (e) => {
            if (e.target !== textarea && !menu.contains(e.target)) {
                fecharMenu();
            }
        });
    }

    configurarAutocompleteSQL('queryDestinoModal', 'autocompleteVariaveis');
    configurarAutocompleteSQL('origemQueryExpandidaModal', 'autocompleteVariaveisExpandido');

    function dadosResposta(payload) {
        if (payload && typeof payload === 'object') {
            if (payload.dados && typeof payload.dados === 'object') return payload.dados;
            if (payload.data && typeof payload.data === 'object') return payload.data;
            return payload;
        }
        return {};
    }

    function formatarData(dataIso) {
        if (!dataIso) return 'Nao executado';
        const data = new Date(dataIso);
        if (Number.isNaN(data.getTime())) return dataIso;
        return data.toLocaleString('pt-BR');
    }

    function formatarDuracao(duracaoMs) {
        const valor = Number(duracaoMs || 0);
        if (!valor) return '-';
        if (valor < 1000) return `${valor} ms`;
        const segundos = Math.floor(valor / 1000);
        if (segundos < 60) return `${segundos}s`;
        const minutos = Math.floor(segundos / 60);
        return `${minutos}m ${segundos % 60}s`;
    }

    function badgeStatus(status) {
        const valor = String(status || 'NUNCA_EXECUTADO').toUpperCase();
        const mapaClasse = {
            SUCESSO: 'proc-status-ok',
            ERRO: 'proc-status-erro',
            EM_EXECUCAO: 'proc-status-run',
            NUNCA_EXECUTADO: 'proc-status-neutro',
        };
        return `<span class="proc-status ${mapaClasse[valor] || 'proc-status-neutro'}">${escapeHtml(valor)}</span>`;
    }

    function atualizarKpis() {
        document.getElementById('kpiTotalWorkflows').textContent = String(workflows.length);
        document.getElementById('kpiTotalConexoes').textContent = String(conexoes.length);
        document.getElementById('kpiErros').textContent = String(workflows.filter((item) => item.statusUltimaExecucao === 'ERRO').length);
        document.getElementById('kpiAgendados').textContent = String(workflows.filter((item) => item.ativo && item.proximaExecucaoEm).length);
    }

    function aplicarFiltrosWorkflow() {
        const termo = String(filtroTextoWorkflow.value || '').trim().toLowerCase();
        const status = String(filtroStatusWorkflow.value || 'todos').toUpperCase();
        const situacao = String(filtroAtivoWorkflow.value || 'todos');

        return workflows.filter((item) => {
            const texto = [item.nomeProcedimento, item.nomeConexaoOrigem, item.nomeConexaoDestino, item.tabelaDestino, item.queryDestino].join(' ').toLowerCase();
            const atendeTexto = !termo || texto.includes(termo);
            const atendeStatus = status === 'TODOS' || String(item.statusUltimaExecucao || '').toUpperCase() === status;
            const atendeSituacao = situacao === 'todos' || (situacao === 'ativos' ? item.ativo : !item.ativo);
            return atendeTexto && atendeStatus && atendeSituacao;
        });
    }

    function renderizarConexoes() {
        if (!estruturaPronta) {
            tabelaConexoesBody.innerHTML = `<tr><td colspan="6">${escapeHtml(mensagemEstrutura)}</td></tr>`;
            return;
        }
        if (!conexoes.length) {
            tabelaConexoesBody.innerHTML = '<tr><td colspan="6">Nenhuma conexao cadastrada.</td></tr>';
            return;
        }

        tabelaConexoesBody.innerHTML = conexoes.map((item) => `
            <tr>
                <td><strong>${escapeHtml(item.nomeConexao)}</strong></td>
                <td>${escapeHtml(item.tipoBanco)}</td>
                <td><code>${escapeHtml(item.caminhoSegredoVault)}</code></td>
                <td>${escapeHtml(item.schemaPadrao || '-')}</td>
                <td>${item.ativo ? '<span class="proc-ativo-badge">ATIVA</span>' : '<span class="proc-inativo-badge">INATIVA</span>'}</td>
                <td>
                    <div class="proc-acoes-linha">
                        <button type="button" class="proc-btn-acao js-editar-conexao" data-id="${item.idConexao}" title="Editar conexao"><i class="ph-bold ph-pencil-simple"></i></button>
                        <button type="button" class="proc-btn-acao js-excluir-conexao" data-id="${item.idConexao}" title="Excluir conexao"><i class="ph-bold ph-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    function renderizarWorkflows() {
        if (!estruturaPronta) {
            tabelaWorkflowsBody.innerHTML = `<tr><td colspan="6">${escapeHtml(mensagemEstrutura)}</td></tr>`;
            return;
        }
        const itens = aplicarFiltrosWorkflow();
        if (!itens.length) {
            tabelaWorkflowsBody.innerHTML = '<tr><td colspan="6">Nenhuma tarefa encontrada para o filtro atual.</td></tr>';
            return;
        }

        tabelaWorkflowsBody.innerHTML = itens.map((item) => `
            <tr>
                <td>
                    <div class="proc-col-principal">
                        <strong>${escapeHtml(item.nomeProcedimento)}</strong>
                        <small>${escapeHtml(item.descricaoProcedimento || 'Sem descricao tecnica')}</small>
                        ${item.ativo ? '<span class="proc-ativo-badge">ATIVA</span>' : '<span class="proc-inativo-badge">INATIVA</span>'}
                    </div>
                </td>
                <td>
                    <div class="proc-conexao-info">
                        <span class="proc-conexao-nome"><i class="ph-bold ph-database"></i> ${escapeHtml(item.nomeConexaoOrigem)}</span>
                    </div>
                </td>
                <td>
                    <div class="proc-conexao-info">
                        <span class="proc-conexao-nome"><i class="ph-bold ph-hard-drives"></i> ${escapeHtml(item.nomeConexaoDestino)}</span>
                        <span class="proc-tag-alvo">${escapeHtml(item.modoDestino === 'QUERY_DESTINO' ? 'Query Customizada' : `${item.schemaDestino}.${item.tabelaDestino}`)}</span>
                    </div>
                </td>
                <td>${escapeHtml(item.descricaoAgendamento || 'Manual')}</td>
                <td>
                    <div>${badgeStatus(item.statusUltimaExecucao)}</div>
                    <small>${escapeHtml(formatarData(item.ultimaExecucaoEm))} | ${escapeHtml(formatarDuracao(item.duracaoUltimaExecucaoMs))}</small>
                </td>
                <td>
                    <div class="proc-acoes-linha">
                        <button type="button" class="proc-btn-acao js-historico-workflow" data-id="${item.idProcedimento}" title="Historico"><i class="ph-bold ph-clock-counter-clockwise"></i></button>
                        <button type="button" class="proc-btn-acao js-editar-workflow" data-id="${item.idProcedimento}" title="Editar"><i class="ph-bold ph-pencil-simple"></i></button>
                        <button type="button" class="proc-btn-acao js-executar-workflow" data-id="${item.idProcedimento}" title="Executar"><i class="ph-bold ph-play"></i></button>
                        <button type="button" class="proc-btn-acao js-excluir-workflow" data-id="${item.idProcedimento}" title="Excluir"><i class="ph-bold ph-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    function preencherSeletoresConexao() {
        const opcoes = conexoes.filter((item) => item.ativo).map((item) => `<option value="${item.idConexao}">${escapeHtml(item.nomeConexao)} [${escapeHtml(item.tipoBanco)}]</option>`).join('');
        seletorConexaoOrigem.innerHTML = `<option value="">Selecione</option>${opcoes}`;
        seletorConexaoDestino.innerHTML = `<option value="">Selecione</option>${opcoes}`;
    }

    async function carregarConexoes() {
        if (!estruturaPronta) {
            renderizarConexoes();
            return;
        }
        const resposta = await fetch(endpointListarConexoes, { cache: 'no-cache' });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao carregar conexoes.');
        conexoes = Array.isArray(dadosResposta(conteudo).conexoes) ? dadosResposta(conteudo).conexoes : [];
        preencherSeletoresConexao();
        atualizarKpis();
        renderizarConexoes();
    }

    async function carregarWorkflows() {
        if (!estruturaPronta) {
            renderizarWorkflows();
            return;
        }
        const resposta = await fetch(endpointListarWorkflows, { cache: 'no-cache' });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao carregar tarefas.');
        workflows = Array.isArray(dadosResposta(conteudo).procedimentos) ? dadosResposta(conteudo).procedimentos : [];
        atualizarKpis();
        renderizarWorkflows();
        if (idWorkflowHistorico) await carregarHistorico(idWorkflowHistorico);
    }

    async function carregarHistorico(idWorkflow) {
        const historicoDescricao = document.getElementById('historicoDescricaoModal');
        const listaHistorico = document.getElementById('listaHistoricoWorkflowModal');
        if (!listaHistorico) return;

        if (!estruturaPronta) {
            listaHistorico.innerHTML = `<p class="proc-historico-vazio">${escapeHtml(mensagemEstrutura)}</p>`;
            return;
        }
        idWorkflowHistorico = Number(idWorkflow);
        const workflow = workflows.find((item) => Number(item.idProcedimento) === Number(idWorkflow));
        if (historicoDescricao) {
            historicoDescricao.textContent = workflow ? `Histórico recente de "${workflow.nomeProcedimento}"` : 'Histórico da tarefa selecionada.';
        }
        listaHistorico.innerHTML = '<p class="proc-historico-vazio"><i class="ph-bold ph-circle-notch proc-spin"></i> Carregando histórico...</p>';

        const resposta = await fetch(`${endpointHistoricoWorkflow}?idProcedimento=${encodeURIComponent(idWorkflow)}`, { cache: 'no-cache' });
        const conteudo = await resposta.json();
        if (!resposta.ok) {
            listaHistorico.innerHTML = `<p class="proc-historico-vazio">${escapeHtml(conteudo?.mensagem || 'Falha ao carregar histórico.')}</p>`;
            return;
        }

        const historico = Array.isArray(dadosResposta(conteudo).historico) ? dadosResposta(conteudo).historico : [];
        if (!historico.length) {
            listaHistorico.innerHTML = '<p class="proc-historico-vazio">Nenhuma execução registrada para esta tarefa.</p>';
            return;
        }

        listaHistorico.innerHTML = historico.map((item) => `
            <article class="proc-historico-item" style="border: 1px solid var(--hub-cor-borda); border-radius: 8px; padding: 0.85rem; margin-bottom: 0.65rem; background: var(--hub-cor-superficie-2);">
                <div class="proc-historico-item-topo" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    ${badgeStatus(item.statusExecucao)}
                    <small style="color: var(--hub-cor-texto-suave); font-weight: 600;">${escapeHtml(formatarData(item.dataInicio))}</small>
                </div>
                <div class="proc-historico-item-corpo" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.5rem; font-size: 0.84rem; color: var(--hub-cor-texto);">
                    <div><strong>Origem:</strong> ${escapeHtml(String(item.totalLinhasOrigem || 0))}</div>
                    <div><strong>Processadas:</strong> ${escapeHtml(String(item.totalLinhasProcessadas || 0))}</div>
                    <div><strong>Escritas:</strong> ${escapeHtml(String(item.totalLinhasEscritas || 0))}</div>
                    <div><strong>Duração:</strong> ${escapeHtml(formatarDuracao(item.duracaoMs))}</div>
                    <div><strong>Executor:</strong> ${escapeHtml(item.executadoPor || '-')}</div>
                </div>
                ${item.mensagem ? `<div style="margin-top: 0.5rem; font-size: 0.82rem; color: var(--hub-cor-texto-suave); border-top: 1px dashed var(--hub-cor-borda); padding-top: 0.4rem;"><strong>Mensagem:</strong> ${escapeHtml(item.mensagem)}</div>` : ''}
            </article>
        `).join('');
    }

    function resetarModalConexao() {
        document.getElementById('idConexaoModal').value = '0';
        document.getElementById('nomeConexaoModal').value = '';
        const tipo = String(document.getElementById('tipoBancoModal').value || 'MSSQL').toUpperCase();
        document.getElementById('caminhoSegredoVaultModal').value = '';
        document.getElementById('driverBancoModal').value = '';
        document.getElementById('schemaPadraoModal').value = (tipo === 'MSSQL' ? 'dbo' : (tipo === 'POSTGRESQL' ? 'public' : ''));
        document.getElementById('parametrosConexaoModal').value = (tipo === 'MSSQL' ? '{\n  "TrustServerCertificate": "yes"\n}' : '{}');
        document.getElementById('observacaoConexaoModal').value = '';
        document.getElementById('ativoConexaoModal').checked = true;
    }

    function abrirEdicaoConexao(idConexao) {
        const conexao = conexoes.find((item) => Number(item.idConexao) === Number(idConexao));
        if (!conexao) return;
        document.getElementById('idConexaoModal').value = String(conexao.idConexao);
        document.getElementById('nomeConexaoModal').value = conexao.nomeConexao || '';
        document.getElementById('tipoBancoModal').value = conexao.tipoBanco || 'MSSQL';
        document.getElementById('caminhoSegredoVaultModal').value = conexao.caminhoSegredoVault || '';
        document.getElementById('driverBancoModal').value = conexao.driverBanco || '';
        document.getElementById('schemaPadraoModal').value = conexao.schemaPadrao || 'dbo';
        document.getElementById('parametrosConexaoModal').value = JSON.stringify(conexao.parametrosConexao || {}, null, 2);
        document.getElementById('observacaoConexaoModal').value = conexao.observacao || '';
        document.getElementById('ativoConexaoModal').checked = Boolean(conexao.ativo);
        LuftCore.abrirModal('modalConexaoIntegracao');
    }

    async function salvarConexao() {
        if (!estruturaPronta) {
            alert(mensagemEstrutura);
            return;
        }
        let parametrosConexao = {};
        const textoParametros = String(document.getElementById('parametrosConexaoModal').value || '').trim();
        if (textoParametros) {
            try {
                parametrosConexao = JSON.parse(textoParametros);
            } catch {
                alert('Parametros extras precisam estar em JSON valido.');
                return;
            }
        }
        const payload = {
            idConexao: Number(document.getElementById('idConexaoModal').value || 0),
            nomeConexao: document.getElementById('nomeConexaoModal').value,
            tipoBanco: document.getElementById('tipoBancoModal').value,
            caminhoSegredoVault: document.getElementById('caminhoSegredoVaultModal').value,
            driverBanco: document.getElementById('driverBancoModal').value,
            schemaPadrao: document.getElementById('schemaPadraoModal').value,
            parametrosConexao,
            observacao: document.getElementById('observacaoConexaoModal').value,
            ativo: document.getElementById('ativoConexaoModal').checked,
        };
        const resposta = await fetch(endpointSalvarConexao, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(payload),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao salvar conexao.');
        LuftCore.fecharModal('modalConexaoIntegracao');
        await carregarConexoes();
    }

    function resetarModalWorkflow() {
        document.getElementById('idWorkflowModal').value = '0';
        document.getElementById('nomeWorkflowModal').value = '';
        document.getElementById('descricaoWorkflowModal').value = '';
        document.getElementById('conexaoOrigemModal').value = '';
        document.getElementById('conexaoDestinoModal').value = '';
        
        document.getElementById('origemQueryModal').value = `SELECT 
    'SB1010 - COMPARTILHADA' AS Origem,
    B1_COD AS Codigo_Produto,
    B1_DESC AS Descricao_Produto,
    B1_CONTA AS Conta_Contabil_Padrao
FROM U_C1JTKS_PR.SB1010
WHERE TRIM(B1_COD) IN ('552071101', '5520707', '5520709', '5521409', '5520307', '5520711')
  AND D_E_L_E_T_ <> '*';`;

        document.getElementById('modoDestinoModal').value = 'TABELA_ALVO';
        
        document.getElementById('queryDestinoModal').value = `MERGE INTO Tb_Produtos_Luft AS Destino
USING (
    SELECT 
        @{Codigo_Produto} AS Codigo_Produto,
        @{Descricao_Produto} AS Descricao_Produto,
        @{Conta_Contabil_Padrao} AS Conta_Contabil_Padrao
) AS Origem 
ON (Destino.Codigo_Produto = Origem.Codigo_Produto)

WHEN MATCHED THEN 
    UPDATE SET 
        Destino.Descricao_Produto = Origem.Descricao_Produto,
        Destino.Conta_Contabil_Padrao = Origem.Conta_Contabil_Padrao

WHEN NOT MATCHED THEN
    INSERT (Codigo_Produto, Descricao_Produto, Conta_Contabil_Padrao) 
    VALUES (Origem.Codigo_Produto, Origem.Descricao_Produto, Origem.Conta_Contabil_Padrao);`;
        
        document.getElementById('schemaDestinoModal').value = 'dbo';
        document.getElementById('tabelaDestinoModal').value = '';
        document.getElementById('modoCargaModal').value = 'APPEND';
        document.getElementById('tipoAgendamentoModal').value = 'MANUAL';
        document.getElementById('intervaloMinutosModal').value = '15';
        document.getElementById('horarioExecucaoModal').value = '';
        document.getElementById('dataExecucaoEspecificaModal').value = '';
        document.getElementById('timeoutSegundosModal').value = '1800';
        document.getElementById('loteLinhasModal').value = '1000';
        document.getElementById('criarTabelaAutomaticamenteModal').checked = true;
        document.getElementById('ativoWorkflowModal').checked = true;
        mapaCamposAtual = [];
        previewOrigemAtual = { colunas: [], amostras: [] };
        renderizarTabelaMapaCampos();
        previewCamposOrigem.innerHTML = '<p class="proc-historico-vazio">Nenhuma query testada.</p>';
        previewTabelaOrigemWrap.innerHTML = '<p class="proc-historico-vazio">Nenhuma amostra carregada.</p>';
        atualizarCamposAgendamento();
        atualizarCamposDestino();
        sincronizarHighlightSql(document.getElementById('origemQueryModal'), document.getElementById('origemQueryCode'));
        sincronizarHighlightSql(document.getElementById('queryDestinoModal'), document.getElementById('queryDestinoCode'));
        ativarAbaWorkflow('pane-origem');
    }

    async function abrirEdicaoWorkflow(idWorkflow) {
        const resposta = await fetch(`${endpointDetalheWorkflow}?idProcedimento=${encodeURIComponent(idWorkflow)}`, { cache: 'no-cache' });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao carregar tarefa.');
        const workflow = dadosResposta(conteudo).procedimento || {};
        document.getElementById('idWorkflowModal').value = String(workflow.idProcedimento || 0);
        document.getElementById('nomeWorkflowModal').value = workflow.nomeProcedimento || '';
        document.getElementById('descricaoWorkflowModal').value = workflow.descricaoProcedimento || '';
        document.getElementById('conexaoOrigemModal').value = String(workflow.idConexaoOrigem || '');
        document.getElementById('conexaoDestinoModal').value = String(workflow.idConexaoDestino || '');
        document.getElementById('origemQueryModal').value = workflow.origemQuery || '';
        document.getElementById('modoDestinoModal').value = workflow.modoDestino || 'TABELA_ALVO';
        document.getElementById('queryDestinoModal').value = workflow.queryDestino || '';
        document.getElementById('schemaDestinoModal').value = workflow.schemaDestino || 'dbo';
        document.getElementById('tabelaDestinoModal').value = workflow.tabelaDestino || '';
        document.getElementById('modoCargaModal').value = workflow.modoCarga || 'APPEND';
        document.getElementById('tipoAgendamentoModal').value = workflow.tipoAgendamento || 'MANUAL';
        document.getElementById('intervaloMinutosModal').value = workflow.intervaloMinutos || '15';
        document.getElementById('horarioExecucaoModal').value = workflow.horarioExecucao || '';
        document.getElementById('dataExecucaoEspecificaModal').value = workflow.dataExecucaoEspecifica ? workflow.dataExecucaoEspecifica.slice(0, 16) : '';
        document.getElementById('timeoutSegundosModal').value = workflow.timeoutSegundos || '1800';
        document.getElementById('loteLinhasModal').value = workflow.loteLinhas || '1000';
        document.getElementById('criarTabelaAutomaticamenteModal').checked = Boolean(workflow.criarTabelaAutomaticamente);
        document.getElementById('ativoWorkflowModal').checked = Boolean(workflow.ativo);
        mapaCamposAtual = Array.isArray(workflow.mapaCampos) ? workflow.mapaCampos : [];
        renderizarTabelaMapaCampos();
        atualizarCamposAgendamento();
        atualizarCamposDestino();
        sincronizarHighlightSql(document.getElementById('origemQueryModal'), document.getElementById('origemQueryCode'));
        sincronizarHighlightSql(document.getElementById('queryDestinoModal'), document.getElementById('queryDestinoCode'));
        ativarAbaWorkflow('pane-origem');
        LuftCore.abrirModal('modalWorkflowIntegracao');
    }

    function atualizarCamposAgendamento() {
        const tipo = String(seletorTipoAgendamento.value || 'MANUAL');
        const blocoIntervalo = document.getElementById('blocoIntervaloMinutosModal');
        const blocoHorario = document.getElementById('blocoHorarioExecucaoModal');
        const blocoData = document.getElementById('blocoDataExecucaoEspecificaModal');

        if (blocoIntervalo) blocoIntervalo.style.display = (tipo === 'INTERVALO' ? 'block' : 'none');
        if (blocoHorario) blocoHorario.style.display = (tipo === 'DIARIO' ? 'block' : 'none');
        if (blocoData) blocoData.style.display = (tipo === 'DATA_ESPECIFICA' ? 'block' : 'none');
    }

    function atualizarCamposDestino() {
        const modo = String(seletorModoDestino.value || 'TABELA_ALVO');
        document.querySelectorAll('.proc-campo-destino-tabela').forEach((elemento) => {
            elemento.style.display = (modo === 'TABELA_ALVO' ? 'block' : 'none');
        });
        document.querySelectorAll('.proc-campo-destino-query').forEach((elemento) => {
            elemento.style.display = (modo === 'QUERY_DESTINO' ? 'block' : 'none');
        });

        const tabMapeamento = document.getElementById('tabMapeamento');
        if (tabMapeamento) {
            tabMapeamento.style.display = (modo === 'QUERY_DESTINO' ? 'none' : 'flex');
            if (modo === 'QUERY_DESTINO' && tabMapeamento.classList.contains('active')) {
                ativarAbaWorkflow('pane-origem');
            }
        }
    }

    function renderizarPreviewCampos(colunas) {
        if (!Array.isArray(colunas) || !colunas.length) {
            previewCamposOrigem.innerHTML = '<p class="proc-historico-vazio">Nenhuma coluna encontrada.</p>';
            return;
        }
        previewCamposOrigem.innerHTML = colunas.map((coluna) => `
            <article class="proc-campo-preview-item">
                <strong>${escapeHtml(coluna.nomeCampo)}</strong>
                <small>${escapeHtml(coluna.tipoInferido)} | nulos na amostra: ${escapeHtml(String(coluna.nulosNaAmostra))}</small>
                <span>Exemplo: ${escapeHtml(coluna.exemplo ?? '-')}</span>
            </article>
        `).join('');
    }

    function renderizarTabelaPreview(container, linhas) {
        if (!Array.isArray(linhas) || !linhas.length) {
            container.innerHTML = '<p class="proc-historico-vazio">Nenhuma linha disponível na amostra.</p>';
            return;
        }
        const colunas = Object.keys(linhas[0] || {});
        const cabecalho = colunas.map((coluna) => `<th>${escapeHtml(coluna)}</th>`).join('');
        const corpo = linhas.map((linha, idx) => `
            <tr>
                <td class="proc-td-num">${idx + 1}</td>
                ${colunas.map((coluna) => `<td title="${escapeHtml(String(linha[coluna] ?? ''))}">${escapeHtml(String(linha[coluna] ?? ''))}</td>`).join('')}
            </tr>
        `).join('');

        container.innerHTML = `
            <table class="proc-datagrid">
                <thead>
                    <tr>
                        <th class="proc-th-num">#</th>
                        ${cabecalho}
                    </tr>
                </thead>
                <tbody>${corpo}</tbody>
            </table>
        `;
    }

    function renderizarTabelaMapaCampos() {
        const badge = document.getElementById('badgeTotalMapeamentos');
        if (badge) badge.textContent = `${mapaCamposAtual.length} mapeados`;

        const tabelaBody = document.querySelector('#tabelaMapaCampos tbody');
        if (!tabelaBody) return;

        if (!mapaCamposAtual.length) {
            tabelaBody.innerHTML = '<tr><td colspan="7" class="proc-historico-vazio">Clique em "Adicionar Campo" ou em "Gerar da Origem" para iniciar o mapeamento.</td></tr>';
            return;
        }

        tabelaBody.innerHTML = mapaCamposAtual.map((campo, indice) => `
            <tr data-indice="${indice}">
                <td><input class="form-control js-mapa-origem" type="text" value="${escapeHtml(campo.nomeCampoOrigem || '')}" placeholder="Ex.: C3_NUM" ${campo.tipoTransformacao === 'AUTO_SEQUENCIAL' ? 'disabled' : ''}></td>
                <td><input class="form-control js-mapa-destino" type="text" value="${escapeHtml(campo.nomeCampoDestino || '')}" placeholder="Ex.: NumeroPedido"></td>
                <td>
                    <select class="form-control js-mapa-tipo" onchange="const tr = this.closest('tr'); if(this.value==='AUTO_SEQUENCIAL'){ tr.querySelector('.js-mapa-origem').value=''; tr.querySelector('.js-mapa-origem').disabled=true; } else { tr.querySelector('.js-mapa-origem').disabled=false; }">
                        ${['DIRETO','TEXTO_MAIUSCULO','TEXTO_MINUSCULO','TRIM','INTEGER','DECIMAL','BOOLEANO','DATA_ISO','TEMPLATE','VALOR_PADRAO','AUTO_SEQUENCIAL'].map((tipo) => `<option value="${tipo}" ${campo.tipoTransformacao === tipo ? 'selected' : ''}>${tipo}</option>`).join('')}
                    </select>
                </td>
                <td><input class="form-control js-mapa-expressao" type="text" value="${escapeHtml(campo.expressaoTransformacao || '')}" placeholder="Ex.: {CampoA}-{CampoB}"></td>
                <td><input class="form-control js-mapa-padrao" type="text" value="${escapeHtml(campo.valorPadrao || '')}" placeholder="Ex.: 0"></td>
                <td style="text-align: center;" title="Define como Chave Primária (Upsert/PK)"><input class="js-mapa-chave" type="checkbox" ${campo.eChave ? 'checked' : ''}></td>
                <td><input class="form-control js-mapa-seq" type="number" value="${campo.ultimoValorSequencial || 0}" ${campo.tipoTransformacao === 'AUTO_SEQUENCIAL' ? '' : 'disabled'}></td>
                <td style="text-align: center;"><input class="js-mapa-ativo" type="checkbox" ${campo.ativo !== false ? 'checked' : ''}></td>
                <td style="text-align: center;"><button type="button" class="proc-btn-acao js-remover-campo" title="Remover este campo"><i class="ph-bold ph-trash"></i></button></td>
            </tr>
        `).join('');
    }

    function coletarMapaCamposDaTabela() {
        mapaCamposAtual = Array.from(tabelaMapaCamposBody.querySelectorAll('tr[data-indice]')).map((linha, indice) => ({
            ordemExecucao: indice + 1,
            nomeCampoOrigem: linha.querySelector('.js-mapa-origem')?.value || '',
            nomeCampoDestino: linha.querySelector('.js-mapa-destino')?.value || '',
            tipoTransformacao: linha.querySelector('.js-mapa-tipo')?.value || 'DIRETO',
            expressaoTransformacao: linha.querySelector('.js-mapa-expressao')?.value || '',
            valorPadrao: linha.querySelector('.js-mapa-padrao')?.value || '',
            ativo: Boolean(linha.querySelector('.js-mapa-ativo')?.checked),
            eChave: Boolean(linha.querySelector('.js-mapa-chave')?.checked),
            ultimoValorSequencial: parseInt(linha.querySelector('.js-mapa-seq')?.value) || 0,
            idWorkflowCampo: mapaCamposAtual[indice]?.idWorkflowCampo || 0
        }));
    }

    async function testarOrigem() {
        if (!estruturaPronta) {
            alert(mensagemEstrutura);
            return;
        }
        const payload = {
            idConexaoOrigem: Number(document.getElementById('conexaoOrigemModal').value || 0),
            origemQuery: document.getElementById('origemQueryModal').value,
        };
        const resposta = await fetch(endpointTestarOrigem, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(payload),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao testar origem.');
        const dados = dadosResposta(conteudo);
        previewOrigemAtual = { colunas: dados.colunas || [], amostras: dados.amostras || [] };
        renderizarPreviewCampos(dados.colunas || []);
        renderizarTabelaPreview(previewTabelaOrigemWrap, dados.amostras || []);

        const badgeLinhas = document.getElementById('badgeTotalLinhasAmostra');
        const badgeCampos = document.getElementById('badgeTotalCamposAmostra');
        if (badgeLinhas) badgeLinhas.textContent = `${(dados.amostras || []).length} linhas`;
        if (badgeCampos) badgeCampos.textContent = `${(dados.colunas || []).length} colunas`;

        if (!mapaCamposAtual.length) {
            mapaCamposAtual = Array.isArray(dados.mapaCamposSugerido) ? dados.mapaCamposSugerido : [];
            renderizarTabelaMapaCampos();
        }
    }

    function montarObjetoWorkflow() {
        coletarMapaCamposDaTabela();
        return {
            idProcedimento: parseInt(document.getElementById('idWorkflowModal').value) || 0,
            nomeProcedimento: document.getElementById('nomeWorkflowModal').value,
            descricaoProcedimento: document.getElementById('descricaoWorkflowModal').value,
            idConexaoOrigem: parseInt(document.getElementById('conexaoOrigemModal').value) || 0,
            idConexaoDestino: parseInt(document.getElementById('conexaoDestinoModal').value) || 0,
            origemQuery: document.getElementById('origemQueryModal').value,
            modoDestino: document.getElementById('modoDestinoModal').value,
            queryDestino: document.getElementById('queryDestinoModal').value,
            schemaDestino: document.getElementById('schemaDestinoModal').value,
            tabelaDestino: document.getElementById('tabelaDestinoModal').value,
            modoCarga: document.getElementById('modoCargaModal').value,
            criarTabelaAutomaticamente: document.getElementById('criarTabelaAutomaticamenteModal').checked,
            tipoAgendamento: document.getElementById('tipoAgendamentoModal').value,
            configuracaoAgendamento: {
                horarioExecucao: document.getElementById('horarioExecucaoModal').value,
                dataExecucaoEspecifica: document.getElementById('dataExecucaoEspecificaModal').value,
            },
            intervaloMinutos: parseInt(document.getElementById('intervaloMinutosModal').value) || null,
            timeoutSegundos: parseInt(document.getElementById('timeoutSegundosModal').value) || 1800,
            loteLinhas: parseInt(document.getElementById('loteLinhasModal').value) || 1000,
            ativo: document.getElementById('ativoWorkflowModal').checked,
            mapaCampos: mapaCamposAtual,
        };
    }

    const textareaQueryDestino = document.getElementById('queryDestinoModal');
    const autocompleteMenu = document.getElementById('autocompleteVariaveis');
    let autocompleteIndex = -1;

    function renderizarAutocomplete(opcoes, left, top) {
        if (!opcoes || opcoes.length === 0) {
            autocompleteMenu.style.display = 'none';
            return;
        }
        autocompleteMenu.style.display = 'block';
        autocompleteMenu.style.left = left + 'px';
        autocompleteMenu.style.top = top + 'px';
        
        autocompleteMenu.innerHTML = opcoes.map((op, idx) => `
            <div class="proc-autocomplete-item ${idx === autocompleteIndex ? 'ativo' : ''}" data-valor="${escapeHtml(op)}">
                @${escapeHtml(op)}
            </div>
        `).join('');

        const itens = autocompleteMenu.querySelectorAll('.proc-autocomplete-item');
        itens.forEach(item => {
            item.addEventListener('click', () => inserirVariavelAutocomplete(item.dataset.valor));
        });
    }

    function inserirVariavelAutocomplete(valor) {
        const text = textareaQueryDestino.value;
        const pos = textareaQueryDestino.selectionStart;
        const indexArroba = text.lastIndexOf('@', pos - 1);
        
        if (indexArroba >= 0) {
            const inicio = text.substring(0, indexArroba);
            const fim = text.substring(pos);
            const novoTexto = inicio + '@{' + valor + '}' + fim;
            textareaQueryDestino.value = novoTexto;
            textareaQueryDestino.focus();
            const novaPos = indexArroba + valor.length + 3;
            textareaQueryDestino.setSelectionRange(novaPos, novaPos);
            sincronizarHighlightSql(textareaQueryDestino, document.getElementById('queryDestinoCode'));
        }
        autocompleteMenu.style.display = 'none';
    }

    textareaQueryDestino.addEventListener('input', (e) => {
        const val = textareaQueryDestino.value;
        const pos = textareaQueryDestino.selectionStart;
        
        const arr = val.substring(0, pos).split(/[\s,()=+-]/);
        const palavraAtual = arr[arr.length - 1];
        
        if (palavraAtual.startsWith('@')) {
            const termo = palavraAtual.substring(1).toLowerCase();
            const opcoes = previewOrigemAtual.colunas.filter(c => c.toLowerCase().includes(termo));
            
            const linhas = val.substring(0, pos).split('\n');
            const top = linhas.length * 20; 
            const left = 10;

            if (opcoes.length > 0) {
                if (autocompleteIndex >= opcoes.length) autocompleteIndex = 0;
                renderizarAutocomplete(opcoes, left, top);
            } else {
                autocompleteMenu.style.display = 'none';
            }
        } else {
            autocompleteMenu.style.display = 'none';
        }
    });

    textareaQueryDestino.addEventListener('keydown', (e) => {
        if (autocompleteMenu.style.display === 'block') {
            const itens = autocompleteMenu.querySelectorAll('.proc-autocomplete-item');
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                autocompleteIndex = (autocompleteIndex + 1) % itens.length;
                renderizarAutocomplete(previewOrigemAtual.colunas.filter(c => c.toLowerCase().includes(textareaQueryDestino.value.substring(textareaQueryDestino.value.lastIndexOf('@') + 1, textareaQueryDestino.selectionStart).toLowerCase())), parseInt(autocompleteMenu.style.left), parseInt(autocompleteMenu.style.top));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                autocompleteIndex = (autocompleteIndex - 1 + itens.length) % itens.length;
                renderizarAutocomplete(previewOrigemAtual.colunas.filter(c => c.toLowerCase().includes(textareaQueryDestino.value.substring(textareaQueryDestino.value.lastIndexOf('@') + 1, textareaQueryDestino.selectionStart).toLowerCase())), parseInt(autocompleteMenu.style.left), parseInt(autocompleteMenu.style.top));
            } else if (e.key === 'Enter' && autocompleteIndex >= 0 && itens[autocompleteIndex]) {
                e.preventDefault();
                inserirVariavelAutocomplete(itens[autocompleteIndex].dataset.valor);
            } else if (e.key === 'Escape') {
                autocompleteMenu.style.display = 'none';
            }
        }
    });

    document.addEventListener('click', (e) => {
        if (e.target !== textareaQueryDestino && !autocompleteMenu.contains(e.target)) {
            autocompleteMenu.style.display = 'none';
        }
    });

    async function salvarWorkflow() {
        const payload = montarObjetoWorkflow();
        const resposta = await fetch(endpointSalvarWorkflow, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(payload),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok || conteudo?.sucesso === false) {
            let msgErro = conteudo?.mensagem || conteudo?.message || 'Falha ao salvar tarefa.';
            if (conteudo?.detalhes) {
                const subMsg = typeof conteudo.detalhes === 'string' ? conteudo.detalhes : (conteudo.detalhes.erro || conteudo.detalhes.mensagem || '');
                if (subMsg && subMsg !== msgErro) {
                    msgErro += ` - ${subMsg}`;
                }
            }
            throw new Error(msgErro);
        }
        LuftCore.fecharModal('modalWorkflowIntegracao');
        await carregarWorkflows();
        LuftCore.notificar('sucesso', 'Tarefa salva com sucesso!');
    }

    async function executarWorkflow(idWorkflow) {
        const resposta = await fetch(endpointExecutarWorkflow, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ idProcedimento: idWorkflow }),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao executar tarefa.');
        await carregarWorkflows();
        await carregarHistorico(idWorkflow);
        alert(conteudo?.mensagem || 'Tarefa executada com sucesso.');
    }

    async function testarConexaoModal() {
        if (!estruturaPronta) {
            alert(mensagemEstrutura);
            return;
        }
        let parametrosConexao = {};
        const textoParametros = String(document.getElementById('parametrosConexaoModal').value || '').trim();
        if (textoParametros) {
            try {
                parametrosConexao = JSON.parse(textoParametros);
            } catch {
                alert('Parametros extras precisam estar em JSON valido.');
                return;
            }
        }
        const payload = {
            tipoBanco: document.getElementById('tipoBancoModal').value,
            caminhoSegredoVault: document.getElementById('caminhoSegredoVaultModal').value,
            driverBanco: document.getElementById('driverBancoModal').value,
            parametrosConexao,
        };
        const resposta = await fetch(endpointTestarConexao, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify(payload),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao testar conexao.');
        alert(conteudo?.mensagem || 'Conexao testada com sucesso!');
    }

    async function excluirConexao(idConexao) {
        if (!confirm('Deseja realmente excluir esta conexao?')) return;
        const resposta = await fetch(endpointExcluirConexao, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ idConexao: Number(idConexao) }),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao excluir conexao.');
        await carregarConexoes();
        alert(conteudo?.mensagem || 'Conexao excluida com sucesso.');
    }

    async function excluirWorkflow(idWorkflow) {
        if (!confirm('Deseja realmente excluir esta tarefa e todo o seu historico?')) return;
        const resposta = await fetch(endpointExcluirWorkflow, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ idProcedimento: Number(idWorkflow) }),
        });
        const conteudo = await resposta.json();
        if (!resposta.ok) throw new Error(conteudo?.mensagem || 'Falha ao excluir tarefa.');
        await carregarWorkflows();
        alert(conteudo?.mensagem || 'Tarefa excluida com sucesso.');
    }

    tabelaConexoesBody.addEventListener('click', async (evento) => {
        const btnEditar = evento.target.closest('.js-editar-conexao');
        if (btnEditar) {
            abrirEdicaoConexao(btnEditar.dataset.id);
            return;
        }
        const btnExcluir = evento.target.closest('.js-excluir-conexao');
        if (btnExcluir) {
            try {
                await excluirConexao(btnExcluir.dataset.id);
            } catch (erro) {
                alert(erro.message || 'Falha ao excluir conexao.');
            }
        }
    });

    tabelaWorkflowsBody.addEventListener('click', async (evento) => {
        const botao = evento.target.closest('button');
        if (!botao) return;
        try {
            if (botao.classList.contains('js-historico-workflow')) {
                await carregarHistorico(botao.dataset.id);
                LuftCore.abrirModal('modalHistoricoWorkflow');
                return;
            }
            if (botao.classList.contains('js-editar-workflow')) {
                await abrirEdicaoWorkflow(botao.dataset.id);
                return;
            }
            if (botao.classList.contains('js-executar-workflow')) {
                await executarWorkflow(botao.dataset.id);
                return;
            }
            if (botao.classList.contains('js-excluir-workflow')) {
                await excluirWorkflow(botao.dataset.id);
            }
        } catch (erro) {
            alert(erro.message || 'Falha ao executar a acao da tarefa.');
        }
    });

    tabelaMapaCamposBody.addEventListener('click', (evento) => {
        const botao = evento.target.closest('.js-remover-campo');
        if (!botao) return;
        const linha = botao.closest('tr');
        if (!linha) return;
        linha.remove();
        coletarMapaCamposDaTabela();
        renderizarTabelaMapaCampos();
    });

    filtroTextoWorkflow.addEventListener('input', renderizarWorkflows);
    filtroStatusWorkflow.addEventListener('change', renderizarWorkflows);
    filtroAtivoWorkflow.addEventListener('change', renderizarWorkflows);

    function ativarAbaWorkflow(idAba) {
        const abas = Array.from(document.querySelectorAll('#navAbasWorkflow .proc-modal-tab'));
        const paineis = Array.from(document.querySelectorAll('.proc-tab-pane'));
        const indiceAtual = abas.findIndex((aba) => aba.dataset.tab === idAba);
        if (indiceAtual === -1) return;

        abas.forEach((aba, idx) => aba.classList.toggle('active', idx === indiceAtual));
        paineis.forEach((painel) => painel.classList.toggle('active', painel.id === idAba));

        const btnAnterior = document.getElementById('btnAbaAnterior');
        const btnProximo = document.getElementById('btnAbaProximo');
        const btnSalvar = document.getElementById('btnSalvarWorkflowModal');
        
        if (btnAnterior) btnAnterior.style.visibility = (indiceAtual > 0 ? 'visible' : 'hidden');
        if (btnProximo) btnProximo.style.display = (indiceAtual < abas.length - 1 ? 'inline-flex' : 'none');
        if (btnSalvar) btnSalvar.style.display = (indiceAtual === abas.length - 1 ? 'inline-flex' : 'none');
    }

    async function executarComCarregando(botao, textoLoading, acaoAsync) {
        if (!botao) return await acaoAsync();
        const htmlOriginal = botao.innerHTML;
        botao.disabled = true;
        botao.innerHTML = `<i class="ph-bold ph-circle-notch proc-spin"></i> <span>${escapeHtml(textoLoading)}</span>`;
        try {
            return await acaoAsync();
        } finally {
            botao.innerHTML = htmlOriginal;
            botao.disabled = false;
        }
    }

    document.getElementById('navAbasWorkflow')?.addEventListener('click', (evento) => {
        const aba = evento.target.closest('.proc-modal-tab');
        if (aba && aba.dataset.tab) {
            ativarAbaWorkflow(aba.dataset.tab);
        }
    });

    document.getElementById('btnAbaProximo')?.addEventListener('click', () => {
        const abas = Array.from(document.querySelectorAll('#navAbasWorkflow .proc-modal-tab'));
        const indiceAtual = abas.findIndex((aba) => aba.classList.contains('active'));
        if (indiceAtual !== -1 && indiceAtual < abas.length - 1) {
            ativarAbaWorkflow(abas[indiceAtual + 1].dataset.tab);
        }
    });

    document.getElementById('btnAbaAnterior')?.addEventListener('click', () => {
        const abas = Array.from(document.querySelectorAll('#navAbasWorkflow .proc-modal-tab'));
        const indiceAtual = abas.findIndex((aba) => aba.classList.contains('active'));
        if (indiceAtual > 0) {
            ativarAbaWorkflow(abas[indiceAtual - 1].dataset.tab);
        }
    });

    document.getElementById('navAbasExplorer')?.addEventListener('click', (evento) => {
        const aba = evento.target.closest('.proc-explorer-tab');
        if (!aba || !aba.dataset.explorer) return;
        document.querySelectorAll('#navAbasExplorer .proc-explorer-tab').forEach((t) => t.classList.remove('active'));
        document.querySelectorAll('.proc-explorer-panel').forEach((p) => p.classList.remove('active'));
        aba.classList.add('active');
        document.getElementById(aba.dataset.explorer)?.classList.add('active');
    });

    const inputQueryMain = document.getElementById('origemQueryModal');
    const codeQueryMain = document.getElementById('origemQueryCode');
    const inputQueryExpandida = document.getElementById('origemQueryExpandidaModal');
    const codeQueryExpandida = document.getElementById('origemQueryExpandidaCode');

    inputQueryMain?.addEventListener('input', () => sincronizarHighlightSql(inputQueryMain, codeQueryMain));
    inputQueryMain?.addEventListener('scroll', () => sincronizarHighlightSql(inputQueryMain, codeQueryMain));

    inputQueryExpandida?.addEventListener('input', () => sincronizarHighlightSql(inputQueryExpandida, codeQueryExpandida));
    inputQueryExpandida?.addEventListener('scroll', () => sincronizarHighlightSql(inputQueryExpandida, codeQueryExpandida));

    document.getElementById('btnExpandirEditorQuery')?.addEventListener('click', () => {
        const inputMain = document.getElementById('origemQueryModal');
        const inputExp = document.getElementById('origemQueryExpandidaModal');
        const codeExp = document.getElementById('origemQueryExpandidaCode');
        if (inputExp && inputMain) {
            inputExp.value = inputMain.value;
            inputExp.dataset.origemEditor = 'origemQueryModal';
            sincronizarHighlightSql(inputExp, codeExp);
        }
        LuftCore.abrirModal('modalEditorQuerySql');
    });

    document.getElementById('btnExpandirEditorQueryDestino')?.addEventListener('click', () => {
        const inputDestino = document.getElementById('queryDestinoModal');
        const inputExp = document.getElementById('origemQueryExpandidaModal');
        const codeExp = document.getElementById('origemQueryExpandidaCode');
        if (inputExp && inputDestino) {
            inputExp.value = inputDestino.value;
            inputExp.dataset.origemEditor = 'queryDestinoModal';
            sincronizarHighlightSql(inputExp, codeExp);
        }
        LuftCore.abrirModal('modalEditorQuerySql');
    });

    document.getElementById('btnAplicarQueryExpandida')?.addEventListener('click', () => {
        const inputExp = document.getElementById('origemQueryExpandidaModal');
        const editorAlvoId = inputExp?.dataset?.origemEditor || 'origemQueryModal';
        const targetInput = document.getElementById(editorAlvoId);
        const targetCode = document.getElementById(editorAlvoId === 'origemQueryModal' ? 'origemQueryCode' : 'queryDestinoCode');
        if (targetInput && inputExp) {
            targetInput.value = inputExp.value;
            sincronizarHighlightSql(targetInput, targetCode);
        }
        LuftCore.fecharModal('modalEditorQuerySql');
    });

    btnNovaConexao.addEventListener('click', () => {
        if (!estruturaPronta) { alert(mensagemEstrutura); return; }
        resetarModalConexao();
        LuftCore.abrirModal('modalConexaoIntegracao');
    });
    document.getElementById('btnTestarConexaoModal')?.addEventListener('click', () => {
        const btn = document.getElementById('btnTestarConexaoModal');
        executarComCarregando(btn, 'Testando conexão...', testarConexaoModal).catch((erro) => alert(erro.message || 'Falha ao testar conexão.'));
    });
    btnSalvarConexaoModal.addEventListener('click', () => {
        executarComCarregando(btnSalvarConexaoModal, 'Salvando conexão...', salvarConexao).catch((erro) => alert(erro.message || 'Falha ao salvar conexão.'));
    });
    btnAtualizarConexoes.addEventListener('click', () => carregarConexoes().catch((erro) => alert(erro.message || 'Falha ao carregar conexões.')));

    btnNovoWorkflow.addEventListener('click', () => {
        if (!estruturaPronta) { alert(mensagemEstrutura); return; }
        resetarModalWorkflow();
        LuftCore.abrirModal('modalWorkflowIntegracao');
    });
    btnSalvarWorkflowModal.addEventListener('click', () => {
        executarComCarregando(btnSalvarWorkflowModal, 'Salvando tarefa...', salvarWorkflow).catch((erro) => {
            LuftCore.notificar('erro', erro.message || 'Falha ao salvar tarefa.');
        });
    });
    btnAtualizarWorkflows.addEventListener('click', () => carregarWorkflows().catch((erro) => alert(erro.message || 'Falha ao carregar tarefas.')));
    btnTestarOrigem.addEventListener('click', () => {
        executarComCarregando(btnTestarOrigem, 'Testando origem...', testarOrigem).catch((erro) => alert(erro.message || 'Falha ao testar origem.'));
    });
    const inputQueryDestino = document.getElementById('queryDestinoModal');
    const codeQueryDestino = document.getElementById('queryDestinoCode');
    inputQueryDestino?.addEventListener('input', () => sincronizarHighlightSql(inputQueryDestino, codeQueryDestino));
    inputQueryDestino?.addEventListener('scroll', () => sincronizarHighlightSql(inputQueryDestino, codeQueryDestino));

    btnAdicionarCampo.addEventListener('click', () => {
        coletarMapaCamposDaTabela();
        mapaCamposAtual.push({ ordemExecucao: mapaCamposAtual.length + 1, nomeCampoOrigem: '', nomeCampoDestino: '', tipoTransformacao: 'DIRETO', expressaoTransformacao: '', valorPadrao: '', ativo: true });
        renderizarTabelaMapaCampos();
    });

    document.getElementById('btnGerarMapeamentoSugerido')?.addEventListener('click', () => {
        if (previewOrigemAtual && Array.isArray(previewOrigemAtual.colunas) && previewOrigemAtual.colunas.length) {
            mapaCamposAtual = previewOrigemAtual.colunas.map((coluna, idx) => ({
                ordemExecucao: idx + 1,
                nomeCampoOrigem: coluna.nomeCampo,
                nomeCampoDestino: coluna.nomeCampo,
                tipoTransformacao: 'DIRETO',
                expressaoTransformacao: '',
                valorPadrao: '',
                ativo: true
            }));
            renderizarTabelaMapaCampos();
        } else {
            alert('Por favor, faça um teste de origem na Etapa 1 primeiro.');
        }
    });

    seletorTipoAgendamento.addEventListener('change', atualizarCamposAgendamento);
    seletorModoDestino.addEventListener('change', atualizarCamposDestino);
    document.getElementById('tipoBancoModal')?.addEventListener('change', (e) => {
        const tipo = String(e.target.value || '').toUpperCase();
        const campoParametros = document.getElementById('parametrosConexaoModal');
        if (tipo === 'MSSQL') {
            if (!campoParametros.value || campoParametros.value.trim() === '{}') {
                campoParametros.value = '{\n  "TrustServerCertificate": "yes"\n}';
            }
        } else {
            try {
                const parsed = JSON.parse(campoParametros.value || '{}');
                delete parsed.TrustServerCertificate;
                delete parsed.trustServerCertificate;
                campoParametros.value = Object.keys(parsed).length ? JSON.stringify(parsed, null, 2) : '{}';
            } catch {
                if (tipo !== 'MSSQL') campoParametros.value = '{}';
            }
        }
    });

    try {
        conexoes = JSON.parse(dadosElemento?.dataset?.conexoes || '[]');
    } catch {
        conexoes = [];
    }
    try {
        workflows = JSON.parse(dadosElemento?.dataset?.workflows || '[]');
    } catch {
        workflows = [];
    }

    preencherSeletoresConexao();
    atualizarCamposAgendamento();
    atualizarCamposDestino();
    atualizarKpis();
    renderizarConexoes();
    renderizarWorkflows();

    if (estruturaPronta) {
        carregarConexoes().catch((erro) => console.error(erro));
        carregarWorkflows().catch((erro) => console.error(erro));
    }
})();

// TUTORIAL INTERATIVO COM DRIVER.JS
window.iniciarTutorialWorkflow = function() {
    const driver = window.driver.js.driver;
    const seletorModo = document.getElementById('modoDestinoModal');
    
    function mudarModo(modo) {
        if(seletorModo) {
            seletorModo.value = modo;
            seletorModo.dispatchEvent(new Event('change'));
        }
    }

    function selecionarConexao(selectId, textoBusca) {
        const select = document.getElementById(selectId);
        if(!select) return;
        for (let i = 0; i < select.options.length; i++) {
            if (select.options[i].text.toUpperCase().includes(textoBusca.toUpperCase())) {
                select.selectedIndex = i;
                select.dispatchEvent(new Event('change'));
                break;
            }
        }
    }

    function rolarParaElemento(seletor) {
        setTimeout(() => {
            const el = document.querySelector(seletor);
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 50);
    }

    let passos = [
        { 
            element: 'button[data-tab="pane-origem"]', 
            popover: { title: '1. Setup & Origem', description: 'Nesta aba inicial você configura a tarefa, escolhe o Modo de Destino e de onde os dados serão lidos.', side: "bottom", align: 'start' },
            onHighlightStarted: (element) => { 
                mudarModo('TABELA_ALVO'); 
                document.querySelector('button[data-tab="pane-origem"]').click(); 
            }
        },
        { 
            element: '#nomeWorkflowModal', 
            popover: { title: 'Nome da Tarefa', description: 'Defina um nome curto e claro para a sua tarefa de orquestração.', side: "left", align: 'start' }
        },
        { 
            element: '#conexaoOrigemModal', 
            popover: { title: 'Conexão de Origem', description: 'Escolha de qual banco de dados os dados serão extraídos. Suas credenciais estão seguras no Vault.', side: "left", align: 'start' },
            onHighlightStarted: (element) => { selecionarConexao('conexaoOrigemModal', 'ORACLE'); }
        },
        { 
            element: '#modoDestinoModal', 
            popover: { title: 'Modo de Destino', description: 'Temos duas formas: <br><br><b>1. Tabela Alvo:</b> O sistema faz tudo baseado no mapeamento De-Para.<br><b>2. Query Customizada:</b> Você escreve a query.', side: "left", align: 'start' }
        },
        { 
            element: '#descricaoWorkflowModal', 
            popover: { title: 'Descrição Técnica', description: 'Detalhe a finalidade desta tarefa de orquestração.', side: "left", align: 'start' }
        },
        { 
            element: '#origemQueryModal', 
            popover: { title: 'Query de Origem', description: 'Escreva a query de extração aqui. Colunas que esta query retornar se tornarão variáveis no destino.', side: "left", align: 'start' }
        },
        { 
            element: '#btnExpandirEditorQuery', 
            popover: { title: 'Editor Expandido (Origem)', description: 'Para queries complexas, abra o Editor em Tela Cheia.', side: "bottom", align: 'start' }
        },
        { 
            element: '#modalEditorQuerySql .proc-editor-sql-wrap', 
            popover: { title: 'Modo Tela Cheia', description: 'Aqui dentro você pode escrever sua query confortavelmente.', side: "bottom", align: 'start' },
            onHighlightStarted: (element) => { document.getElementById('btnExpandirEditorQuery').click(); }
        },
        { 
            element: '#btnTestarOrigem', 
            popover: { title: 'Testar Origem', description: 'Clique para testar sua query e gerar a amostra de dados.', side: "bottom", align: 'start' },
            onHighlightStarted: (element) => { 
                LuftCore.fecharModal('modalEditorQuerySql'); 
                setTimeout(() => { document.getElementById('btnTestarOrigem').click(); }, 300);
            }
        },
        {
            element: '#navAbasExplorer',
            popover: { title: 'Data Explorer', description: 'Após o teste, veja os resultados da amostra e colunas inferidas.', side: "top", align: 'start' }
        },
        { 
            element: 'button[data-tab="pane-mapeamento"]', 
            popover: { title: '2. Mapeamento (Modo Tabela Alvo)', description: 'Configure como cada campo da origem deve ser gravado no destino.', side: "bottom", align: 'start' },
            onHighlightStarted: (element) => { 
                document.querySelector('button[data-tab="pane-mapeamento"]').click(); 
            }
        },
        { 
            element: '#btnGerarMapeamentoSugerido', 
            popover: { title: 'Mapeamento Automático', description: 'Gere a estrutura inicial de mapeamento com base na origem.', side: "left", align: 'start' },
            onHighlightStarted: (element) => {
                setTimeout(() => { document.getElementById('btnGerarMapeamentoSugerido').click(); }, 300);
            }
        },
        { 
            element: 'button[data-tab="pane-destino"]', 
            popover: { title: '3. Destino (Tabela Alvo)', description: 'Informe o banco de destino, schema e tabela.', side: "bottom", align: 'start' },
            onHighlightStarted: (element) => { document.querySelector('button[data-tab="pane-destino"]').click(); }
        },
        { 
            element: '#conexaoDestinoModal', 
            popover: { title: 'Conexão de Destino', description: 'Escolha o banco alvo onde as informações serão escritas.', side: "left", align: 'start' },
            onHighlightStarted: (element) => { selecionarConexao('conexaoDestinoModal', 'MSSQL'); }
        },
        { 
            element: 'button[data-tab="pane-agenda"]', 
            popover: { title: '4. Agenda & Performance', description: 'Configure o agendamento automático e limites de lote.', side: "bottom", align: 'start' },
            onHighlightStarted: (element) => { 
                LuftCore.fecharModal('modalEditorQuerySql');
                document.querySelector('button[data-tab="pane-agenda"]').click(); 
            }
        },
        { 
            element: '#btnSalvarWorkflowModal', 
            popover: { title: 'Finalizar!', description: 'Clique em Salvar para concluir o cadastro da tarefa.', side: "top", align: 'start' }
        }
    ];

    passos = passos.map(passo => {
        const original = passo.onHighlightStarted;
        passo.onHighlightStarted = (element) => {
            rolarParaElemento(passo.element);
            if (original) original(element);
        };
        return passo;
    });

    const driverObj = driver({
        showProgress: true,
        doneBtnText: 'Concluir',
        nextBtnText: 'Próximo',
        prevBtnText: 'Anterior',
        allowClose: true,
        steps: passos,
        onDestroyStarted: () => {
            document.querySelector('button[data-tab="pane-origem"]')?.click();
            mudarModo('TABELA_ALVO');
            driverObj.destroy();
        }
    });
    driverObj.drive();
};
