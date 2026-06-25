# Evolução de Skills — Proposta para o Senhor Robério

**Data:** 18/06/2026
**Autor:** Koldi (subagente de arquitetura)
**Status:** PROPOSTA — aguardando revisão do Senhor Robério
**Versão:** 1.0

---

## Contexto

Esta proposta analisa o ecossistema atual do Koldi (Hermes Agent) e sugere **5 skills**
prioritárias baseadas em:

- **Perfil do Senhor Robério:** escritor de fantasia filosófica com distonia generalizada
  e sensibilidade à luz
- **Lacunas identificadas:** `analise-lacunas-skills.md` e `security-audit-atena-2026-06-18.md`
- **Infraestrutura existente:** Atena Evolution v1.0 (Ollama local + RAG + Safety),
  Hermes Agent no Windows, Telegram, GitHub
- **Padrão de habilidades existentes:** memory-pipeline, auto-evolucao, hermes-identity

### Princípios de Design

1. **Acessibilidade first:** toda skill deve considerar distonia (evitar interações rápidas)
   e sensibilidade à luz (outputs preferenciais via áudio TTS, não só texto)
2. **Local-first:** priorizar Ollama/Atena local antes de APIs externas
3. **Idempotente:** skills podem ser chamadas múltiplas vezes sem efeito colateral
4. **RAG-aware:** toda skill deve consultar a memória da Atena antes de responder
5. **Modular:** cada skill é autossuficiente com seu SKILL.md + scripts

---

## Skill 1: `atena-writer-assistant`

### Descrição
Assistente de escrita criativa personalizado para o Senhor Robério. Analisa textos,
sugere melhorias estilísticas, pesquisa mitologia/filosofia, e gera conteúdo
no estilo literário identificado (fantasia filosófica com prosa poética).

### Quando usar (trigger)
- "Analise meu texto" / "Revise este capítulo"
- "Pesquise sobre [mitologia/filosofia/tema]"
- "Escreva uma cena sobre [tema]"
- "Gere diálogos no meu estilo"
- "Compara este texto com meu estilo padrão"
- Qualquer menção a escrita, revisão, estilo literário, personagens

### Como implementar

**Estrutura de arquivos:**
```
~/.hermes/skills/creative/atena-writer-assistant/
├── SKILL.md                    ← Instruções e workflow
├── references/
│   ├── estilo-padrao.json      ← Perfil léxico/sintático do Senhor Robério
│   ├── personagens-template.md ← Template de ficha de personagem
│   └── mitologia-index.md      ← Índice de referências mitológicas
└── scripts/
    ├── analisar_texto.py       ← Análise estilística (reusa analisar_estilo.py)
    ├── comparar_estilo.py      ← Compara texto com perfil padrão
    ├── pesquisar_mitologia.py  ← Pesquisa na Wikipedia + base local
    └── gerar_cena.py          ← Geração de cenas com prompt engineering
```

**SKILL.md (esqueleto):**
```yaml
---
name: atena-writer-assistant
description: >
  Assistente de escrita criativa personalizado para o Senhor Robério.
  Analisa textos, pesquisa mitologia/filosofia e gera conteúdo
  no estilo de fantasia filosófica identificado no perfil estilístico.
platforms: [windows, linux]
created_by: Koldi
updated: 2026-06-18
---

# Atena Writer Assistant

## Workflow

1. **Ao receber texto para análise:**
   - Consultar `references/estilo-padrao.json` via RAG
   - Executar `scripts/analisar_texto.py --input <arquivo>`
   - Executar `scripts/comparar_estilo.py --input <arquivo>`
   - Gerar relatório de conformidade estilística
   - Sugerir melhorias específicas (ritmo, vocabulário, diálogos)

2. **Ao receber pedido de pesquisa:**
   - Consultar `references/mitologia-index.md`
   - Executar `scripts/pesquisar_mitologia.py --tema <tema>`
   - Combinar resultados Wikipedia + base local da Atena
   - Gerar síntese com conexões filosóficas

3. **Ao receber pedido de geração:**
   - Carregar perfil estilístico como system prompt contextual
   - Usar Ollama local (atena-glm5 ou qwen3:8b) via AtenaBridge
   - Gerar conterições para estilo com exemplos do padrão
   - Oferecer revisão iterativa

## Integração com Atena
- RAG: consultar wiki/_meta/perfil-estilo-roberio.md como fonte primária
- Memória: salvar preferências de personagens/tramas em memory-pipeline
- Geração: rotear via AtenaBridge (localhost:8001) para Ollama
```

