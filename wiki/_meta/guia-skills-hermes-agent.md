# Guia de Skills do Hermes Agent

## SOFTWARE-DEVELOPMENT

### browser-cdp
1. **O que faz**: Conecta a um Chrome existente via CDP (Chrome DevTools Protocol) para controle programático do navegador.
2. **Quando usar**: Quando voce ja tem uma instancia do Chrome aberta e quer controla-la sem abrir uma nova janela; ideal para depuracao ou automacao em sessao existente.
3. **Quando nao usar**: Quando precisa de isolamento completo, auto-healing de seletores, ou nao tem uma instancia Chrome ja rodando com CDP habilitado.

### browser-harness
1. **O que faz**: Automacao de navegador com auto-healing de seletores e resiliencia a mudancas na pagina.
2. **Quando usar**: Automacao web em geral onde os seletores podem mudar entre versoes; recomendada para scripts de longa duracao ou paginas dinamicas.
3. **Quando nao usar**: Tasks rapidas e pontuais onde o CDP direto e suficiente, ou quando voce precisa de interacao com uma sessao Chrome ja existente.

### debugging-hermes-tui-commands
1. **O que faz**: Depuracao do Hermes Agent TUI (Terminal User Interface) com comandos especificos de troubleshooting.
2. **Quando usar**: Quando o Hermes Agent esta apresentando problemas de interface, rendering ou comportamento no terminal.
3. **Quando nao usar**: Debugging de codigo de aplicacao comum (use systematic-debugging ou node-inspect-debugger).

### hermes-agent-skill-authoring
1. **O que faz**: Cria ou edita arquivos SKILL.md para definir novas skills do Hermes Agent.
2. **Quando usar**: Quando voce precisa criar uma nova skill para o Hermes Agent ou modificar uma existente.
3. **Quando nao usar**: Tasks que nao envolvem a criacao ou manutencao de skills do Hermes.

### node-inspect-debugger
1. **O que faz**: Depuracao de aplicacoes Node.js via protocolo --inspect com breakpoints, step-through e variaveis.
2. **Quando usar**: Debugging detalhado de codigo Node.js onde console.log e insuficiente.
3. **Quando nao usar**: Debugging de TUI (use debugging-hermes-tui-commands) ou debugging generico sem Node.js.

### plan
1. **O que faz**: Cria um plano detalhado de acao sem executar nenhum comando ou modificar arquivos.
2. **Quando usar**: Antes de comecar tasks complexas para organizar etapas, validar abordagem e evitar retrabalho.
3. **Quando nao usar**: Tasks simples e diretas onde o plano e obvio; quando o usuario quer execucao imediata.

### reflexion-engine
1. **O que faz**: Gerencia memoria compartilhada entre sessoes e faz routing inteligente de agentes baseado em contexto.
2. **Quando usar**: Tasks que exigem continuidade entre sessoes, memoria de longo prazo, ou coordenacao entre multiplos agentes.
3. **Quando nao usar**: Tasks isoladas e independentes sem necessidade de contexto historico.

### requesting-code-review
1. **O que faz**: Solicita review de codigo antes do commit, analisando qualidade, seguranca e estilo.
2. **Quando usar**: Pre-commit para garantir que o codigo segue os padroes do projeto antes de ser versionado.
3. **Quando nao usar**: Quando o codigo e experimental/throwaway (use spike) ou quando o usuario explicitamente dispensa review.

### spike
1. **O que faz**: Executa um experimento rapido e descartavel para validar uma hipotese tecnica.
2. **Quando usar**: Para explorar uma tecnologia, biblioteca ou abordagem sem compromisso de codigo em producao.
3. **Quando nao usar**: Quando o resultado precisa ser mantido, versionado ou seguir padroes de qualidade.

### subagent-driven-development
1. **O que faz**: Delega tasks complexas para subagentes via `delegate_task`, permitindo execucao paralela e especializada.
2. **Quando usar**: Tasks grandes que podem ser decompostas em subtasks independentes; paralelizacao de trabalho.
3. **Quando nao usar**: Tasks simples ou sequenciais onde o overhead de delegacao nao se justifica.

