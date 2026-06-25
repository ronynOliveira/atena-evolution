/**
 * ATENA EVOLUÇÃO - Chat Holográfico
 * Frontend vanilla JS para comunicação com Ollama API
 * Versão: 2.0.0
 */

// ============================================
// CONFIGURAÇÃO E CONSTANTES
// ============================================
const CONFIG = {
    OLLAMA_URL: 'http://localhost:11434/api/generate',
    OLLAMA_MODELS_URL: 'http://localhost:11434/api/tags',
    DEFAULT_MODEL: 'hermes3:8b',
    TYPEWRITER_SPEED: 30, // ms por caractere
    MAX_HISTORY: 100,
    CHART_MAX_POINTS: 20
};

// ============================================
// ESTADO DA APLICAÇÃO
// ============================================
const state = {
    currentModel: CONFIG.DEFAULT_MODEL,
    models: [],
    messages: [],
    isGenerating: false,
    totalTokens: 0,
    sessionStartTime: Date.now(),
    performanceHistory: [], // {model, time, tokens}
    abortController: null
};

// ============================================
// ELEMENTOS DO DOM
// ============================================
let elements = {};

function cacheElements() {
    elements = {
        chatMessages: document.getElementById('chat-messages'),
        userInput: document.getElementById('user-input'),
        sendBtn: document.getElementById('send-btn'),
        modelSelect: document.getElementById('model-select'),
        modelName: document.getElementById('model-name'),
        responseTime: document.getElementById('response-time'),
        tokenCount: document.getElementById('token-count'),
        ramUsage: document.getElementById('ram-usage'),
        statusIndicator: document.getElementById('status-indicator'),
        statusText: document.getElementById('status-text'),
        loadingOverlay: document.getElementById('loading-overlay'),
        chart: document.getElementById('performance-chart'),
        clearBtn: document.getElementById('clear-btn'),
        versionInfo: document.getElementById('version-info'),
        costInfo: document.getElementById('cost-info'),
        typingIndicator: document.getElementById('typing-indicator')
    };
}

// ============================================
// TEMA CYBERPUNK - VARIÁVEIS CSS
// ============================================
const theme = {
    colors: {
        primary: '#00f0ff',
        secondary: '#ff00e5',
        accent: '#39ff14',
        background: '#0a0a1a',
        surface: '#1a1a2e',
        text: '#e0e0ff',
        textDim: '#6a7ba0',
        glow: '0 0 20px rgba(0,240,255,0.5)'
    }
};

// ============================================
// UTILIDADES
// ============================================
function formatTime(ms) {
    if (ms < 1000) return Math.round(ms) + 'ms';
    return (ms / 1000).toFixed(1) + 's';
}

function formatTokens(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// SISTEMA DE SOM (Web Audio API)
// ============================================
class SoundSystem {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
    }

    init() {
        if (!this.audioContext) {
            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            } catch (e) {
                this.enabled = false;
            }
        }
        return this.audioContext;
    }

    playNotification(type) {
        type = type || 'success';
        if (!this.enabled) return;
        try {
            const ctx = this.init();
            if (!ctx) return;
            const oscillator = ctx.createOscillator();
            const gainNode = ctx.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(ctx.destination);

            if (type === 'success') {
                oscillator.frequency.setValueAtTime(880, ctx.currentTime);
                oscillator.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.1);
                oscillator.type = 'sine';
            } else if (type === 'error') {
                oscillator.frequency.setValueAtTime(400, ctx.currentTime);
                oscillator.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.2);
                oscillator.type = 'square';
            } else if (type === 'send') {
                oscillator.frequency.setValueAtTime(600, ctx.currentTime);
                oscillator.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.05);
                oscillator.type = 'sine';
            }

            gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);

            oscillator.start(ctx.currentTime);
            oscillator.stop(ctx.currentTime + 0.15);
        } catch (e) {
            // Silenciar erros de audio
        }
    }
}

const sound = new SoundSystem();