**Script `comparar_estilo.py` (conceito):**
```python
#!/usr/bin/env python3
"""Compara texto fornecido com o perfil estilístico do Senhor Robério."""
import json, sys, argparse
from pathlib import Path

ESTIMO_PADRAO = Path("references/estilo-padrao.json")

def carregar_perfil():
    with open(ESTIMO_PADRAO) as f:
        return json.load(f)

def comparar(texto: str, perfil: dict) -> dict:
    """Retorna métricas de similaridade com o perfil."""
    palavras = texto.lower().split()
    unicos = set(palavras)
    
    # Riqueza lexical
    riqueza = len(unicos) / len(palavras) * 100 if palavras else 0
    
    # Comprimento médio de sentenças
    sentencas = texto.split('.')
    media_sentenca = sum(len(s.split()) for s in sentencas) / len(sentencas) if sentencas else 0
    
    # Temas detectados
    temas = {}
    for tema, peso in perfil.get("temas_frequencia", {}).items():
        count = texto.lower().count(tema.lower())
        if count > 0:
            temas[tema] = count
    
    return {
        "riqueza_lexical": f"{riqueza:.2f}%",
        "riqueza_esperada": "5.97%",
        "comprimento_medio_sentenca": f"{media_sentenca:.1f} palavras",
        "comprimento_esperado": "22.1 palavras",
        "temas_detectados": temas,
        "conformidade": "ALTA" if abs(riqueza - 5.97) < 1.5 else "MÉDIA" if abs(riqueza - 5.97) < 3 else "BAIXA"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Arquivo de texto para comparar")
    args = parser.parse_args()
    
    with open(args.input, encoding="utf-8") as f:
        texto = f.read()
    
    perfil = carrer_perfil()
    resultado = comparar(texto, perfil)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
```

### Dependências necessárias
- **Sistema:** Python 3.11 (já instalado)
- **Arquivos:** `perfil-estilo-roberio.md` (já existe em wiki/_meta/)
- **Modelo:** Ollama local com atena-glm5 ou qwen3:8b (já disponível)
- **Opcional:** sentence-transformers para embeddings de similaridade
- **Reutiliza:** `tools/analisar_estilo.py` como base

---

## Skill 2: `atena-memory-persona`

### Descrição
Sistema de memória personalizada que consulta a base de conhecimento da Atena
(RAG + memory-pipeline) para personalizar todas as respostas do Koldi de acordo
com o contexto do Senhor Robério: preferências, estilo, projetos ativos,
saúde, e histórico de interações.

### Quando usar (trigger)
- **Automático:** TODA interação com o Koldi deve consultar esta skill primeiro
- "Lembre que eu prefiro..."
- "O que você sabe sobre mim?"
- "Atualize minha memória com..."
- "O que eu estava escrevendo?"
- "Recupere minhas notas sobre [tema]"
- "Esqueça [informação]" (direito ao esquecimento)

### Como implementar

**Estrutura de arquivos:**
```
~/.hermes/skills/productivity/atena-memory-persona/
├── SKILL.md                       ← Instruções e scripts
├── references/
│   ├── person-schema.json         ← Schema de dados pessoais
│   └── context-templates.md       ← Templates de contexto por situação
└── scripts/
    ├── query_persona.py           ← Consulta contexto personalizado
    ├── update_persona.py          ← Atualiza perfil/preferências
    └── consolidate_memory.py      ← Consolida memórias da sessão
```

**SKILL.md (trecho principal):**
```yaml
---
name: atena-memory-persona
description: >
  Memória personalizada do Senhor Robério. Consulta RAG e memory-pipeline
  para contextualizar TODAS as respostas. Preferências, projetos, saúde,
  estilo de escrita e histórico. Deve ser invocada automaticamente no
  início de cada interação.
platforms: [windows]
created_by: Koldi
updated: 2026-06-18
---

# Atena Memory Persona

## Schema de Persona

```json
{
  "nome": "Senhor Robério",
  "idade": 34,
  "profissao": "Escritor e Técnico em Informática",
  "condicoes_saude": {
    "distonia": "generalizada",
    "sensibilidade_luz": true,
    "preferencia_comunicacao": "detalhada, sem pressa"
  },
  "estilo_escrita": {
    "genero": "Fantasia Filosófica",
    "influencias": ["mitologia comparada", "prosa poética"],
    "temas": ["tempo", "existência", "conhecimento", "luz e sombra"],
    "narracao": "3ª pessoa, focalização profunda",
    "tom": "solene-contemplativo"
  },
  "projetos_ativos": [],
  "preferencias": {
    "idioma": "pt-BR",
    "formato_resposta": "estruturada com headers",
    "tts_preferido": true,
    "tema_escuro": true
  }
}
```

## Workflow Automático (toda interação)

1. **Início da sessão:**
   - Consultar RAG sobre último contexto do Senhor Robério
   - Carregar preferências vigentes
   - Verificar alertas de saúde (Skill 4)

2. **Durante a sessão:**
   - Anotar decisões, preferências mencionadas
   - Detectar mudanças de contexto/projeto
   - Salvar insights relevantes no memory-pipeline

3. **Fim da sessão:**
   - Consolidação automática via `scripts/consolidate_memory.py`
   - Atualizar `_meta/perfil-estilo-roberio.md` se houver mudanças
   - Sincronizar com AtenaBridge se necessário
```