### systematic-debugging
1. **O que faz**: Processo estruturado de 4 fases (identificar, isolar, corrigir, verificar) para debugging de software.
2. **Quando usar**: Bugs complexos onde a causa raiz nao e obvia e requer abordagem metodica.
3. **Quando nao usar**: Bugs triviais (erro de sintaxe, typo) onde a correcao e imediata.

### test-driven-development
1. **O que faz**: Ciclo RED-GREEN-REFACTOR: escreve teste que falha, faz passar, refatora.
2. **Quando usar**: Quando o usuario pede TDD explicitamente ou quando o problema tem especificacoes claras e testaveis.
3. **Quando nao usar**: Codigo exploratorio, prototipacao rapida, ou quando nao ha requisitos claros para testar.

### writing-plans
1. **O que faz**: Cria planos detalhados de implementacao com etapas, estimativas e dependencias.
2. **Quando usar**: Planejamento de features, epics, ou sprints onde a execucao sera feita posteriormente.
3. **Quando nao usar**: Tasks simples que cabem em uma unica acao; quando o plano e o proprio plano (use plan).

---

## GITHUB

### codebase-inspection
1. **O que faz**: Analisa um repositorio retornando linhas de codigo (LOC), linguagens usadas e estrutura geral.
2. **Quando usar**: Ao clonar ou acessar um repositorio novo para entender sua composicao e escala.
3. **Quando nao usar**: Quando voce ja conhece o repositorio ou precisa de analise mais profunda (use subagent).

### github-auth
1. **O que faz**: Configura autenticacao com GitHub (tokens, SSH, OAuth) para permitir operacoes na API.
2. **Quando usar**: Antes de qualquer operacao que exija autenticacao GitHub (clonar privado, criar PR, etc.).
3. **Quando nao usar**: Repositorios publicos sem necessidade de autenticacao; quando o auth ja esta configurado.

### github-code-review
1. **O que faz**: Revisa Pull Requests no GitHub analisando diffs, apontando problemas e sugerindo melhorias.
2. **Quando usar**: Para revisar PRs abertos como parte do fluxo de review de codigo.
3. **Quando nao usar**: Revisao local pre-commit (use requesting-code-review) ou quando o PR ja foi revisado.

### github-issues
1. **O que faz**: Cria, tria e gerencia issues no GitHub (labels, assignees, milestones).
2. **Quando usar**: Gerenciamento de backlog, reporte de bugs, ou organizacao de tarefas no GitHub Issues.
3. **Quando nao usar**: Tasks que nao precisam ser registradas como issues; gerenciamento em outra ferramenta (Linear, Jira).

### github-pr-workflow
1. **O que faz**: Ciclo completo de PR: criar, revisar, aprovar, mergear, fechar.
2. **Quando usar**: Fluxo padrao de contribuicao em repositorios GitHub com revisao de codigo.
3. **Quando nao usar**: Projetos sem processo de PR; commits diretos ou fluxo Git diferente.

### github-repo-management
1. **O que faz**: Clona, fork, cria e configura repositorios no GitHub.
2. **Quando usar**: Setup inicial de projetos, criacao de forks para contribuicao, ou gerenciamento de repos.
3. **Quando nao usar**: Operacoes dentro de um repo ja clonado (use outras skills GitHub).

---

## PRODUCTIVITY

### accessibility-toolkit
1. **O que faz**: Ferramentas de acessibilidade para usuarios com distonia, incluindo recursos de entrada adaptativa.
2. **Quando usar**: Quando o usuario tem dificuldades motoras e precisa de metodos alternativos de interacao.
3. **Quando nao usar**: Usuarios sem necessidades especiais de acessibilidade.

### airtable
1. **O que faz**: Operacoes CRUD em bases Airtable via API, incluindo criacao, leitura, atualizacao e delecao de registros.
2. **Quando usar**: Automacao de bases Airtable, sincronizacao de dados, ou integracao com Airtable como banco.
3. **Quando nao usar**: Quando o Airtable nao e a fonte de dados; para bancos relacionais ou outras planilhas.

