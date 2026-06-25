# Wiki Schema

## Domain
Projeto Atena — memória expandida do Arquiteto. Cobertura: IA, arquitetura de software, conceitos filosóficos aplicados à tecnologia, personas de agentes, ferramentas, experimentos, e o mapa conceitual da Cidade Anômala.

## Conventions
- File names: lowercase, hyphens, no spaces (ex: `transformer-architecture.md`)
- Toda página wiki começa com YAML frontmatter
- Use wikilinks para ligar páginas (mínimo 2 links de saída por página)
- Ao atualizar, sempre atualize a data `updated`
- Toda página nova deve ser adicionada ao `index.md`
- Toda ação deve ser registrada no `log.md`
- **Marcadores de proveniência:** Em páginas que sintetizam 3+ fontes, adicione `^[raw/articles/arquivo.md]` ao final de parágrafos cuja afirmação vem de uma fonte específica

## Frontmatter
```yaml
---
title: Título da Página
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [do taxonomy abaixo]
sources: [raw/articles/nome-fonte.md]
# Opcionais:
confidence: high | medium | low
contested: true
contradictions: [outro-page-slug]
---
```

### raw/ Frontmatter
```yaml
---
source_url: https://exemplo.com/artigo
ingested: YYYY-MM-DD
sha256: <hex digest>
---
```

## Tag Taxonomy

### Agentes & Personas
`agent`, `persona`, `cloud-partner`, `batedor`, `arquiteto`, `parceira-da-nuvem`

### Conceitos Filosóficos
`cidade-anomala`, `artefato-cognitivo`, `tempo-puxado`, `dialetica`, `navegacao`, `traducao-entre-mundos`, `gnostico-construtor`

### Tecnologia
`ia`, `llm`, `arquitetura`, `ferramenta`, `skill`, `plugin`, `mcp`, `cdp`, `tts`, `acessibilidade`

### Projetos
`projeto-atena`, `hermes-agent`, `obsidian`, `llm-wiki`, `kimi-webbridge`, `composio`

### Metodologia
`protocolo`, `pipeline`, `teste`, `debug`, `refatoracao-realidade`, `planejamento`

### Pessoas
`pessoa`, `pesquisador`, `criador`

## Page Thresholds
- **Criar página** quando entidade/conceito aparece em 2+ fontes ou é central em uma fonte
- **Adicionar a página existente** quando fonte menciona algo já coberto
- **NÃO criar página** para menções passageiras
- **Dividir página** quando exceder ~200 linhas
- **Arquivar página** quando conteúdo for totalmente superado — mover para `_archive/`

## Entity Pages
Uma página por entidade notável. Incluir: visão geral, fatos chave, relações ([[wikilinks]]), referências.

## Concept Pages
Uma página por conceito. Incluir: definição, estado atual, questões abertas, conceitos relacionados.

## Comparison Pages
Análises lado a lado. Incluir: o que está sendo comparado, dimensões (tabela), veredito, fontes.

## Update Policy
Quando nova informação conflita com conteúdo existente:
1. Verifique datas — fontes mais novas geralmente superam antigas
2. Se genuinamente contraditório, note ambas posições com datas e fontes
3. Marque a contradição no frontmatter: `contradictions: [page-name]`
4. Sinalize para revisão do Arquiteto no relatório de lint
