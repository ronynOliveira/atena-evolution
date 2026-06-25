# UI Bug Report — Atena Evolução

**Data:** 2026-06-18  
**Analista:** OWL (subagent)  
**URL testada:** http://127.0.0.1:8081  
**Arquivos analisados:**
- `C:\Users\dell-\AppData\Local\hermes\atena_evolution\web\index.html` (1557 linhas)
- `C:\Users\dell-\AppData\Local\hermes\atena_evolution\web\style.css` (1810 linhas)

---

## Resumo Executivo

| Categoria | Bugs Encontrados |
|---|---|
| 1. Bugs Visuais | 5 |
| 2. Bugs Funcionais | 6 |
| 3. Acessibilidade | 7 |
| 4. Responsividade | 4 |
| 5. Erros JS / Console | 5 |
| 6. Performance | 3 |
| 7. Inconsistências de Design | 4 |
| 8. Segurança | 5 |
| **TOTAL** | **39** |

---

## 1. BUGS VISUAIS

### BUG-V01 — Spinner inline com sintaxe inválida no innerHTML

**Arquivo:** `index.html`, linha 1313  
**Problema:** O spinner é inserido via `innerHTML` com uma tag `<div>` malformada:
```js
elements.refreshModelsBtn.innerHTML = '<div=\"spinner\"></div> Carregando...';
```
O atributo está `div=\"spinner\"` em vez de `class=\"spinner\"`. Isso cria um elemento HTML inválido. O navegador tenta corrigir, mas o spinner nunca aparece corretamente.  
**Impacto:** Usuário não recebe feedback visual de carregamento ao atualizar modelos.  
**Correção:**
```js
elements.refreshModelsBtn.innerHTML = '<div class="spinner"></div> Carregando...';
```

---

### BUG-V02 — Tooltip `data-tooltext` (typo) no botão Exportar

**Arquivo:** `index.html`, linha 219  
**Problema:** O botão de exportar usa `data-tooltext` em vez de `data-tooltip`:
```html
<button class="header-btn" id="exportChatBtn" data-tooltext="Exportar Chat">
```
O CSS só reconhece `[data-tooltip]`, então o tooltip nunca aparece.  
**Impacto:** Usuário não sabe o que o botão de exportar faz.  
**Correção:** Trocar `data-tooltext` por `data-tooltip`.

---

### BUG-V03 — z-index do sidebar-overlay (9) menor que o sidebar (10) mas maior que o header (5)

**Arquivo:** `style.css`, linhas 169 (sidebar z-index:10), 607 (header z-index:5), 1705 (overlay z-index:9)  
**Problema:** O overlay tem z-index 9, o sidebar tem z-index 10. Isso está correto. Porém, o header tem z-index 5, o que significa que em telas menores onde o sidebar fica fixed, o header fica atrás do sidebar quando aberto. Além disso, o `.main-content` tem z-index 1, e o sidebar fixed em mobile cobre o header.  
**Impacto:** Em mobile, o sidebar aberto pode sobrepor o header de forma visualmente estranha.  
**Correção:** Garantir que o header tenha z-index >= 10 em mobile, ou que o sidebar só comece abaixo do header.

---

### BUG-V04 — Modal de imagem: padding 0 no modal conflita com modal-header padding

**Arquivo:** `style.css`, linha 1512  
**Problema:** O modal de imagem define `padding: 0` no `.modal`, mas o `.modal-header` interno tem `padding: 16px 20px`. Isso faz com que o header do modal fique sem espaçamento lateral alinhado, criando uma inconsistência visual.  
**Impacto:** Visual desalinhado no modal de preview de imagem.  
**Correção:** Remover `padding: 0` do `.image-preview-modal .modal` ou aplicar padding consistente.

---

### BUG-V05 — Galeria de imagens: `grid-column: 1 / -1` no gallery-empty pode causar overflow

**Arquivo:** `style.css`, linha 1314  
**Problema:** O elemento `.gallery-empty` usa `grid-column: 1 / -1` para ocupar toda a linha da grid. Se a grid tiver apenas 1 coluna em mobile, o texto pode overflowar sem quebra adequada.  
**Impacto:** Texto "Nenhuma imagem gerada ainda" pode ultrapassar o container em telas muito pequenas.  
**Correção:** Adicionar `word-break: break-word` e `padding` adequado ao `.gallery-empty`.

---

## 2. BUGS FUNCIONAIS

### BUG-F01 — Botão de micrófono não funciona em HTTP (requer HTTPS)