// ============================================
// GRÁFICO DE PERFORMANCE (D3.js)
// ============================================
class PerformanceChart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = [];
        this.margin = { top: 20, right: 30, bottom: 40, left: 50 };
        this.width = 400;
        this.height = 150;
        this.init();
    }

    init() {
        // Verificar se D3 está disponível
        if (typeof d3 === 'undefined') {
            this.container.innerHTML = '<p style="color: #6a7ba0; text-align: center; padding-top: 40px;">D3.js não carregado</p>';
            return;
        }

        this.svg = d3.select('#' + this.container.id)
            .append('svg')
            .attr('width', '100%')
            .attr('height', this.height)
            .attr('viewBox', '0 0 ' + this.width + ' ' + this.height)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        // Definir gradientes
        const defs = this.svg.append('defs');
        
        const gradient = defs.append('linearGradient')
            .attr('id', 'chartGradient')
            .attr('x1', '0%').attr('y1', '0%')
            .attr('x2', '0%').attr('y2', '100%');
        
        gradient.append('stop').attr('offset', '0%').attr('stop-color', '#00f0ff').attr('stop-opacity', 0.3);
        gradient.append('stop').attr('offset', '100%').attr('stop-color', '#00f0ff').attr('stop-opacity', 0);

        // Título
        this.svg.append('text')
            .attr('x', 10)
            .attr('y', 15)
            .attr('fill', '#6a7ba0')
            .attr('font-size', '10px')
            .text('Tempo de Resposta por Modelo');

        this.g = this.svg.append('g')
            .attr('transform', 'translate(' + this.margin.left + ',' + this.margin.top + ')');
    }

    addDataPoint(model, timeMs, tokens) {
        this.data.push({
            model: model,
            time: timeMs,
            tokens: tokens,
            index: this.data.length,
            timestamp: new Date()
        });

        // Limitar pontos
        if (this.data.length > CONFIG.CHART_MAX_POINTS) {
            this.data.shift();
        }

        this.render();
    }

    render() {
        if (typeof d3 === 'undefined' || !this.svg) return;

        this.g.selectAll('*').remove();

        const innerWidth = this.width - this.margin.left - this.margin.right;
        const innerHeight = this.height - this.margin.top - this.margin.bottom;

        if (this.data.length === 0) return;

        // Escalas
        const xScale = d3.scaleLinear()
            .domain([0, Math.max(this.data.length - 1, 1)])
            .range([0, innerWidth]);

        const yMax = d3.max(this.data, function(d) { return d.time; }) || 1000;
        const yScale = d3.scaleLinear()
            .domain([0, yMax * 1.1])
            .range([innerHeight, 0]);

        // Linha
        const line = d3.line()
            .x(function(d, i) { return xScale(i); })
            .y(function(d) { return yScale(d.time); })
            .curve(d3.curveMonotoneX);

        // Área
        const area = d3.area()
            .x(function(d, i) { return xScale(i); })
            .y0(innerHeight)
            .y1(function(d) { return yScale(d.time); })
            .curve(d3.curveMonotoneX);

        // Eixo X
        this.g.append('g')
            .attr('transform', 'translate(0,' + innerHeight + ')')
            .call(d3.axisBottom(xScale).ticks(5).tickFormat(function(d) { return ''; }))
            .selectAll('text')
            .attr('fill', '#6a7ba0')
            .attr('font-size', '9px');

        // Eixo Y
        this.g.append('g')
            .call(d3.axisLeft(yScale).ticks(4).tickFormat(function(d) { return (d/1000).toFixed(1) + 's'; }))
            .selectAll('text')
            .attr('fill', '#6a7ba0')
            .attr('font-size', '9px');

        this.g.selectAll('.domain, .tick line')
            .attr('stroke', '#1a2a3a');

        // Grid
        this.g.append('g')
            .attr('class', 'grid')
            .selectAll('line')
            .data(yScale.ticks(4))
            .enter()
            .append('line')
            .attr('x1', 0).attr('x2', innerWidth)
            .attr('y1', function(d) { return yScale(d); }).attr('y2', function(d) { return yScale(d); })
            .attr('stroke', '#1a2a3a')
            .attr('stroke-dasharray', '2,2');

        // Área preenchida
        this.g.append('path')
            .datum(this.data)
            .attr('fill', 'url(#chartGradient)')
            .attr('d', area);

        // Linha
        const path = this.g.append('path')
            .datum(this.data)
            .attr('fill', 'none')
            .attr('stroke', '#00f0ff')
            .attr('stroke-width', 2)
            .attr('d', line);

        // Animação da linha
        const totalLength = path.node() ? path.node().getTotalLength() : 0;
        path
            .attr('stroke-dasharray', totalLength + ' ' + totalLength)
            .attr('stroke-dashoffset', totalLength)
            .transition()
            .duration(500)
            .attr('stroke-dashoffset', 0);

        // Pontos
        this.g.selectAll('.dot')
            .data(this.data)
            .enter()
            .append('circle')
            .attr('class', 'dot')
            .attr('cx', function(d, i) { return xScale(i); })
            .attr('cy', function(d) { return yScale(d.time); })
            .attr('r', 0)
            .attr('fill', (d) => this.getModelColor(d.model))
            .attr('stroke', '#fff')
            .attr('stroke-width', 1)
            .transition()
            .delay((d, i) => i * 30)
            .duration(300)
            .attr('r', 3);

        // Labels dos modelos
        this.g.selectAll('.label')
            .data(this.data)
            .enter()
            .append('text')
            .attr('x', (d, i) => xScale(i))
            .attr('y', d => yScale(d.time) - 8)
            .attr('fill', (d) => this.getModelColor(d.model))
            .attr('font-size', '8px')
            .attr('text-anchor', 'middle')
            .text((d, i) => i === this.data.length - 1 ? d.model.substring(0, 8) : '');
    }

    getModelColor(model) {
        const colors = ['#00f0ff', '#ff00e5', '#39ff14', '#ffd700', '#ff6b35'];
        let hash = 0;
        for (let i = 0; i < model.length; i++) {
            hash = model.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    }
}