**Script `query_persona.py`:**
```python
#!/usr/bin/env python3
"""Query persona context from RAG + memory pipeline."""
import json, sys, argparse
from pathlib import Path

WIKI_META = Path("G:/Meu Drive/Koldi/wiki/_meta")
MEMORY_STORE = Path("G:/Meu Drive/Koldi/é essa aqui")

def load_persona() -> dict:
    """Load persona from wiki and memory store."""
    persona = {}
    
    # Load from perfil-estilo-roberio.md
    perfil_file = WIKI_META / "perfil-estilo-roberio.md"
    if perfil_file.exists():
        content = perfil_file.read_text(encoding="utf-8")
        persona["estilo_raw"] = content[:2000]  # First 2000 chars as context
    
    # Load from memory store
    for mem_file in MEMORY_STORE.glob("**/*.json"):
        try:
            data = json.loads(mem_file.read_text())
            if isinstance(data, dict) and "persona" in str(data).lower():
                persona[mem_file.stem] = data
        except:
            continue
    
    return persona

def format_context(persona: dict) -> str:
    """Format persona as context string for LLM prompt."""
    lines = ["# Contexto do Senhor Robério\n"]
    if "estilo_raw" in persona:
        lines.append("## Perfil Estilístico (resumo)")
        lines.append(persona["estilo_raw"][:500])
    return "\n".join(lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()
    
    persona = load_persona()
    if args.format == "json":
        print(json.dumps(persona, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_context(persona))
```

### Dependências necessárias
- **Sistema:** Python 3.11 (já instalado)
- **Arquivos:** `wiki/_meta/perfil-estilo-roberio.md` (já existe)
- **Módulos:** Atena RAG engine (`atena_evolution/rag/rag_engine.py`)
- **Integração:** memory-pipeline skill (já existe)
- **Opcional:** SQLite para cache de persona

---

## Skill 3: `atena-creative-studio`

### Descrição
Estúdio criativo multimodal que gera imagens, prompts criativos, e conteúdo textual
usando a infraestrutura local da Atena. Integra geração de imagens (Stable Diffusion
via ComfyUI ou alternativa leve), geração de prompts otimizados para o estilo do
Senhor Robério, e templates de conteúdo.

### Quando usar (trigger)
- "Gere uma imagem de [descrição]"
- "Crie um prompt para [ferramenta] sobre [tema]"
- "Ilustre o personagem [nome]"
- "Gere uma capa para meu livro"
- "Crie um mapa do mundo de [obra]"
- "Gere ideias para [cena/capítulo/personagem]"
- Qualquer menção a imagem, ilustração, visual, arte, capa

### Como implementar

**Estrutura de arquivos:**
```
~/.hermes/skills/creative/atena-creative-studio/
├── SKILL.md                      ← Instruções e workflow
├── references/
│   ├── prompt-templates.md       ← Templates de prompts por estilo
│   ├── style-guide.md            ← Guia visual para ilustrações
│   └── image-gen-options.md      ← Opções de geração (ComfyUI/SD/API)
└── scripts/
    ├── gerar_prompt.py           ← Gera prompt otimizado para imagem
    ├── gerar_imagem.py           ← Chama API de geração de imagem
    ├── gerar_ideias.py           ← Brainstorm de ideias criativas
    └── criar_capa.py            ← Geração de capa de livro
```