**Arquivo:** `index.html`, linhas 1494-1512  
**Problema:** A API `SpeechRecognition` exige contexto seguro (HTTPS ou localhost). A aplicação roda em `http://127.0.0.1:8081`, que é considerado contexto seguro. Porém, se acessada via IP de rede (ex: `http://192.168.x.x:8081`), a API falha silenciosamente. O código até verifica `'webkitSpeechRecognition' in window`, mas não verifica se o contexto é seguro.  
**Impacto:** Botão de microfone pode não funcionar em alguns cenários de rede local.  
**Correção:** Adicionar verificação:
```js
if (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
  showToast('Reconhecimento de voz requer HTTPS', 'warning');
  return;
}
```

---

### BUG-F02 — Regenerar mensagem não atualiza o DOM corretamente

**Arquivo:** `index.html`, linhas 941-959  
**Problema:** A função `regenerateMessage` remove mensagens do DOM iterando sobre `$$('.message')` e comparando com `btn.closest('.message')`. Porém, após a regeneração, o `sendMessage` é chamado novamente, que por sua vez chama `appendMessageBubble`. Se a mensagem de usuário não estiver visível (scroll), a nova resposta pode aparecer em posição errada. Além disso, a função remove todas as mensagens após a mensagem clicada, mas não remove a própria mensagem clicada (a mensagem da Atena), o que pode deixar elementos órfãos.  
**Impacto:** Regenerar pode deixar mensagens duplicadas ou fora de ordem na UI.  
**Correção:** Limpar completamente as mensagens do DOM e re-renderizar a partir de `state.messages` após fatiar.

---

### BUG-F03 — Export de chat não formata timestamps corretamente

**Arquivo:** `index.html`, linhas 1376-1378  
**Problema:** O export usa `new Date(m.timestamp).toLocaleTimeString('pt-BR')`, mas se `m.timestamp` for `undefined` (mensagens antigas sem timestamp), exibe "Invalid Date".  
**Impacto:** Arquivo exportado com "Invalid Date" em mensagens antigas.  
**Correção:** Adicionar fallback:
```js
const time = m.timestamp ? new Date(m.timestamp).toLocaleTimeString('pt-BR') : 'N/A';
```

---

### BUG-F04 — Botão "Anexar arquivo" é apenas placeholder

**Arquivo:** `index.html`, linhas 1515-1517  
**Problema:** O botão de anexar apenas exibe um toast "Funcionalidade em desenvolvimento". Não há input file oculto, não há drag-and-drop, não há integração com nenhuma API.  
**Impacto:** Usuário pode tentar anexar arquivos e ficar confuso.  
**Correção:** Ou remover o botão até que a funcionalidade exista, ou implementar com `<input type="file">` oculto.

---

### BUG-F05 — `AbortSignal.timeout()` pode não ser suportado em navegadores antigos

**Arquivo:** `index.html`, linhas 666, 688, 709  
**Problema:** `AbortSignal.timeout(ms)` é uma API relativamente nova (Chrome 103+, Firefox 100+). Navegadores mais antigos lançarão `TypeError: AbortSignal.timeout is not a function`.  
**Impacto:** Requisições de status podem falhar silenciosamente em navegadores antigos.  
**Correção:** Usar `AbortController` com `setTimeout` como fallback:
```js
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000);
// ... fetch(..., { signal: controller.signal })
clearTimeout(timeoutId);
```

---

### BUG-F06 — `btoa(unescape(encodeURIComponent(svg)))` é deprecated e falha com caracteres especiais

**Arquivo:** `index.html`, linha 1039  
**Problema:** `unescape()` e `encodeURIComponent()` combinados com `btoa()` é um workaround antigo para UTF-8 em base64. `unescape` é deprecated e pode falhar com caracteres Unicode certos (emojis, caracteres acentuados no prompt).  
**Impactos:** Geração de placeholder SVG falha silenciosamente se o prompt contiver emojis ou caracteres especiais.  
**Correção:** Usar `btoa(new TextEncoder().encode(svg))` ou uma função de encoding UTF-8 adequada:
```js
function utf8ToBase64(str) {
  return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (_, p1) =>
    String.fromCharCode(parseInt(p1, 16))
  ));
}
```

---

## 3. PROBLEMAS DE ACESSIBILIDADE

### BUG-A01 — Botões de ação sem `aria-label`