let performanceChart;

// ============================================
// STATUS DO SISTEMA
// ============================================
function updateSystemStatus() {
    // RAM via performance API (Chrome-only memory API)
    if (performance.memory) {
        const memoryMB = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
        const totalMB = Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024);
        const percent = Math.round((memoryMB / totalMB) * 100);
        elements.ramUsage.textContent = 'RAM: ' + memoryMB + 'MB / ' + totalMB + 'MB (' + percent + '%)';
    } else {
        elements.ramUsage.textContent = 'RAM: API indisponível (use Chrome)';
    }

    // Modelo ativo
    elements.modelName.textContent = state.currentModel;

    // Status indicator
    if (state.isGenerating) {
        elements.statusIndicator.className = 'status-indicator generating';
        elements.statusText.textContent = 'Gerando resposta...';
    } else {
        elements.statusIndicator.className = 'status-indicator online';
        elements.statusText.textContent = 'Online';
    }

    // Token count
    elements.tokenCount.textContent = 'Tokens: ' + formatTokens(state.totalTokens);
}

// Atualizar status a cada segundo
setInterval(updateSystemStatus, 1000);

// ============================================
// CARREGAR MODELOS DISPONÍVEIS
// ============================================
async function loadModels() {
    try {
        const response = await fetch(CONFIG.OLLAMA_MODELS_URL);
        if (!response.ok) throw new Error('Erro ao carregar modelos');
        
        const data = await response.json();
        state.models = data.models || [];
        
        if (state.models.length === 0) {
            // Fallback caso nenhum modelo listado
            state.models = [{ name: CONFIG.DEFAULT_MODEL }];
        }

        // Preencher select
        elements.modelSelect.innerHTML = '';
        state.models.forEach(function(model) {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name;
            if (model.name === state.currentModel) {
                option.selected = true;
            }
            elements.modelSelect.appendChild(option);
        });

        // Verificar se o modelo padrão existe
        const hasDefault = state.models.some(function(m) { return m.name === CONFIG.DEFAULT_MODEL; });
        if (hasDefault) {
            state.currentModel = CONFIG.DEFAULT_MODEL;
        } else if (state.models.length > 0) {
            state.currentModel = state.models[0].name;
        }
        elements.modelSelect.value = state.currentModel;
    } catch (error) {
        console.error('Erro ao carregar modelos:', error);
        // Usar modelo padrão como fallback
        elements.modelSelect.innerHTML = '<option value="' + CONFIG.DEFAULT_MODEL + '">' + CONFIG.DEFAULT_MODEL + '</option>';
        elements.statusText.textContent = 'Ollama offline';
        elements.statusIndicator.className = 'status-indicator offline';
    }
}

// ============================================
// ANIMAÇÃO DE LOADING (Neon Dots)
// ============================================
function showLoadingDots() {
    elements.loadingOverlay.classList.add('active');
}

function hideLoadingDots() {
    elements.loadingOverlay.classList.remove('active');
}