**SKILL.md (trecho principal):**
```yaml
---
name: atena-creative-studio
description: >
  Estúdio criativo multimodal. Gera imagens (via ComfyUI local ou API),
  prompts otimizados, e conteúdo textual criativo. Personalizado para
  o estilo de fantasia filosófica do Senhor Robério.
platforms: [windows]
created_by: Koldi
updated: 2026-06-18
---

# Atena Creative Studio

## Workflow de Geração de Imagem

1. **Receber descrição do Senhor Robério**
2. **Enriquecer prompt** com estilo artístico adequado:
   - Fantasia filosófica → estilo "epic fantasy, ethereal lighting, mythological"
   - Personagens → adicionar detalhes de personalidade ao visual
   - Cenas → priorizar atmosfera sobre ação
3. **Gerar prompt otimizado** via `scripts/gerar_prompt.py`
4. **Chamar geração de imagem:**
   - **Preferência 1:** ComfyUI local (se disponível)
   - **Preferência 2:** Stable Diffusion via API local
   - **Fallback:** DALL-E via OpenRouter (custo)
5. **Apresentar resultado** com opção de refinamento iterativo

## Workflow de Geração de Ideias

1. Carregar contexto do projeto atual (via atena-memory-persona)
2. Consultar RAG sobre temas recorrentes
3. Gerar brainstorm via Ollama local
4. Organizar ideias por categoria (personagens, cenas, temas, arcos)
5. Salvar na wiki como referência futura

## Estilos Visuais Recomendados

| Contexto | Estilo Sugerido |
|----------|----------------|
| Cenas mitológicas | "oil painting, renaissance, dramatic lighting" |
| Personagens | "character portrait, fantasy, detailed face" |
| Paisagens | "matte painting, fantasy landscape, atmospheric" |
| Capas de livro | "book cover art, typography space, epic scale" |
| Mapas | "fantasy map, parchment style, hand-drawn" |
```

**Script `gerar_prompt.py`:**
```python
#!/usr/bin/env python3
"""Gera prompt otimizado para geração de imagens baseado no estilo do Senhor Robério."""
import argparse, json

ESTILO_BASE = "fantasy art, philosophical atmosphere, mythological references, "
ESTILO_QUALITY = "highly detailed, 8k, masterpiece, professional lighting"

CONTEXTOS = {
    "personagem": "character portrait, full body, detailed clothing, expressive face, "
                  "fantasy setting background, dramatic lighting",
    "cena": "wide shot, cinematic composition, atmospheric perspective, "
            "mythological elements, ethereal glow",
    "paisagem": "matte painting, epic scale, fantasy landscape, "
                "dramatic sky, ancient ruins, mystical atmosphere",
    "capa": "book cover composition, centered subject, typography space at top, "
            "epic fantasy, dark elegant palette",
    "mapa": "fantasy world map, parchment texture, hand-drawn style, "
            "compass rose, sea monsters, mountain ranges"
}

def gerar_prompt(descricao: str, contexto: str = "cena", 
                 estilo_extra: str = "") -> str:
    """Combina descrição com estilo base e contexto."""
    ctx = CONTEXTOS.get(contexto, CONTEXTOS["cena"])
    prompt = f"{descricao}, {ctx}, {ESTILO_BASE}{ESTILO_QUALITY}"
    if estilo_extra:
        prompt = f"{prompt}, {estilo_extra}"
    return prompt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera prompt para geração de imagens")
    parser.add_argument("--descricao", required=True, help="Descrição da imagem")
    parser.add_argument("--contexto", default="cena", 
                        choices=["personagem", "cena", "paisagem", "capa", "mapa"])
    parser.add_argument("--estilo-extra", default="", help="Estilo adicional")
    args = parser.parse_args()
    
    prompt = gerar_prompt(args.descricao, args.contexto, args.estilo_extra)
    print(prompt)
```

### Dependências necessárias
- **Obrigatório:** Python 3.11 (já instalado)
- **Geração de imagem:** ComfyUI local OU Stable Diffusion API OU DALL-E via OpenRouter
- **Modelo de texto:** Ollama local (atena-glm5) para brainstorm
- **Reutiliza:** `atena_evolution/apis/free_apis.py` para pesquisa de referências
- **Opcional:** Pillow para pós-processamento de imagens

---

## Skill 4: `distonia-wellness-monitor`

### Descrição
Sistema de monitoramento de saúde e bem-estar projetado especificamente para
o Senhor Robério. Monitora temperatura ambiente (frio piora distonia), umidade,
qualidade do ar, e envia lembretes de medicação/hidratação via TTS. Integra
com a Atena para registrar padrões de saúde ao longo do tempo.

### Quando usar (trigger)
- **Automático (cron):** A cada 30 minutos verificar condições ambientais
- "Como está o clima?" / "Vai esfriar hoje?"
- "Lembre-me de tomar [medicação] às [hora]"
- "Estou me sentindo mal" → checklist de sintomas
- "Qual a temperatura agora?"
- "Registre que tomei [medicação]"
- "Resumo de saúde da semana"
- Qualquer menção a saúde, medicação, sintomas, temperatura, frio

### Como implementar