**Arquivo:** `index.html`, linhas 216-224 (header), 297-303 (chat input actions)  
**Problema:** Botões como "Nova Conversa", "Exportar Chat", "Alternar Tema", "Anexar arquivo", "Entrada por voz" usam apenas `data-tooltip` para identificação. Leitores de tela leem apenas o conteúdo do `<i class="fas fa-...">`, que não tem texto alternativo.  
**Impacto:** Usuários com deficiência visual não conseguem identificar a função dos botões.  
**Correção:** Adicionar `aria-label` em todos os botões de ação:
```html
<button class="header-btn" id="newChatBtn" aria-label="Nova Conversa">
```

---

### BUG-A02 — Sidebar navigation sem `role="navigation"` e sem `aria-current`

**Arquivo:** `index.html`, linha 53  
**Problema:** A `<nav class="sidebar-nav">` não tem `role="navigation"` explícito (embora `<nav>` tenha semântica implícita, é boa prática). Os botões de navegação não indicam qual está ativo via `aria-current="page"`.  
**Impacto:** Leitores de tela não anunciam qual painel está ativo.  
**Correção:** Adicionar `aria-current="page"` ao botão ativo e `role="tablist"` com `role="tab"` nos botões.

---

### BUG-A03 — Chat input textarea sem `aria-label`

**Arquivo:** `index.html`, linhas 291-295  
**Problema:** O `<textarea id="chatInput">` não tem `aria-label` ou `aria-labelledby`. Leitores de tela podem anunciá-lo apenas como "editar texto".  
**Impacto:** Usuários de leitor de tela não sabem o propósito do campo.  
**Correção:** Adicionar `aria-label="Digite sua mensagem"`.

---

### BUG-A04 — Quick prompts sem semântica de botão acessível

**Arquivo:** `index.html`, linhas 259-282  
**Problema:** Os botões de quick prompts não têm `aria-label` descritivo. Leitores de tela leem o texto do `<span>`, mas não há indicação de que são ações rápidas.  
**Impacto:** Acessibilidade parcial — o texto é legível, mas o contexto não é claro.  
**Correção:** Adicionar `aria-label` com descrição da ação.

---

### BUG-A05 — Modal de preview de imagem não tem `role="dialog"` e não gerencia foco

**Arquivo:** `index.html`, linhas 488-508  
**Problema:** O modal não tem `role="dialog"`, `aria-modal="true"`, nem `aria-labelledby`. Quando aberto, o foco não é transferido para o modal, e ao fechar, o foco não retorna ao botão que o abriu.  
**Impacto:** Leitores de tela não anunciam o modal; navegação por teclado fica presa.  
**Correção:** Adicionar atributos ARIA e gerenciamento de foco com `focus trap`.

---

### BUG-A06 — Contraste insuficiente em textos muted

**Arquivo:** `style.css`, linha 27  
**Problema:** `--text-muted: #64748b` sobre `--bg-primary: #0a0a1a` tem contraste de aproximadamente 4.2:1, que passa AA para texto grande mas falha para texto normal (< 4.5:1). O `--text-placeholder: #475569` sobre `--bg-input: #0d0d25` tem contraste de ~3.5:1, falhando AA.  
**Impacto:** Textos secundários e placeholders são difíceis de ler.  
**Correção:** Aumentar `--text-muted` para pelo menos `#94a3b8` (já usado como `--text-secondary`) e `--text-placeholder` para `#64748b`.

---

### BUG-A07 — Indicador de status (online/offline) não tem texto alternativo para leitores de tela

**Arquivo:** `index.html`, linhas 76-85  
**Problema:** Os indicadores de status usam apenas cores (verde/vermelho) e um `<span>` com texto. Não há `aria-live` para anunciar mudanças de status, e o `.status-dot` não tem `aria-label`.  
**Impacto:** Usuários de leitor de tela não são notificados quando o status da conexão muda.  
**Correção:** Adicionar `aria-live="polite"` ao container de status e `aria-label` aos dots.

---

## 4. PROBLEMAS DE RESPONSIVIDADE

### BUG-R01 — Sidebar em mobile não fecha ao clicar em um item de navegação

**Arquivo:** `index.html`, linhas 1244-1252  
**Problema:** Ao clicar em um item da navegação da sidebar (Status, Config, Histórico), o painel muda mas a sidebar permanece aberta em mobile. O overlay também não é desativado.  
**Impacto:** Em mobile, o conteúdo fica escondido atrás da sidebar aberta após trocar de painel.  
**Correção:** Fechar a sidebar ao clicar em um item de navegação em mobile:
```js
btn.addEventListener('click', () => {
  // ... existing code ...
  if (window.innerWidth <= 1024) {
    elements.sidebar.classList.remove('open');
    elements.sidebarOverlay.classList.remove('active');
  }
});
```