### google-workspace
1. **O que faz**: Acesso e manipulacao de Gmail, Google Calendar e Google Drive.
2. **Quando usar**: Automacao de emails, criacao/gerenciamento de eventos, ou manipulacao de arquivos no Drive.
3. **Quando nao usar**: Tasks que nao envolvem o ecossistema Google; para email em geral (use himalaya).

### linear
1. **O que faz**: Gerenciamento de issues, projetos e sprints no Linear.
2. **Quando usar**: Tasks de gerenciamento de projeto dentro do Linear (criar issues, atualizar status, planejar sprints).
3. **Quando nao usar**: Projetos gerenciados em GitHub Issues, Jira, ou outra ferramenta.

### maps
1. **O que faz**: Geocodificacao, calculo de rotas e informacoes geograficas.
2. **Quando usar**: Quando precisa converter enderecos em coordenadas, calcular distancias ou obter direcoes.
3. **Quando nao usar**: Tasks sem componente geografico ou de localizacao.

### nano-pdf
1. **O que faz**: Edicao de PDFs: merge, split, extracao de paginas, anotacoes e conversao.
2. **Quando usar**: Manipulacao de documentos PDF (combinar, separar, extrair paginas).
3. **Quando nao usar**: Extracao de texto de PDFs (use ocr-and-documents); criacao de documentos (use PowerPoint ou Google Workspace).

### notion
1. **O que faz**: Operacoes CRUD em pages e databases do Notion via API.
2. **Quando usar**: Automacao de Notion, criacao/atualizacao de paginas, ou consulta a databases.
3. **Quando nao usar**: Tasks que nao envolvem o Notion; anotacoes pessoais rapidas (use Obsidian).

### ocr-and-documents
1. **O que faz**: Extracao de texto de PDFs e imagens via OCR (Optical Character Recognition).
2. **Quando usar**: Digitalizacao de documentos, extracao de texto de imagens ou PDFs escaneados.
3. **Quando nao usar**: PDFs ja com texto selecionavel (use leitura direta); edicao de PDFs (use nano-pdf).

### powerpoint
1. **O que faz**: Criacao e edicao de apresentacoes PowerPoint (.pptx) com slides, graficos e animacoes.
2. **Quando usar**: Quando precisa gerar ou modificar apresentacoes PowerPoint programaticamente.
3. **Quando nao usar**: Apresentacoes simples que podem ser feitas em Markdown ou Google Slides.

### teams-meeting-pipeline
1. **O que faz**: Pipeline completo para resumir reunioes do Teams: transcricao, extracao de acoes e sumarizacao.
2. **Quando usar**: Apos reunioes no Teams para gerar atas, acoes e sumarios automaticamente.
3. **Quando nao usar**: Reunioes em outras plataformas (Zoom, Google Meet); quando nao ha gravacao/transcricao disponivel.

### voice-assistant
1. **O que faz**: Pipeline completo de voz: speech-to-text, processamento, e text-to-speech.
2. **Quando usar**: Interfaces conversacionais por voz, automacao com entrada/saida de audio.
3. **Quando nao usar**: Tasks puramente textuais sem componente de audio.

---

## AUTONOMOUS-AI-AGENTS

### claude-code
1. **O que faz**: Delega tasks para o Claude Code, um agente autonomo de terminal da Anthropic.
2. **Quando usar**: Quando voce quer que outro agente AI execute uma task de forma independente, especialmente codigo.
3. **Quando nao usar**: Tasks que exigem skills especificas do Hermes Agent nao disponiveis no Claude Code.

### codex
1. **O que faz**: Delega tasks para o Codex, agente autonomo da OpenAI para desenvolvimento de software.
2. **Quando usar**: Quando quer delegar desenvolvimento para o agente Codex da OpenAI.
3. **Quando nao usar**: Quando a task requer ferramentas ou contexto que apenas o Hermes Agent possui.

### hermes-agent
1. **O que faz**: Configura e gerencia o proprio Hermes Agent (skills, config, memoria).
2. **Quando usar**: Manutencao, configuracao ou atualizacao do Hermes Agent.
3. **Quando nao usar**: Tasks de desenvolvimento que nao envolvem configuracao do Hermes.