// ============================================
// RENDERIZAR MENSAGEM NO CHAT
// ============================================
function createMessageElement(role, content) {
    content = content || '';
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-' + role;
    
    const avatar = role === 'user' ? '👤' : '🤖';
    const roleLabel = role === 'user' ? 'Você' : state.currentModel;
    
    messageDiv.innerHTML = 
        '<div class="message-avatar">' + avatar + '</div>' +
        '<div class="message-content">' +
            '<div class="message-header">' +
                '<span class="message-role">' + roleLabel + '</span>' +
                '<span class="message-time">' + new Date().toLocaleTimeString('pt-BR') + '</span>' +
            '</div>' +
            '<div class="message-text"></div>' +
            '<div class="message-meta" style="display:none;"></div>' +
        '</div>';
    
    return messageDiv;
}

function addMessageToChat(role, content, animate) {
    content = content || '';
    animate = animate || false;
    
    const messageEl = createMessageElement(role, content);
    elements.chatMessages.appendChild(messageEl);
    
    const textEl = messageEl.querySelector('.message-text');
    
    if (animate && role === 'assistant') {
        // Efeito typewriter para respostas da IA
        typeWriter(textEl, content);
    } else {
        textEl.innerHTML = escapeHtml(content).replace(/\n/g, '<br>');
    }
    
    // Auto-scroll
    scrollToBottom();
    
    // Salvar no histórico
    state.messages.push({ role: role, content: content, timestamp: Date.now() });
    
    // Limitar histórico
    if (state.messages.length > CONFIG.MAX_HISTORY) {
        state.messages.shift();
    }
    
    return messageEl;
}

// ============================================
// EFEITO TYPEWRITER
// ============================================
let typeWriterTimeout = null;

function typeWriter(element, text, speed) {
    speed = speed || CONFIG.TYPEWRITER_SPEED;
    
    // Cancelar typewriter anterior se existir
    if (typeWriterTimeout) {
        clearTimeout(typeWriterTimeout);
    }
    
    let i = 0;
    element.textContent = '';
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            scrollToBottom();
            typeWriterTimeout = setTimeout(type, speed);
        } else {
            typeWriterTimeout = null;
        }
    }
    
    type();
}

// ============================================
// AUTO-SCROLL
// ============================================
function scrollToBottom() {
    requestAnimationFrame(function() {
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    });
}

// ============================================
// ENVIAR MENSAGEM PARA OLLAMA
// ============================================
async function sendMessage() {
    const message = elements.userInput.value.trim();
    if (!message || state.isGenerating) return;
    
    // Inicializar audio context na interação do usuário
    sound.init();
    sound.playNotification('send');
    
    // Desabilitar input
    state.isGenerating = true;
    elements.sendBtn.disabled = true;
    elements.userInput.disabled = true;
    showLoadingDots();
    updateSystemStatus();
    
    // Adicionar mensagem do usuário
    addMessageToChat('user', message);
    
    // Limpar input
    elements.userInput.value = '';
    elements.userInput.style.height = 'auto';
    
    // Criar placeholder para resposta da IA
    const aiMessageEl = addMessageToChat('assistant', '', true);
    const textEl = aiMessageEl.querySelector('.message-text');
    const metaEl = aiMessageEl.querySelector('.message-meta');
    
    const startTime = performance.now();
    
    try {
        state.abortController = new AbortController();
        
        // Preparar contexto do histórico
        const history = state.messages.slice(-10); // Últimas 10 mensagens para contexto
        const prompt = buildPromptWithHistory(history);
        
        const response = await fetch(CONFIG.OLLAMA_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: state.currentModel,
                prompt: prompt,
                stream: true,
                options: {
                    temperature: 0.7,
                    top_p: 0.9
                }
            }),
            signal: state.abortController.signal
        });
        
        if (!response.ok) {
            throw new Error('Erro HTTP: ' + response.status);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let totalTokens = 0;
        let done = false;
        
        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;
            
            const chunk = decoder.decode(value, { stream: true });
            
            // Ollama envia objetos JSON separados por newline
            const lines = chunk.split('\n').filter(function(line) { return line.trim(); });
            
            for (let j = 0; j < lines.length; j++) {
                try {
                    const parsed = JSON.parse(lines[j]);
                    if (parsed.response) {
                        fullResponse += parsed.response;
                        // Atualizar texto com typewriter-like streaming
                        textEl.textContent = fullResponse;
                        scrollToBottom();
                    }
                    if (parsed.eval_count) {
                        totalTokens = parsed.eval_count;
                    }
                } catch (e) {
                    // Ignorar erros de parse de linhas parciais
                }
            }
        }
        
        const endTime = performance.now();
        const responseTime = endTime - startTime;
        
        // Atualizar estado
        state.totalTokens += totalTokens;
        
        // Adicionar ao histórico de performance
        const perfData = {
            model: state.currentModel,
            time: responseTime,
            tokens: totalTokens
        };
        state.performanceHistory.push(perfData);
        performanceChart.addDataPoint(state.currentModel, responseTime, totalTokens);
        
        // Atualizar metadata
        metaEl.style.display = 'flex';
        metaEl.innerHTML = 
            '<span>⏱️ ' + formatTime(responseTime) + '</span>' +
            '<span>📊 ' + formatTokens(totalTokens) + ' tokens</span>' +
            '<span>🧠 ' + state.currentModel + '</span>';
        
        // Som de notificação
        sound.playNotification('success');
        
        updateSystemStatus();
        
    } catch (error) {
        if (error.name === 'AbortError') {
            // Usuário cancelou
        } else {
            console.error('Erro ao enviar mensagem:', error);
            textEl.textContent = 'Erro: ' + error.message + '. Verifique se o Ollama está rodando em localhost:11434.';
            sound.playNotification('error');
        }
    } finally {
        state.isGenerating = false;
        state.abortController = null;
        elements.sendBtn.disabled = false;
        elements.userInput.disabled = false;
        hideLoadingDots();
        elements.userInput.focus();
        updateSystemStatus();
    }
}