---

### BUG-R02 — Tabs escondem texto em mobile (< 768px), mas não há indicação visual

**Arquivo:** `style.css`, linhas 1625-1631  
**Problema:** Em telas <= 768px, `.tab-btn span { display: none; }` esconde o texto das tabs, mostrando apenas ícones. Porém, não há tooltip ou aria-label para indicar qual tab é qual.  
**Impacto:** Usuários em mobile não sabem qual tab está ativa.  
**Correção:** Adicionar `title` ou `aria-label` aos botões de tab com o nome da tab.

---

### BUG-R03 — Quick prompts em 1 coluna em mobile podem ser muito longos

**Arquivo:** `style.css`, linha 1642  
**Problema:** Em mobile, quick prompts mudam para `grid-template-columns: 1fr`. Os botões têm `padding: 14px 16px` e textos longos como "Explique a relatividade", que podem overflowar ou ficar com altura excessiva.  
**Impacto:** Botões de prompt ficam com layout quebrado em mobile.  
**Correção:** Adicionar `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` ao texto do botão.

---

### BUG-R04 — Header não acomoda o título + botões em telas muito pequenas (< 360px)

**Arquivo:** `style.css`, linhas 1676-1697  
**Problema:** Em telas de 320-360px, o header com título + 3 botões pode overflowar. O título já tem `font-size: 0.95rem` mas os 3 botões de 36px cada (108px) + gaps + padding do header podem não caber.  
**Impacto:** Elementos do header podem overflowar em dispositivos muito pequenos.  
**Correção:** Reduzir tamanho dos botões ou do título em telas < 360px.

---

## 5. ERROS NO CONSOLE JAVASCRIPT

### BUG-J01 — `$$('.tab-btn')[0]` pode ser undefined se não houver tabs

**Arquivo:** `index.html`, linha 1215  
**Problema:** Ao carregar uma conversão, o código assume que existe pelo menos um `.tab-btn`:
```js
$$('.tab-btn')[0].classList.add('active');
```
Se o DOM não tiver `.tab-btn` (cenário improvável mas possível com DOM dinâmico), isso lança `TypeError: Cannot read properties of undefined`.  
**Impacto:** Erro no console que pode quebrar o carregamento de conversas.  
**Correção:** Adicionar verificação:
```js
const firstTab = $$('.tab-btn')[0];
if (firstTab) firstTab.classList.add('active');
```

---

### BUG-J02 — `navigator.clipboard.writeText` falha em contexto não seguro

**Arquivo:** `index.html`, linha 936  
**Problema:** `navigator.clipboard.writeText()` requer HTTPS ou localhost. Se a aplicação for acessada via IP de rede em HTTP, lança `NotAllowedError`. O `.then()` não tem `.catch()`.  
**Impacto:** Erro no console ao tentar copiar mensagem.  
**Correção:** Adicionar tratamento de erro:
```js
navigator.clipboard.writeText(bubble.textContent).then(() => {
  showToast('Mensagem copiada!', 'success');
}).catch(() => {
  showToast('Não foi possível copiar', 'error');
});
```

---

### BUG-J03 — `URL.createObjectURL` nunca é revogado no export

**Arquivo:** `index.html`, linha 1381  
**Problema:** O blob URL criado com `URL.createObjectURL(blob)` nunca é revogado com `URL.revokeObjectURL()`. Cada export cria um novo blob na memória que nunca é liberado.  
**Impacto:** Vazamento de memória gradual com exports repetidos.  
**Correção:** Revogar após o clique:
```js
a.click();
URL.revokeObjectURL(a.href);
```

---

### BUG-J04 — `localStorage.setItem` pode lançar exceção em modo privado

**Arquivo:** `index.html`, múltiplas linhas  
**Problema:** Em alguns navegadores em modo privado/anônimo, `localStorage.setItem` pode lançar `QuotaExceededError` ou `SecurityError`. Não há try/catch em nenhuma das chamadas.  
**Impacto:** Erro no console e perda de funcionalidade de persistência.  
**Correção:** Envolver todas as chamadas `localStorage.setItem` em try/catch.

---

### BUG-J05 — `JSON.parse` sem try/catch no carregamento de conversas

