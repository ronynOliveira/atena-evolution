# Wiki Log

> Registro cronológico de todas as ações wiki. Somente append.
> Formato: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> Quando este arquivo exceder 500 entradas: renomear para log-YYYY.md, começar novo.

## [2026-05-18] create | Wiki initialized
- Domain: Projeto Atena — memória expandida do Arquiteto
- Estrutura criada com SCHEMA.md, index.md, log.md
- Diretórios: raw/{articles,papers,transcripts,assets}, entities, concepts, comparisons, queries, _archive, _meta

## [2026-05-18] create | Páginas iniciais do Projeto Atena
- entities/projeto-atena.md — visão geral do projeto
- entities/hermes-agent.md — framework do agente
- entities/parceira-da-nuvem.md — Gemini como parceira
- entities/obsidian.md — editor de notas
- entities/llm-wiki.md — base de conhecimento
- entities/kimi-webbridge.md — ponte web
- entities/chrome-cdp.md — controle do navegador
- concepts/cidade-anomala.md — mapa conceitual
- concepts/protocolo-dialetico.md — método dialético
- concepts/teoria-do-tempo-puxado.md — futuro puxa presente
- concepts/gnostico-construtor.md — persona do Hermes
- concepts/traducao-entre-mundos.md — ponte entre mundos
- index.md atualizado com 12 páginas

## [2026-05-18] ingest | Karpathy LLM Wiki pattern
- Fonte: https://gist.github.com/karpathy/442a5bf555914893e9891c11519de94f
- Salvo em raw/articles/karpathy-llm-wiki-2026.md
- Referenciado em entities/llm-wiki.md e entities/obsidian.md

## [2026-05-18] update | Expansão de todas as páginas
- Todas as 12 páginas expandidas com conteúdo rico e wikilinks

## [2026-05-19] update | Migração da memória Hermes para o wiki
- entities/hermes-agent.md — reescrito com ambiente, regras operacionais, TTS pipeline
- entities/habilidades-aprendidas.md — criado: registro central de habilidades
- entities/ambiente-tecnico.md — criado: hardware, software, paths, portas, modelos
- index.md — atualizado com 15 páginas (9 entities + 5 concepts + 1 index)
- Wiki agora é a memória primária do Hermes

## [2026-05-20] create | Migração de memória do sistema para wiki
- concepts/diretivas-acessibilidade.md — criado: TTS, sensibilidade à luz, modelo comunicação, acessibilidade motora
- entities/ambiente-tecnico.md — atualizado: hardware, software, paths, portas, modelos, pitfalls
- index.md — atualizado com nova página de diretivas
- Estratégia definida: memória do sistema migra para wiki quando encher, ao invés de compactar

## [2026-05-20] create | Migração completa da memória do sistema
- entities/hermes-desktop.md — criado: GUI Electron v0.4.2, funcionalidades, instalação
- entities/sessao-16-05-2026.md — criado: Kimi WebBridge, quatro dimensões da parceria com Gemini
- entities/vps-oracle-cloud.md — criado: Oracle Cloud Free Tier, acesso celular, bancos de dados
- concepts/tts-windows-pipeline.md — criado: pipeline edge-tts→ffmpeg→PowerShell, regras de uso
- concepts/projetos-pendentes.md — criado: GITHUB_TOKEN, Composio, fluxo pesquisa, segurança
- concepts/diretivas-acessibilidade.md — já existia, verificado
- entities/ambiente-tecnico.md — já existia, verificado
- index.md — atualizado: 12 entities + 8 concepts + 1 index = 21 páginas wiki (+ raw/sources)
- TODAS as 13 entradas da memória do sistema agora têm páginas wiki correspondentes
- Memória do sistema pode ser limpa — wiki é a fonte primária

## [2026-05-20] create | Migração de skills e criação do sistema de automação
- entities/catalogo-skills.md — criado: 83 skills em 17 categorias, skills customizadas, regras de uso
- concepts/automacao-atena.md — criado: sistema de automação, scripts, frequência, regras
- tools/cerebro_atena.py — criado: script orquestrador principal (6 verificações)
- tools/automacao_memoria.py — criado: verificação de memória e migração
- tools/evolucao_continua.py — criado: análise com OpnCode para melhorias
- index.md — atualizado: 13 entities + 9 concepts + 1 index = 23 páginas wiki
- Memória do sistema limpa: de 13 para 2 entradas (11% → 1%)
- Estratégia: memória → wiki quando encher, nunca compactar
- Automação: scripts verificam memória, wiki, skills, pendências e evolução contínua