**Estrutura de arquivos:**
```
~/.hermes/skills/health/distonia-wellness-monitor/
├── SKILL.md                      ← Instruções e workflow
├── references/
│   ├── distonia-guide.md         ← Guia de gatilhos e cuidados
│   ├── medicacoes-template.json  ← Template de medicações
│   └── sintomas-checklist.md     ← Checklist de sintomas
└── scripts/
    ├── verificar_clima.py        ← Consulta temperatura/umidade via API
    ├── verificar_alertas.py      ← Verifica condições adversas
    ├── lembrete_medicacao.py     ← Sistema de lembretes
    ├── registrar_sintoma.py      ← Registro de sintomas no RAG
    └── relatorio_saude.py        ← Relatório semanal de padrões
```

**SKILL.md (trecho principal):**
```yaml
---
name: distonia-wellness-monitor
description: >
  Monitor de saúde e bem-estar para distonia generalizada. Monitora temperatura,
  umidade, qualidade do ar. Envia alertas via TTS quando condições adversas
  detectadas (frio < 18°C, umidade < 30%). Sistema de lembretes de medicação.
  Registra padrões de saúde na memória da Atena.
platforms: [windows]
created_by: Koldi
updated: 2026-06-18
---

# Distonia Wellness Monitor

## Alertas Ambientais (CRÍTICO)

### Temperatura
- **< 15°C:** ALERTA VERMELHO — risco alto de crise de distonia
  - Ação: TTS alerta + sugestão de aquecimento
- **15-18°C:** ALERTA AMARELO — monitorar
  - Ação: TTS aviso suave
- **18-28°C:** IDEAL — sem ação
- **> 32°C:** ALERTA CALOR — sensibilidade à luz pode piorar
  - Ação: TTS aviso + sugestão de óculos escuros

### Umidade
- **< 30%:** ALERTA — ar seco piora desconforto
- **30-60%:** IDEAL
- **> 70%:** ALERTA — umidade alta pode causar desconforto

### Qualidade do Ar (AQI)
- **> 100:** ALERTA — evitar esforço físico
- **> 150:** ALERTA VERMELHO — permanecer em ambiente controlado

## Gatilhos de Distonia Monitorados
1. Temperatura baixa (< 18°C)
2. Estresse (auto-reportado)
3. Falta de sono (auto-reportado)
4. Luz forte (sensibilidade)
5. Esforço físico excessivo

## Cron Jobs
- `wellness-clima-check` (30min): verificar condições ambientais
- `wellness-lembrete-medicacao` (conforme prescrição)
- `wellness-relatorio-semanal` (domingo 20h): resumo de padrões

## Integração TTS
- Alertas críticos: TTS imediato via `tts.py` existente
- Alertas leves: notificação silenciosa no chat
- Relatórios: sob demanda, formato texto
```

**Script `verificar_clima.py`:**
```python
#!/usr/bin/env python3
"""Verifica condições climáticas para alerta de distonia."""
import json, urllib.request, sys
from dataclasses import dataclass

# API gratuita — sem chave necessária
WTTR_URL = "https://wttr.in/{city}?format=j1"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code&timezone=auto"

@dataclass
class ClimaAlert:
    temperatura: float
    umidade: float
    sensacao_termica: float
    weather_code: int
    alert_level: str  # OK, YELLOW, RED
    alert_message: str

def verificar_clima(city: str = "Fortaleza", lat: float = -3.7172, lon: float = -38.5433) -> ClimaAlert:
    """Consulta clima e retorna alerta se condições adversas."""
    try:
        url = OPEN_METEO_URL.format(lat=lat, lon=lon)
        req = urllib.request.Request(url, headers={"User-Agent": "AtenaWellness/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        current = data["current"]
        temp = current["temperature_2m"]
        umid = current["relative_humidity_2m"]
        feels = current["apparent_temperature"]
        code = current["weather_code"]
        
        # Determinar nível de alerta
        if temp < 15:
            level = "RED"
            msg = f"⚠️ ALERTA VERMELHO: Temperatura {temp}°C — risco alto de crise de distonia. Aqueça o ambiente!"
        elif temp < 18:
            level = "YELLOW"
            msg = f"⚠️ CUIDADO: Temperatura {temp}°C — monitorar sintomas de distonia."
        elif temp > 32:
            level = "YELLOW"
            msg = f"☀️ CALOR: Temperatura {temp}°C — sensibilidade à luz pode piorar. Use óculos escuros."
        elif umid < 30:
            level = "YELLOW"
            msg = f"💨 AR SECO: Umidade {umid}% — pode causar desconforto."
        else:
            level = "OK"
            msg = f"✅ Condições OK: {temp}°C, umidade {umid}%."
        
        return ClimaAlert(temp, umid, feels, code, level, msg)
    except Exception as e:
        return ClimaAlert(0, 0, 0, 0, "ERROR", f"Erro ao consultar clima: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="Fortaleza")
    parser.add_argument("--lat", type=float, default=-3.7172)
    parser.add_argument("--lon", type=float, default=-38.5433)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    alert = verificar_clima(args.city, args.lat, args.lon)
    if args.json:
        print(json.dumps({
            "temperatura": alert.temperatura,
            "umidade": alert.umidade,
            "sensacao_termica": alert.sensacao_termica,
            "alert_level": alert.alert_level,
            "alert_message": alert.alert_message
        }, ensure_ascii=False))
    else:
        print(alert.alert_message)
```