**Arquivo:** `index.html`, linha 537  
**Problema:** Se o dado em `localStorage` estiver corrompido (edição manual, dados de versão antiga), `JSON.parse` lança `SyntaxError` que não é capturado, quebrando toda a inicialização.  
**Impacto:** A aplicação inteira quebra se houver dados corrompidos no localStorage.  
**Correção:**
```js
try {
  conversations: JSON.parse(localStorage.getItem('atena_conversations') || '[]'),
} catch (e) {
  conversations: [];
}
```

---

## 6. PROBLEMAS DE PERFORMANCE

### BUG-P01 — `scrollToBottom()` chamado a cada chunk do stream

**Arquivo:** `index.html`, linha 828  
**Problema:** Durante o streaming de resposta, `scrollToBottom()` é chamado a cada chunk de texto recebido. Isso força reflow do DOM a cada poucos milissegundos.  
**Impacto:** Animacoes de scroll "tremidas" e uso excessivo de CPU durante streaming longo.  
**Correção:** Usar `requestAnimationFrame` para debounce:
```js
let scrollRAF = null;
function scrollToBottom() {
  if (scrollRAF) cancelAnimationFrame(scrollRAF);
  scrollRAF = requestAnimationFrame(() => {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  });
}
```

---

### BUG-P02 — `setInterval` de 30s para status check sem cleanup

**Arquivo:** `index.html`, linhas 1542-1545  
**Problema:** O `setInterval` que verifica status a cada 30s nunca é limpo. Se a página ficar aberta por muito tempo, acumula chamadas. Além disso, não há backoff — se o servidor estiver offline, continua tentando a cada 30s indefinidamente.  
**Impacto:** Requisições desnecessárias em segundo plano, consumo de bateria em mobile.  
**Correção:** Implementar backoff exponencial e armazenar o ID do intervalo para cleanup.

---

### BUG-P03 — `renderImageGallery()` recria todos os cards a cada atualização

**Arquivo:** `index.html`, linhas 1065-1101  
**Problema:** A função `renderImageGallery()` remove e recria TODOS os cards de imagem a cada atualização, mesmo que apenas uma imagem tenha sido adicionada. Com 50 imagens no limite, isso causa reflows massivos.  
**Impacto:** Travamento da UI ao gerar imagens quando a galeria já tem muitas imagens.  
**Correção:** Usar diffing ou apenas adicionar o novo card no início sem recriar tudo.

---

## 7. INCONSISTÊNCIAS DE DESIGN

### BUG-D01 — Duplicação de campos de configuração entre sidebar e tab "Configurações"

**Arquivo:** `index.html`, linhas 123-176 (sidebar) vs 377-481 (tab config)  
**Problema:** Os mesmos campos de configuração (Ollama URL, API URL, chaves de API, temperatura, max tokens) existem em dois lugares: na sidebar (painel "Config") e na tab "Configurações". A sincronização entre eles é manual e frágil (função `syncConfigTab()`).  
**Impacto:** Usuário pode configurar em um lugar e não perceber que o outro não foi atualizado.  
**Correção:** Usar uma única fonte de verdade e eliminar a duplicação, ou sincronizar automaticamente com observers.

---

### BUG-D02 — Fonte `--font-mono` (JetBrains Mono) não é carregada

**Arquivo:** `style.css`, linha 51  
**Problema:** A variável `--font-mono` referencia `'JetBrains Mono', 'Fira Code', monospace`, mas nenhuma dessas fontes é carregada no HTML. O Google Fonts só carrega `Inter`.  
**Impacto:** Código exibido em fonte monospace genérica (system), não na fonte premium pretendida.  
**Correção:** Adicionar o link do Google Fonts para JetBrains Mono ou Fira Code.

---

### BUG-D03 — Estilos inline excessivos no HTML

**Arquivo:** `index.html`, múltiplas linhas (ex: 97, 124, 167, 180, 325, 355, 460, etc.)  
**Problema:** Há dezenas de atributos `style=""` inline no HTML, como `style="margin-top: 8px;"`, `style="flex: 1;"`, `style="border: none; padding: 0; background: transparent;"`. Isso dificulta a manutenção e sobrescreve estilos do CSS sem necessidade.  
**Impacto:** Dificuldade de manutenção, inconsistência visual.  
**Correção:** Mover todos os estilos inline para classes CSS.

---

### BUG-D04 — Cores inconsistentes entre badges de versão e badges de conexão

