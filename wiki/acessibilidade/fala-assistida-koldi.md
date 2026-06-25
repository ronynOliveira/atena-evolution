# Koldi's Fala Assistida — Pesquisa e Desenvolvimento

> Criado em 26 de Maio de 2026 para o Senhor Robério
> Distonia Generalizada → Disartria Hipercinética → Fala Irregular

## Pesquisa Realizada

### Impacto da Distonia na Fala (3 níveis)
1. **Laríngeo** — Disfonia espasmódica (voz tensa/estrangalhada)
2. **Orofacial-articulatório** — Disartria hipercinética (articulação imprecisa)
3. **Respiratório** — Padrão respiratório irregular (frases encurtadas)

### Diferença Crítica: Afasia vs Disartria
- **Afasia** = distúrbio de **linguagem** (compreensão/prejuízo)
- **Disartria** (caso do Senhor) = distúrbio **motor** (compreensão PRESERVADA)

### Stack Tecnológico Recomendado
| Componente | Ferramenta | 
|------------|------------|
| STT adaptado | Whisper + LoRA + UA-Speech corpus |
| Predição texto | BERTimbau + Trie (autocomplete rápido) |
| Completamento | GPorTuguese-2 / Gervásio 7B |
| AAC Interface | Inspirado no Cboard (open source) |
| PLN Base | spaCy pt_core_news_lg |

## Script Criado: `scripts/fala_assistida.py`

### Funcionalidades
- **Predição** de palavras (dicionário + autocomplete)
- **Frases prontas** por categoria (emergência, saudações, etc.)
- **Correção** de padrões comuns de digitação irregular (tremor)
- **TTS** integrado com voz.py
- **Menu interativo** e CLI

### Testes
- ✅ Predição: "obrig" → obrigado, obrigada, obrigado pela ajuda
- ✅ Correção: "obrigdao" → obrigado
- ✅ TTS: funcionando

### Próximas Evoluções Possíveis
- Integração com Whisper para STT de fala irregular
- Aprendizado de padrões individuais de digitação
- Modo varredura para momentos de crise
- Integração com o Memory Tree para registro de humor/saúde