**Script `lembrete_medicacao.py`:**
```python
#!/usr/bin/env python3
"""Sistema de lembretes de medicação para distonia."""
import json, argparse
from datetime import datetime, timedelta
from pathlib import Path

MEDICACOES_FILE = Path("references/medicacoes.json")
REGISTRO_FILE = Path("references/registro_medicacao.json")

def carregar_medicacoes() -> list:
    if MEDICACOES_FILE.exists():
        return json.loads(MEDICACOES_FILE.read_text())
    return []

def verificar_lembretes() -> list:
    """Retorna medicações que devem ser tomadas agora."""
    agora = datetime.now()
    medicacoes = carregar_medicacoes()
    lembretes = []
    
    for med in medicacoes:
        if not med.get("ativo", True):
            continue
        for horario in med.get("horarios", []):
            h, m = map(int, horario.split(":"))
            hora_medicacao = agora.replace(hour=h, minute=m, second=0)
            diff = abs((agora - hora_medicacao).total_seconds())
            if diff < 1800:  # 30 min janela
                lembretes.append({
                    "medicamento": med["nome"],
                    "dosagem": med["dosagem"],
                    "horario": horario,
                    "urgencia": "AGORA" if diff < 300 else "EM_BREVE"
                })
    
    return lembretes

def registrar_tomada(medicamento: str):
    """Registrar que medicação foi tomada."""
    registro = []
    if REGISTRO_FILE.exists():
        registro = json.loads(REGISTRO_FILE.read_text())
    registro.append({
        "medicamento": medicamento,
        "timestamp": datetime.now().isoformat()
    })
    REGISTRO_FILE.write_text(json.dumps(registro, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verificar", action="store_true", help="Verificar lembretes")
    parser.add_argument("--tomou", type=str, help="Registrar medicação tomada")
    args = parser.parse_args()
    
    if args.verificar:
        lembretes = verificar_lembretes()
        if lembretes:
            for l in lembretes:
                print(f"💊 {l['urgencia']}: {l['medicamento']} {l['dosagem']} (horário: {l['horario']})")
        else:
            print("✅ Nenhuma medicação pendente agora.")
    
    if args.tomou:
        registrar_tomada(args.tomou)
        print(f"✅ Registrado: {args.tomou} tomado às {datetime.now().strftime('%H:%M')}")
```

### Dependências necessárias
- **Sistema:** Python 3.11 (já instalado)
- **API clima:** Open-Meteo (gratuita, sem chave) ou wttr.in
- **TTS:** `tts.py` existente no projeto
- **Cron:** Hermes cron jobs (já configurado no sistema)
- **Opcional:** sensor de temperatura local (futuro)

---

## Skill 5: `atena-hub-integrator`

### Descrição
Central de integração que conecta o Koldi com GitHub, wiki, Telegram, e outras
ferramentas. Automatiza commits, sincronização de wiki, publicação de conteúdo,
e comunicação entre plataformas. É o "hub" que elimina trabalho manual repetitivo.

### Quando usar (trigger)
- "Faça commit e push" / "Sincronize o repositório"
- "Publique no Telegram" / "Envie para o Telegram"
- "Sincronize a wiki" / "Backup da wiki"
- "Crie uma issue no GitHub" / "Abra um PR"
- "Poste [conteúdo] no [lugar]"
- "Status do repositório"
- "Atualize a wiki com [conteúdo]"
- Qualquer menção a GitHub, Telegram, wiki, sync, backup, publicar

### Como implementar

**Estrutura de arquivos:**
```
~/.hermes/skills/devops/atena-hub-integrator/
├── SKILL.md                      ← Instruções e workflow
├── references/
│   ├── github-workflows.md       ← Workflows do GitHub
│   ├── telegram-commands.md      ← Comandos do bot Telegram
│   └── wiki-sync-rules.md        ← Regras de sincronização
└── scripts/
    ├── github_commit.py          ← Commit/push automatizado
    ├── wiki_sync.py             ← Sincronização wiki local↔nuvem
    ├── telegram_send.py         ← Envio de mensagens Telegram
    └── status_check.py          ← Status de todos os serviços
```