// ============================================
// CONSTRUIR PROMPT COM HISTÓRICO
// ============================================
function buildPromptWithHistory(history) {
    if (history.length <= 1) {
        return history[0] ? history[0].content : '';
    }
    
    let prompt = '';
    for (let i = 0; i < history.length - 1; i++) {
        const msg = history[i];
        if (msg.role === 'user') {
            prompt += 'Usuário: ' + msg.content + '\n';
        } else {
            prompt += 'Assistente: ' + msg.content + '\n';
        }
    }
    
    return prompt;
}

// ============================================
// CANCELAR GERAÇÃO
// ============================================
function cancelGeneration() {
    if (state.abortController) {
        state.abortController.abort();
    }
}

// ============================================
// LIMPAR CHAT
// ============================================
function clearChat() {
    state.messages = [];
    elements.chatMessages.innerHTML = '';
    showWelcomeMessage();
}

function showWelcomeMessage() {
    const welcomeEl = document.createElement('div');
    welcomeEl.className = 'welcome-message';
    welcomeEl.innerHTML = 
        '<div class="welcome-icon">🤖</div>' +
        '<h2>ATENA EVOLUÇÃO</h2>' +
        '<p>Sistema de Inteligência Artificial Holográfico</p>' +
        '<p class="welcome-subtitle">Digite sua mensagem para iniciar a conversa</p>';
    elements.chatMessages.appendChild(welcomeEl);
}

// ============================================
// ATALHOS DE TECLADO
// ============================================
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (state.isGenerating) {
            cancelGeneration();
        } else {
            sendMessage();
        }
    }
}

// Redimensionar input automaticamente
function autoResizeTextarea() {
    const el = elements.userInput;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    elements.sendBtn.addEventListener('click', function() {
        if (state.isGenerating) {
            cancelGeneration();
        } else {
            sendMessage();
        }
    });
    
    elements.userInput.addEventListener('keydown', handleKeyDown);
    elements.userInput.addEventListener('input', autoResizeTextarea);
    
    elements.modelSelect.addEventListener('change', function(e) {
        state.currentModel = e.target.value;
        updateSystemStatus();
    });
    
    elements.clearBtn.addEventListener('click', clearChat);
}

// ============================================
// INICIALIZAÇÃO
// ============================================
async function init() {
    cacheElements();
    
    // Configurar footer
    elements.versionInfo.textContent = 'v2.0.0';
    elements.costInfo.textContent = 'Custo: R$ 0,00 (ZERO) - Processamento Local';
    
    // Mostrar mensagem de boas-vindas
    showWelcomeMessage();
    
    // Inicializar gráfico
    performanceChart = new PerformanceChart('performance-chart');
    
    // Carregar modelos
    await loadModels();
    
    // Configurar eventos
    setupEventListeners();
    
    // Atualizar status inicial
    updateSystemStatus();
    
    // Focar no input
    elements.userInput.focus();
    
    console.log('ATENA EVOLUÇÃO inicializado com sucesso!');
}

// Iniciar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