**Arquivo:** `index.html`, linhas 461-466  
**Problema:** O badge de versão usa a classe `.connection-badge connected` (verde), enquanto o badge "Hermes Agent" usa estilo inline com cor azul (`rgba(59, 130, 246, 0.15)`). Deveria usar uma classe consistente.  
**Impacto:** Inconsistência visual nos badges da seção "Sobre".  
**Correção:** Criar uma classe `.badge-blue` ou reutilizar `.connection-badge` com modifier.

---

## 8. SEGURANÇA

### BUG-S01 — XSS via `innerHTML` com conteúdo do usuário em `formatMessage()`

**Arquivo:** `index.html`, linha 872  
**Problema:** A função `formatMessage()` aplica escaping HTML básico (`&`, `<`, `>`), mas a string resultada é inserida via `innerHTML` no `appendMessageBubble`. Se o escaping falhar em algum edge case (ex: atributos HTML injetados), há risco de XSS. Além disso, o conteúdo do usuário é inserido via `innerHTML` em múltiplos pontos (toast, mensagens, galeria).  
**Impacto:** Potencial XSS se conteúdo malicioso contornar o escaping.  
**Correção:** Usar `textContent` em vez de `innerHTML` para conteúdo de mensagens, ou usar uma biblioteca de sanitização como DOMPurify.

---

### BUG-S02 — Dados sensíveis (API keys) armazenados em localStorage sem criptografia

**Arquivo:** `index.html`, linhas 1417-1419  
**Problema:** Chaves de API (Gemini, OpenAI, Anthropic) são armazenadas em texto plano no `localStorage`. Qualquer extensão do navegador, script XSS, ou acesso físico ao computador pode ler essas chaves.  
**Impacto:** Exposição de credenciais de API do usuário.  
**Correção:** Considerar usar sessionStorage (expira ao fechar), ou ao menos documentar o risco. Para uma solução mais robusta, usar um backend para armazenar chaves.

---

### BUG-S03 — SVG gerado com `btoa()` pode conter conteúdo injetável

**Arquivo:** `index.html`, linhas 1022-1039  
**Problema:** O SVG placeholder é gerado com interpolação de string direta do prompt do usuário:
```js
<text ...>${prompt.substring(0, 40)}${prompt.length > 40 ? '...' : ''}</text>
```
Se o prompt conter `</text><script>alert('XSS')</script><text>`, o SVG será malformado e potencialmente executará scripts quando renderizado como data URI.  
**Impacto:** XSS via SVG inject.  
**Correção:** Escapar o prompt antes de inserir no SVG:
```js
const safePrompt = prompt.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
```

---

### BUG-S04 — Sem Content Security Policy (CSP)

**Arquivo:** `index.html`, sem meta tag CSP  
**Problema:** A página não define nenhuma Content Security Policy. Isso permite execução de scripts inline (que já existem), mas também não protege contra injeção de scripts externos.  
**Impacto:** Vulnerável a ataques XSS que injetam scripts externos.  
**Correção:** Adicionar meta tag CSP:
```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: blob:;">
```

---

### BUG-S05 — `fetch` sem validação de origem nas requisições de API

**Arquivo:** `index.html`, linhas 769, 781, 991  
**Problema:** As requisições fetch são feitas para URLs configuráveis (`state.ollamaUrl`, `state.apiUrl`) sem validação. Se um atacante modificar o localStorage (via XSS), pode redirecionar requisições para um servidor malicioso.  
**Impacto:** Exfiltração de dados/credenciais se XSS for explorado.  
**Correção:** Validar que as URLs são localhost ou HTTPS, ou implementar allowlist.

---

## Priorização Sugerida

| Prioridade | Bugs |
|---|---|
| 🔴 **Crítico** | BUG-S01 (XSS innerHTML), BUG-S03 (XSS SVG), BUG-J05 (JSON.parse), BUG-V01 (spinner quebrado) |
| 🟠 **Alto** | BUG-F02 (regenerar), BUG-A01 (aria-labels), BUG-A05 (modal a11y), BUG-S02 (API keys), BUG-S04 (CSP) |
| 🟡 **Médio** | BUG-R01 (sidebar mobile), BUG-P01 (scroll RAF), BUG-P03 (gallery render), BUG-D01 (duplicação), BUG-J03 (memory leak) |
| 🟢 **Baixo** | BUG-V02 (typo tooltip), BUG-A06 (contraste), BUG-D02 (fonte), BUG-D03 (inline styles), BUG-F04 (placeholder) |

---

*Relatório gerado automaticamente por análise estática dos arquivos HTML e CSS.*