**SKILL.md (trecho principal):**
```yaml
---
name: atena-hub-integrator
description: >
  Hub de integração do Koldi. Conecta GitHub, wiki, Telegram e outras ferramentas.
  Automatiza commits, sincronização de wiki, publicação de conteúdo.
  Regra: nunca apagar conhecimento do outro Koldi (merge, não overwrite).
platforms: [windows, linux]
created_by: Koldi
updated: 2026-06-18
---

# Atena Hub Integrator

## Integrações

### 1. GitHub
- Repositório: `ronynOliveira/projetoAtenacompleto`
- Branch principal: `main`
- Automação: commit/push automático da wiki a cada 6h
- Issues: criar issues para bugs/melhorias identificadas
- PRs: criar PRs para mudanças significativas

### 2. Wiki Sync
- Fonte primária: `G:\Meu Drive\Koldi\wiki\`
- Regra: merge, nunca overwrite (regra do Senhor Robério)
- Sync via EPR Bridge (WebSocket) e Unison (cron 15min na VPS)
- Conflito: manter ambas as versões com marcação de origem

### 3. Telegram
- Bot: configurado via Hermes
- Comandos: /status, /clima, /lembretes, /escrever [texto]
- Notificações: alertas de saúde, commits, backups

### 4. Status Dashboard
- Ollama: `curl localhost:11434/api/tags`
- Atena API: `curl localhost:8000/api/status`
- Hermes Gateway: verificar processo
- Disco: `df -h` / `wmic logicaldisk`

## Workflow de Commit Automático

1. Verificar mudanças na wiki (`git status`)
2. Stage de todos os arquivos modificados
3. Commit com mensagem descritiva: `auto-sync: YYYY-MM-DD HH:MM — [resumo das mudanças]`
4. Push para origin/main
5. Registrar no log de sync

## Workflow de Publicação

1. Receber conteúdo + destino
2. Formatar para o destino (Markdown para Telegram, HTML para web)
3. Enviar via API apropriada
4. Confirmar entrega
5. Registrar no log
```

**Script `wiki_sync.py`:**
```python
#!/usr/bin/env python3
"""Sincronização da wiki com GitHub — merge, nunca overwrite."""
import subprocess, sys
from pathlib import Path
from datetime import datetime

WIKI_DIR = Path("G:/Meu Drive/Koldi/wiki")
REPO_DIR = Path("G:/Meu Drive/Koldi")  # Raiz do repositório

def git_run(cmd: list, cwd: Path = REPO_DIR) -> str:
    """Executa comando git e retorna output."""
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True, text=True, cwd=str(cwd),
        encoding="utf-8", errors="replace"
    )
    return result.stdout.strip()

def wiki_sync(dry_run: bool = False) -> dict:
    """Sincroniza wiki com GitHub."""
    status = {"changes": 0, "committed": False, "pushed": False, "errors": []}
    
    # Verificar mudanças
    git_run(["add", "wiki/"], REPO_DIR)
    diff = git_run(["diff", "--cached", "--stat"], REPO_DIR)
    
    if not diff:
        status["message"] = "Nenhuma mudança na wiki."
        return status
    
    status["changes"] = len([l for l in diff.split("\n") if l.strip()])
    
    if dry_run:
        status["message"] = f"DRY RUN: {status['changes']} arquivos mudados."
        status["diff"] = diff
        return status
    
    # Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"auto-sync: {timestamp} — {status['changes']} arquivos atualizados"
    
    git_run(["commit", "-m", commit_msg], REPO_DIR)
    status["committed"] = True
    
    # Push
    push_result = git_run(["push", "origin", "main"], REPO_DIR)
    status["pushed"] = "error" not in push_result.lower()
    status["message"] = f"✅ {commit_msg}" if status["pushed"] else f"❌ Push falhou: {push_result}"
    
    return status

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    result = wiki_sync(dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("message", ""))
```