### opencode
1. **O que faz**: Delega tasks para o Opencode, assistente de engenharia de software via terminal.
2. **Quando usar**: Quando quer delegar tasks de codigo para o Opencode como agente externo.
3. **Quando nao usar**: Tasks que exigem o ecossistema completo de skills do Hermes Agent.

---

## MCP

### composio-mcp
1. **O que faz**: Acesso a 500+ ferramentas de terceiros via protocolo MCP (Model Context Protocol) atraves do Composio.
2. **Quando usar**: Quando precisa de integracoes com servicos externos variados sem configuracao individual.
3. **Quando nao usar**: Quando uma skill nativa do Hermes ja cobre a necessidade (prefira a nativa).

### native-mcp
1. **O que faz**: Conecta a servidores MCP (Model Context Protocol) diretamente para expor ferramentas externas.
2. **Quando usar**: Integracao com servidores MCP customizados ou de terceiros que exponham ferramentas via MCP.
3. **Quando nao usar**: Quando a ferramenta desejada ja esta disponivel como skill nativa do Hermes.

---

## MEDIA

### gif-search
1. **O que faz**: Busca e retorna GIFs animados de servicos como Giphy ou Tenor.
2. **Quando usar**: Para encontrar GIFs para comunicacao, documentacao ou apresentacoes.
3. **Quando nao usar**: Tasks serias que nao se beneficiam de midia animada.

### heartmula
1. **O que faz**: Gera musica proceduralmente usando algoritmos e modelos de composicao.
2. **Quando usar**: Quando precisa de musica gerada para projetos, background ou experimentos sonoros.
3. **Quando nao usar**: Producao musical profissional que requer controle fino (use DAWs especializados).

### songsee
1. **O que faz**: Gera espectrogramas e visualizacoes de audio para analise musical.
2. **Quando usar**: Analise visual de audio, educacao musical, ou debugging de sinais de audio.
3. **Quando nao usar**: Quando precisa apenas ouvir ou transcrever audio.

### spotify
1. **O que faz**: Controle do Spotify: play, pause, skip, playlists e recomendacoes.
2. **Quando usar**: Automacao de reproducao musical, criacao de playlists, ou controle por voz.
3. **Quando nao usar**: Analise de audio (use songsee); geracao de musica (use heartmula).

### youtube-content
1. **O que faz**: Transcricao, summarizacao e extracao de informacao de videos do YouTube.
2. **Quando usar**: Para obter conteudo textual de videos, resumir palestras, ou extrair citacoes.
3. **Quando nao usar**: Upload ou gerenciamento de canal do YouTube.

---

## MLOPS

### dspy
1. **O que faz**: Programas declarativos para Language Models (LMs) com otimizacao automatica de prompts.
2. **Quando usar**: Desenvolvimento de pipelines com LMs onde voce quer otimizar prompts automaticamente.
3. **Quando nao usar**: Chamadas simples e diretas a LLMs sem necessidade de otimizacao de prompt.

### huggingface-hub
1. **O que faz**: Acesso a modelos, datasets e espacos do Hugging Face Hub para download e upload.
2. **Quando usar**: Quando precisa baixar modelos/ datasets ou publicar no Hugging Face.
3. **Quando nao usar**: Inferencia local de modelos GGUF (use llama-cpp); experiment tracking (use weights-and-biases).

### llama-cpp
1. **O que faz**: Inferencia local de modelos GGUF otimizados para CPU/GPU via llama.cpp.
2. **Quando usar**: Execucao local de LLMs em formato GGUF para inferencia offline ou sem custo de API.
3. **Quando nao usar**: Quando prefere API cloud (OpenAI, Anthropic) ou modelos em outros formatos.

### segment-anything-model
1. **O que faz**: Segmentacao de objetos em imagens usando o modelo SAM (Segment Anything Model) da Meta.
2. **Quando usar**: Segmentacao de imagem, remocao de fundo, ou identificacao de objetos em fotos.
3. **Quando nao usar**: Tasks que nao envolvem processamento de imagem ou visao computacional.

### weights-and-biases
1. **O que faz**: Experiment tracking, logging de metricas e visualizacao de treinos no Weights & Biases.
2. **Quando usar**: Durante treinamento de modelos ML para logging de metricas, comparacao de experimentos e colaboracao.
3. **Quando nao usar**: Projetos sem componente de ML; experimentos que nao precisam de tracking.

