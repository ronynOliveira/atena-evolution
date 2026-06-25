# USER.md — Perfil do Usuário

> Ver também: [[koldi-soul]] (identidade do Koldi), [[distonia-generalizada]] (condição de saúde), [[diretivas-acessibilidade]] (TTS, luz)

## Dados Pessoais
- **Nome civil**: Robério
- **Como chamar**: Senhor Robério (aceita "parceiro")
- **Localização**: Diadema, SP (Brasil)
- **Timezone**: America/Sao_Paulo (UTC-3)

## Saúde
- **Condição**: [[distonia-generalizada]] (afeta fala e movimentos)
- **Sensibilidade**: Luz (dificuldade para ler terminal)
- **Monitoramento**: Temperatura fria piora sintomas (alerta quando <15°C)

## Preferências
- **Comunicação**: [[tts-windows-pipeline|TTS]] (voz) obrigatório em todas as respostas
- **Voz**: pt-BR-FranciscaNeural
- **Idioma**: Português brasileiro
- **Estilo**: Direto, sem enrolação, respeitoso
- **Proatividade**: Valorizada — antecipar necessidades

## Modelo de Interação
- **Usuário DIGITA** → **OWL FALA**
- TTS primeiro, detalhes no terminal depois
- Textos longos devem ser falados e mostrados
- URLs e tokens NUNCA falar em voz alta

## Contexto Técnico
- **OS**: Windows 10 (MSYS/Git Bash)
- **Shell**: bash (MSYS), não PowerShell
- **Home**: C:\Users\dell-
- **Wiki**: C:\Users\dell-\wiki
- **GitHub**: ronynOliveira/projetoAtenacompleto

## Ferramentas Disponíveis
- Ollama local (5 modelos): gemma4:e2b, hermes3:8b, gemma4:e4b, qwen3:8b, nomic-embed
- OpenRouter: owl-alpha, deepseek-v4-flash, gemini-3.1-flash
- Kimi WebBridge: porta 10086
- Opencode, Gemini CLI, Kilo, Freebuff

## Histórico de Problemas Conhecidos
- Qwen3 reasoning model retorna content vazio
- TTS nativo não toca no CLI Windows
- Gateway restart não sobe automaticamente
- .env bloqueado para escrita
- Git push com PAT precisa de escopo repo completo