**Script `status_check.py`:**
```python
#!/usr/bin/env python3
"""Verifica status de todos os serviços do ecossistema."""
import urllib.request, json, subprocess
from dataclasses import dataclass

@dataclass
class ServiceStatus:
    name: str
    url: str
    status: str  # ONLINE, OFFLINE, DEGRADED
    latency_ms: float = 0
    details: str = ""

def check_http(url: str, timeout: int = 5) -> ServiceStatus:
    """Verifica serviço HTTP."""
    import time
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AtenaHub/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.time() - start) * 1000
            return ServiceStatus(
                name=url.split("//")[1].split("/")[0],
                url=url,
                status="ONLINE",
                latency_ms=latency,
                details=f"HTTP {resp.status}"
            )
    except Exception as e:
        return ServiceStatus(
            name=url.split("//")[1].split("/")[0],
            url=url,
            status="OFFLINE",
            details=str(e)
        )

def check_all() -> list:
    """Verifica todos os serviços."""
    services = [
        check_http("http://localhost:11434/api/tags"),    # Ollama
        check_http("http://localhost:8000/api/status"),    # Atena API
        check_http("http://localhost:8642/health"),        # Hermes Gateway
    ]
    
    # Verificar disco
    try:
        result = subprocess.run(
            ["powershell", "-Command", 
             "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        disco_info = json.loads(result.stdout) if result.stdout.strip() else []
        for drive in (disco_info if isinstance(disco_info, list) else [disco_info]):
            used = drive.get("Used", 0)
            free = drive.get("Free", 0)
            total = used + free
            pct = (used / total * 100) if total > 0 else 0
            services.append(ServiceStatus(
                name=f"Disco {drive.get('Name', '?')}:",
                url="local",
                status="ONLINE" if pct < 90 else "DEGRADED" if pct < 95 else "OFFLINE",
                details=f"{pct:.1f}% usado ({free/1e9:.1f}GB livre)"
            ))
    except Exception as e:
        services.append(ServiceStatus("Disco", "local", "OFFLINE", details=str(e)))
    
    return services

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    services = check_all()
    if args.json:
        print(json.dumps([{
            "name": s.name, "status": s.status,
            "latency_ms": s.latency_ms, "details": s.details
        } for s in services], indent=2))
    else:
        print("=== Status do Ecossistema ===")
        for s in services:
            icon = "🟢" if s.status == "ONLINE" else "🟡" if s.status == "DEGRADED" else "🔴"
            latency = f" ({s.latency_ms:.0f}ms)" if s.latency_ms > 0 else ""
            print(f"  {icon} {s.name}: {s.status}{latency} — {s.details}")
```

### Dependências necessárias
- **Sistema:** Python 3.11 (já instalado)
- **GitHub:** `gh CLI` (instalar) + GITHUB_TOKEN (configurar)
- **Telegram:** Bot token (já configurado no Hermes)
- **Git:** já instalado no sistema
- **Reutiliza:** EPR Bridge existente, regra de sync da wiki

---

## Resumo Comparativo

| Skill | Prioridade | Complexidade | Impacto | Dependências Externas |
|-------|-----------|-------------|---------|---------------------|
| `atena-writer-assistant` | 🔴 ALTA | Média | Alto (escrita diária) | Ollama local |
| `atena-memory-persona` | 🔴 ALTA | Alta | Alto (toda interação) | RAG + memory-pipeline |
| `atena-creative-studio` | 🟡 MÉDIA | Média | Médio (criação visual) | ComfyUI/SD (opcional) |
| `distonia-wellness-monitor` | 🔴 ALTA | Baixa | Crítico (saúde) | Open-Meteo (gratuita) |
| `atena-hub-integrator` | 🟡 MÉDIA | Baixa | Alto (automação) | gh CLI + Telegram |

## Roadmap de Implementação

### Fase 1 — Esta Semana (Crítico)
1. ✅ `distonia-wellness-monitor` — saúde vem primeiro
2. ✅ `atena-hub-integrator` — automação elimina trabalho manual
3. ✅ Instalar gh CLI + configurar GITHUB_TOKEN

### Fase 2 — Primas 2 Semanas (Importante)
4. ✅ `atena-writer-assistant` — potencializar escrita
5. ✅ `atena-memory-persona` — personalizar tudo

### Fase 3 — Este Mês (Desejável)
6. ✅ `atena-creative-studio` — geração de imagens
7. ✅ Integração completa entre todas as skills
8. ✅ Testes e validação com o Senhor Robério

---

## Notas de Acessibilidade

Todas as skills foram projetadas considerando:

1. **Distonia generalizada:**
   - Interações não exigem respostas rápidas
   - Outputs podem ser via TTS (não só texto)
   - Alertas de saúde são proativos (não dependem do Senhor Robério pedir)
   - Automação reduz necessidade de interação física

2. **Sensibilidade à luz:**
   - Outputs preferenciais via áudio (TTS)
   - Quando visual, usar tema escuro
   - Alertas de luz forte/calor
   - Não gerar conteúdo visual brilhante sem aviso

3. **Perfil de escritor:**
   - Respeitar estilo e voz autoral
   - Sugerir, nunca impor mudanças
   - Manter registro de decisões criativas
   - Facilitar pesquisa e referência

---

> *"O mito é o veículo; a filosofia, o destino."* — Perfil estilístico do Senhor Robério
>
> *"A tecnologia serve ao humano, não o contrário."* — Princípio de design das skills