---

## OUTROS

### obsidian
1. **O que faz**: Gerenciamento de notes no Obsidian, incluindo criacao, busca e organizacao de vaults.
2. **Quando usar**: Anotacoes pessoais, documentacao rapida, ou consulta a vaults Obsidian.
3. **Quando nao usar**: Documentacao compartilhada em equipe (use Notion); wiki persistente (use atena-wiki).

### openhue
1. **O que faz**: Controle de luzes Philips Hue: ligar/desligar, cor, intensidade e cenas.
2. **Quando usar**: Automacao residencial com Philips Hue, integracao com IFTTT ou controle por voz.
3. **Quando nao usar**: Quando nao ha dispositivos Philips Hue no ambiente.

### himalaya
1. **O que faz**: Gerenciamento de email via CLI com suporte a IMAP/SMTP.
2. **Quando usar**: Automacao de email, leitura/ envio de mensagens no terminal.
3. **Quando nao usar**: Email no ecossistema Google (use google-workspace); quando prefere interface grafica.

### pokemon-player
1. **O que faz**: Emulacao e controle de jogos Pokemon, incluindo save states e automacao.
2. **Quando usar**: Jogar ou automatizar acoes em jogos Pokemon via emulador.
3. **Quando nao usar**: Tasks nao relacionadas a jogos Pokemon ou emulacao.

### godmode
1. **O que faz**: **NAO USAR** - Jailbreak que tenta remover restricoes de seguranca do modelo.
2. **Quando usar**: **NUNCA**. Esta skill viola politicas de uso responsavel de IA.
3. **Quando nao usar**: **SEMPRE**. Ignorar completamente.

### prompt-injection-defense
1. **O que faz**: Detecta e previne ataques de injecao de prompt em entradas de usuario.
2. **Quando usar**: Sempre que o sistema processar entrada de usuario nao confiavel que pode conter tentativas de manipulacao.
3. **Quando nao usar**: Em ambientes controlados onde toda entrada e confiavel (raro).

### jupyter-live-kernel
1. **O que faz**: Execucao interativa de codigo Python em kernel Jupyter vivo, mantendo estado entre celulas.
2. **Quando usar**: Analise exploratoria de dados, prototipacao Python com feedback imediato, visualizacao interativa.
3. **Quando nao usar**: Codigo de producao, scripts definitivos, ou quando o estado entre execucoes nao e necessario.

### kimi-webbridge
1. **O que faz**: Controla um navegador real para interagir com qualquer website usando sessoes de login reais.
2. **Quando usar**: Automacao web que requer login, interacao com sites complexos, scraping apos autenticacao.
3. **Quando nao usar**: Automacao simples sem necessidade de navegador real; quando browser-harness e suficiente.

### dogfood
1. **O que faz**: Testes de QA (Quality Assurance) em aplicacoes web simulando interacoes de usuario.
2. **Quando usar**: Testing de aplicacoes web antes do deploy, verificacao de fluxos de usuario.
3. **Quando nao usar**: Testes unitarios ou de integracao (use frameworks de teste tradicionais).

### yuanbao
1. **O que faz**: Gerenciamento de grupos de chat e mensagens na plataforma Yuanbao (Tencent).
2. **Quando usar**: Automacao de grupos de chat Tencent, envio de mensagens em lote, moderacao.
3. **Quando nao usar**: Mensageria em outras plataformas (Telegram, WhatsApp, Discord).

### atena-wiki
1. **O que faz**: Wiki de memoria persistente para o Hermes Agent, armazenando conhecimento entre sessoes.
2. **Quando usar**: Para salvar informacoes que devem ser lembradas entre sessoes do Hermes Agent.
3. **Quando nao usar**: Anotacoes temporarias (use Obsidian); documentacao compartilhada (use Notion).

---

## Regra de Ouro

**Prefira sempre a skill mais especifica para a task.** Se nenhuma skill nativa cobrir o caso, use composio-mcp ou native-mcp como fallback. Use as skills de delegacao (claude-code, codex, opencode) quando a task estiver fora do escopo de skills disponiveis ou quando quiser processamento paralelo.
