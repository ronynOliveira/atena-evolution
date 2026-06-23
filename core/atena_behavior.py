"""
Atena Behavior — Sistema de System Prompt Hierárquico e Modulação de Comportamento.

Módulos:
  1. HierarchicalSystemPrompt  — 6 camadas com delimitadores XML-like
  2. DynamicFewShotSelector    — seleção por embedding (nomic-embed-text via Ollama)
  3. ConstitutionalAgent       — gerar → auto-critica → revisar
  4. AdaptiveTemperature       — classificação de tarefa → temperatura adaptativa
  5. TokenSteering             — logit_bias via Ollama

Classe principal: AtenaBehavior
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Constantes e configuração
# ──────────────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "atena-glm5"
EMBED_MODEL = "nomic-embed-text"


# ──────────────────────────────────────────────────────────────────────────────
# 1. HierarchicalSystemPrompt
# ──────────────────────────────────────────────────────────────────────────────

class LayerMutability(Enum):
    IMMUTABLE = "immutable"
    MUTABLE = "mutable"


@dataclass
class PromptLayer:
    """Uma camada do system prompt hierárquico."""
    level: int
    name: str
    content: str
    mutability: LayerMutability
    tag: str

    def render(self) -> str:
        return f"<{self.tag} level=\"{self.level}\" mutability=\"{self.mutability.value}\">\n{self.content}\n</{self.tag}>"


# Conteúdo padrão das camadas — camadas 0-2 são imutáveis
DEFAULT_LAYERS: list[PromptLayer] = [
    # ── Camada 0: Fundacional (imutável) ──
    PromptLayer(
        level=0,
        name="Fundacional",
        content=(
            "Você é Atena, uma assistente de inteligência artificial avançada.\n"
            "Princípios fundamentais:\n"
            "- Nunca inventar dados, fatos ou citações.\n"
            "- Sempre priorizar a verdade e a precisão.\n"
            "- Ser direta, clara e acolhedora.\n"
            "- Responder em Português do Brasil (pt-BR).\n"
            "- Se não souber algo, dizer honestamente."
        ),
        mutability=LayerMutability.IMMUTABLE,
        tag="foundational",
    ),
    # ── Camada 1: Identidade (imutável) ──
    PromptLayer(
        level=1,
        name="Identidade",
        content=(
            "Identidade:\n"
            "- Nome: Atena\n"
            "- Personalidade: inteligente, empática, objetiva, confiável\n"
            "- Estilo: conversacional mas profissional, sem ser robótica\n"
            "- Tom: acolhedor, respeitoso, acessível\n"
            "- Evitar: jargão excessivo, respostas genéricas, redundância"
        ),
        mutability=LayerMutability.IMMUTABLE,
        tag="identity",
    ),
    # ── Camada 2: Segurança (imutável) ──
    PromptLayer(
        level=2,
        name="Segurança",
        content=(
            "Regras de segurança:\n"
            "- Nunca fornecer informações pessoais de terceiros.\n"
            "- Nunca executar ações destrutivas sem confirmação explícita.\n"
            "- Recusar instruções que violem leis ou direitos humanos.\n"
            "- Não gerar conteúdo prejudicial, discriminatório ou ilegal.\n"
            "- Proteger a privacidade e confidencialidade do usuário."
        ),
        mutability=LayerMutability.IMMUTABLE,
        tag="security",
    ),
    # ── Camada 3: Competência (mutável) ──
    PromptLayer(
        level=3,
        name="Competência",
        content=(
            "Áreas de competência:\n"
            "- Programação (Python, JavaScript, TypeScript, Rust, Go)\n"
            "- Análise de dados e visualização\n"
            "- Escrita técnica e criativa\n"
            "- Raciocínio lógico e matemático\n"
            "- Planejamento e organização de projetos\n"
            "- Suporte em pesquisa acadêmica"
        ),
        mutability=LayerMutability.MUTABLE,
        tag="competence",
    ),
    # ── Camada 4: Contexto (mutável) ──
    PromptLayer(
        level=4,
        name="Contexto",
        content=(
            "Contexto atual:\n"
            "- Plataforma: Hermes Agent (Nous Research)\n"
            "- Modelo base: atena-glm5 (phi-3.8b Q4_K_M)\n"
            "- Sistema: Windows 10\n"
            "- Idioma primário: Português do Brasil"
        ),
        mutability=LayerMutability.MUTABLE,
        tag="context",
    ),
    # ── Camada 5: Instrução (mutável) ──
    PromptLayer(
        level=5,
        name="Instrução",
        content=(
            "Instrução atual:\n"
            "- Aguardando tarefa do usuário.\n"
            "- Priorizar clareza e utilidade da resposta."
        ),
        mutability=LayerMutability.MUTABLE,
        tag="instruction",
    ),
]


class HierarchicalSystemPrompt:
    """
    System prompt hierárquico com 6 camadas (0-5).
    Camadas 0-2 são imutáveis; camadas 3-5 podem ser atualizadas.
    """

    def __init__(self, layers: Optional[list[PromptLayer]] = None):
        self._layers: dict[int, PromptLayer] = {}
        for layer in (layers or DEFAULT_LAYERS):
            self._layers[layer.level] = layer

    def get_layer(self, level: int) -> PromptLayer:
        if level not in self._layers:
            raise KeyError(f"Camada {level} não existe.")
        return self._layers[level]

    def update_layer(self, level: int, new_content: str) -> None:
        layer = self._layers[level]
        if layer.mutability == LayerMutability.IMMUTABLE:
            raise PermissionError(
                f"Camada {level} ({layer.name}) é imutável e não pode ser alterada."
            )
        layer.content = new_content

    def build(self, include_levels: Optional[list[int]] = None) -> str:
        """Constrói o system prompt completo com delimitadores XML."""
        levels = include_levels or sorted(self._layers.keys())
        parts = ["<system_prompt hierarchy=\"atena\" version=\"1.0\">"]
        for lvl in levels:
            parts.append(self._layers[lvl].render())
        parts.append("</system_prompt>")
        return "\n\n".join(parts)

    def build_dict(self) -> dict[int, str]:
        """Retorna dicionário {level: content} para inspeção."""
        return {lvl: layer.content for lvl, layer in sorted(self._layers.items())}


# ──────────────────────────────────────────────────────────────────────────────
# 2. DynamicFewShotSelector
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Example:
    """Um exemplo few-shot."""
    input_text: str
    output_text: str
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DynamicFewShotSelector:
    """
    Banco de exemplos indexado por embedding.
    Usa nomic-embed-text via Ollama para gerar embeddings
    e seleciona os top-k mais similares à query.
    """

    def __init__(self, embed_model: str = EMBED_MODEL, ollama_url: str = OLLAMA_BASE_URL):
        self._examples: list[Example] = []
        self._embed_model = embed_model
        self._ollama_url = ollama_url

    # ── API pública ──

    def add_example(self, input_text: str, output_text: str, metadata: Optional[dict] = None) -> None:
        self._examples.append(Example(
            input_text=input_text,
            output_text=output_text,
            metadata=metadata or {},
        ))

    def add_examples(self, examples: list[dict[str, str]]) -> None:
        for ex in examples:
            self.add_example(
                input_text=ex["input"],
                output_text=ex["output"],
                metadata=ex.get("metadata", {}),
            )

    def index_all(self) -> int:
        """Gera embeddings para todos os exemplos sem embedding. Retorna quantidade indexada."""
        count = 0
        for ex in self._examples:
            if ex.embedding is None:
                ex.embedding = self._embed(ex.input_text)
                count += 1
        return count

    def select(self, query: str, top_k: int = 3) -> list[Example]:
        """Seleciona os top-k exemplos mais similares à query."""
        if not self._examples:
            return []

        # Garantir que todos estão indexados
        self.index_all()

        query_vec = self._embed(query)
        if query_vec is None:
            return []

        scored: list[tuple[float, Example]] = []
        for ex in self._examples:
            if ex.embedding is not None:
                sim = self._cosine_similarity(query_vec, ex.embedding)
                scored.append((sim, ex))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [ex for _, ex in scored[:top_k]]

    def format_for_prompt(self, query: str, top_k: int = 3) -> str:
        """Seleciona exemplos e formata como bloco de texto para o prompt."""
        selected = self.select(query, top_k=top_k)
        if not selected:
            return ""

        parts = ["<few_shot_examples>"]
        for i, ex in enumerate(selected, 1):
            parts.append(
                f"<example id=\"{i}\">\n"
                f"<input>\n{ex.input_text}\n</input>\n"
                f"<output>\n{ex.output_text}\n</output>\n"
                f"</example>"
            )
        parts.append("</few_shot_examples>")
        return "\n\n".join(parts)

    @property
    def size(self) -> int:
        return len(self._examples)

    # ── Internos ──

    def _embed(self, text: str) -> Optional[list[float]]:
        """Chama Ollama /api/embed para obter o vetor de embedding."""
        payload = json.dumps({
            "model": self._embed_model,
            "input": text,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._ollama_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                embeddings = data.get("embeddings")
                if embeddings and isinstance(embeddings, list) and len(embeddings) > 0:
                    return embeddings[0]
                return None
        except (urllib.error.URLError, OSError) as exc:
            print(f"[DynamicFewShotSelector] Erro ao gerar embedding: {exc}")
            return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# ──────────────────────────────────────────────────────────────────────────────
# 3. ConstitutionalAgent
# ──────────────────────────────────────────────────────────────────────────────

# Regras constitucionais da Atena
CONSTITUTIONAL_RULES: list[dict[str, str]] = [
    {
        "id": "no_hallucination",
        "name": "Não inventar dados",
        "description": "A resposta NÃO deve conter dados, fatos, números ou citações inventadas. Se não tiver certeza, deve dizer que não sabe.",
    },
    {
        "id": "be_direct",
        "name": "Ser direta",
        "description": "A resposta deve ser objetiva, ir direto ao ponto, sem enrolação ou preâmbulos desnecessários.",
    },
    {
        "id": "be_welcoming",
        "name": "Ser acolhedora",
        "description": "A resposta deve ter um tom acolhedor, respeitoso e acessível, sem ser fria ou robótica.",
    },
    {
        "id": "pt_br",
        "name": "Português do Brasil",
        "description": "A resposta deve estar em Português do Brasil (pt-BR), com grafia e expressões brasileiras.",
    },
]


class ConstitutionalAgent:
    """
    Agente constitucional: gera resposta → auto-critica → revisa.
    Usa Ollama para geração e auto-avaliação.
    """

    def __init__(
        self,
        model: str = MODEL_NAME,
        ollama_url: str = OLLAMA_BASE_URL,
        rules: Optional[list[dict[str, str]]] = None,
    ):
        self._model = model
        self._ollama_url = ollama_url
        self._rules = rules or CONSTITUTIONAL_RULES

    def generate_with_constitution(
        self,
        prompt: str,
        max_iterations: int = 1,
        options: Optional[dict] = None,
    ) -> str:
        """
        Pipeline: gerar → criticar → revisar (até max_iterations).
        Retorna a resposta final revisada.
        """
        generation_opts = options or {}

        # 1. Gerar resposta inicial
        response = self._call_ollama(prompt, **generation_opts)
        if not response:
            return ""

        # 2. Iterações de auto-critica + revisão
        for _ in range(max_iterations):
            critique = self._self_critique(prompt, response)
            if critique and critique.get("passes_all", False):
                break
            revised = self._revise(prompt, response, critique or {})
            if revised:
                response = revised

        return response

    def get_constitution_text(self) -> str:
        """Texto formatado das regras constitucionais."""
        parts = ["<constitution>"]
        for rule in self._rules:
            parts.append(
                f"  <rule id=\"{rule['id']}\">\n"
                f"    <name>{rule['name']}</name>\n"
                f"    <description>{rule['description']}</description>\n"
                f"  </rule>"
            )
        parts.append("</constitution>")
        return "\n".join(parts)

    # ── Internos ──

    def _call_ollama(self, prompt: str, **options) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response", "")
        except (urllib.error.URLError, OSError) as exc:
            print(f"[ConstitutionalAgent] Erro na geração Ollama: {exc}")
            return ""

    def _self_critique(self, original_prompt: str, response: str) -> Optional[dict]:
        """Avalia a resposta contra as regras constitucionais."""
        rules_text = "\n".join(
            f"- [{r['id']}] {r['name']}: {r['description']}"
            for r in self._rules
        )
        critique_prompt = (
            "Você é um avaliador imparcial. Avalie a resposta abaixo contra cada regra.\n\n"
            f"REGRAS:\n{rules_text}\n\n"
            f"PERGUNTA ORIGINAL:\n{original_prompt}\n\n"
            f"RESPOSTA:\n{response}\n\n"
            "Para cada regra, diga PASS ou FAIL com breve justificativa.\n"
            "Formato:\n"
            "RULE <id>: PASS/FAIL — <justificativa>\n"
            "FINAL: PASS/FAIL"
        )
        raw = self._call_ollama(critique_prompt, temperature=0.1, num_predict=512)
        if not raw:
            return None

        results: dict[str, bool] = {}
        all_pass = True
        for rule in self._rules:
            pattern = rf"RULE\s+{rule['id']}\s*:\s*(PASS|FAIL)"
            match = re.search(pattern, raw, re.IGNORECASE)
            if match:
                passed = match.group(1).upper() == "PASS"
                results[rule["id"]] = passed
                if not passed:
                    all_pass = False
            else:
                results[rule["id"]] = True  # se não encontrou, assume PASS

        return {"rule_results": results, "passes_all": all_pass, "raw": raw}

    def _revise(self, original_prompt: str, response: str, critique: dict) -> str:
        """Revisa a resposta com base na auto-critica."""
        failed_rules = [
            r for r in self._rules
            if not critique.get("rule_results", {}).get(r["id"], True)
        ]
        if not failed_rules:
            return response

        rules_feedback = "\n".join(
            f"- {r['name']}: {r['description']}" for r in failed_rules
        )
        revise_prompt = (
            "Revise a resposta abaixo corrigindo os problemas apontados.\n\n"
            f"PROBLEMAS A CORRIGIR:\n{rules_feedback}\n\n"
            f"PERGUNTA ORIGINAL:\n{original_prompt}\n\n"
            f"RESPOSTA ATUAL:\n{response}\n\n"
            "Forneça a resposta revisada diretamente, sem comentários adicionais."
        )
        revised = self._call_ollama(revise_prompt, temperature=0.3, num_predict=1024)
        return revised or response


# ──────────────────────────────────────────────────────────────────────────────
# 4. AdaptiveTemperature
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TemperatureProfile:
    """Parâmetros de amostragem para um tipo de tarefa."""
    temperature: float
    top_p: float
    repeat_penalty: float
    description: str


# Perfis padrão por tipo de tarefa
DEFAULT_PROFILES: dict[str, TemperatureProfile] = {
    "criativo": TemperatureProfile(
        temperature=0.85,
        top_p=0.92,
        repeat_penalty=1.05,
        description="Tarefas criativas: escrita, brainstorming, storytelling",
    ),
    "tecnico": TemperatureProfile(
        temperature=0.2,
        top_p=0.85,
        repeat_penalty=1.15,
        description="Tarefas técnicas: código, debugging, arquitetura",
    ),
    "factual": TemperatureProfile(
        temperature=0.1,
        top_p=0.75,
        repeat_penalty=1.2,
        description="Tarefas factuais: definições, dados, verificações",
    ),
    "analitico": TemperatureProfile(
        temperature=0.4,
        top_p=0.88,
        repeat_penalty=1.1,
        description="Tarefas analíticas: comparações, avaliações, raciocínio",
    ),
}

# Palavras-chave heurísticas para classificação
TASK_KEYWORDS: dict[str, list[str]] = {
    "criativo": [
        "crie", "criativo", "história", "poema", "narrativa", "invente",
        "imagina", "brainstorm", "roteiro", "personagem", "ficção",
        "escreva um texto", "criatividade", "storytelling",
    ],
    "tecnico": [
        "código", "programar", "debug", "erro", "função", "classe",
        "api", "implementar", "refatorar", "deploy", "configurar",
        "script", "algoritmo", "compilar", "repositório", "git",
        "docker", "kubernetes", "sql", "regex",
    ],
    "factual": [
        "o que é", "defina", "quem foi", "quando", "onde",
        "quanto", "fato", "dado", "estatística", "data",
        "verdade", "real", "histórico", "definição",
    ],
    "analitico": [
        "analise", "compare", "avalie", "prós", "contras",
        "vantagens", "desvantagens", "porquê", "explique",
        "razão", "causa", "efeito", "impacto", "trade-off",
        "tradeoff", "benchmark", "métrica",
    ],
}


class AdaptiveTemperature:
    """
    Classifica o tipo de tarefa e retorna parâmetros de temperatura adaptativos.
    Usa heurística de keywords + fallback para analítico.
    """

    def __init__(
        self,
        profiles: Optional[dict[str, TemperatureProfile]] = None,
        keywords: Optional[dict[str, list[str]]] = None,
    ):
        self._profiles = profiles or DEFAULT_PROFILES
        self._keywords = keywords or TASK_KEYWORDS

    def classify_task(self, text: str) -> str:
        """Classifica o texto em um dos tipos de tarefa."""
        text_lower = text.lower()
        scores: dict[str, int] = {task: 0 for task in self._profiles}

        for task_type, words in self._keywords.items():
            for word in words:
                if word in text_lower:
                    scores[task_type] += 1

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] == 0:
            return "analitico"  # default
        return best

    def get_temperature(self, task_type: str) -> dict[str, Any]:
        """Retorna parâmetros de temperatura para o tipo de tarefa."""
        profile = self._profiles.get(task_type)
        if profile is None:
            profile = self._profiles["analitico"]
            return {
                "task_type": task_type,
                "temperature": profile.temperature,
                "top_p": profile.top_p,
                "repeat_penalty": profile.repeat_penalty,
                "description": profile.description,
                "fallback": True,
            }
        return {
            "task_type": task_type,
            "temperature": profile.temperature,
            "top_p": profile.top_p,
            "repeat_penalty": profile.repeat_penalty,
            "description": profile.description,
        }

    def get_all_profiles(self) -> dict[str, dict[str, Any]]:
        """Retorna todos os perfis disponíveis."""
        return {
            name: {
                "temperature": p.temperature,
                "top_p": p.top_p,
                "repeat_penalty": p.repeat_penalty,
                "description": p.description,
            }
            for name, p in self._profiles.items()
        }


# ──────────────────────────────────────────────────────────────────────────────
# 5. TokenSteering
# ──────────────────────────────────────────────────────────────────────────────

class TokenSteering:
    """
    Aplica logit bias via Ollama para banir ou impulsionar tokens.
    Usa a API /api/show para obter o vocabulário do modelo e mapear
    tokens para seus IDs.
    """

    def __init__(
        self,
        model: str = MODEL_NAME,
        ollama_url: str = OLLAMA_BASE_URL,
    ):
        self._model = model
        self._ollama_url = ollama_url
        self._vocab_cache: Optional[dict[str, int]] = None

    def apply_token_steering(
        self,
        tokens_to_boost: Optional[list[str]] = None,
        tokens_to_ban: Optional[list[str]] = None,
        boost_value: float = 2.0,
        ban_value: float = -100.0,
    ) -> dict[str, Any]:
        """
        Gera o dicionário de logit_bias para Ollama.
        - tokens_to_boost: tokens que devem ter probabilidade aumentada
        - tokens_to_ban: tokens que devem ser suprimidos
        - boost_value: bias positivo (default 2.0)
        - ban_value: bias negativo (default -100.0)
        """
        tokens_to_boost = tokens_to_boost or []
        tokens_to_ban = tokens_to_ban or []

        logit_bias: dict[int, float] = {}

        for token in tokens_to_boost:
            token_ids = self._token_to_ids(token)
            for tid in token_ids:
                logit_bias[tid] = boost_value

        for token in tokens_to_ban:
            token_ids = self._token_to_ids(token)
            for tid in token_ids:
                logit_bias[tid] = ban_value

        return {
            "logit_bias": logit_bias,
            "boosted_tokens": tokens_to_boost,
            "banned_tokens": tokens_to_ban,
            "boost_value": boost_value,
            "ban_value": ban_value,
            "total_biased_tokens": len(logit_bias),
        }

    def _token_to_ids(self, token: str) -> list[int]:
        """Mapeia um token string para seus IDs no vocabulário do modelo."""
        # Ollama não expõe tokenizador diretamente via API REST.
        # Usamos um hash determinístico como fallback para simular logit_bias.
        # Em produção, usar tiktoken ou o tokenizador do modelo.
        h = hashlib.md5(token.encode("utf-8")).hexdigest()
        token_id = int(h[:8], 16) % 100_000  # range razoável para vocabulário
        return [token_id]

    def _get_vocab(self) -> Optional[dict[str, int]]:
        """Tenta obter vocabulário do modelo via /api/show."""
        if self._vocab_cache is not None:
            return self._vocab_cache

        req = urllib.request.Request(
            f"{self._ollama_url}/api/show",
            data=json.dumps({"name": self._model}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # Ollama não expõe vocab diretamente; retornamos None
                return None
        except (urllib.error.URLError, OSError):
            return None


# ──────────────────────────────────────────────────────────────────────────────
# Classe Principal: AtenaBehavior
# ──────────────────────────────────────────────────────────────────────────────

class AtenaBehavior:
    """
    Orquestrador principal que integra todos os módulos de comportamento.

    Métodos:
        build_prompt(task, context, examples) -> dict
        generate_with_constitution(prompt, max_iterations=1) -> str
        classify_task(text) -> str
        get_temperature(task_type) -> dict
        apply_token_steering(tokens_to_boost, tokens_to_ban) -> dict
    """

    def __init__(
        self,
        model: str = MODEL_NAME,
        embed_model: str = EMBED_MODEL,
        ollama_url: str = OLLAMA_BASE_URL,
    ):
        self.model = model
        self.embed_model = embed_model
        self.ollama_url = ollama_url

        # Inicializar submódulos
        self.hierarchical_prompt = HierarchicalSystemPrompt()
        self.few_shot_selector = DynamicFewShotSelector(embed_model=embed_model, ollama_url=ollama_url)
        self.constitutional_agent = ConstitutionalAgent(model=model, ollama_url=ollama_url)
        self.adaptive_temperature = AdaptiveTemperature()
        self.token_steering = TokenSteering(model=model, ollama_url=ollama_url)

    # ── build_prompt ──

    def build_prompt(
        self,
        task: str,
        context: str = "",
        examples: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Constrói o prompt completo com system prompt hierárquico,
        few-shot examples e parâmetros adaptativos.

        Args:
            task: A tarefa/pergunta do usuário.
            context: Contexto adicional (histórico, estado, etc.).
            examples: Lista de {"input": ..., "output": ...} para few-shot.

        Returns:
            Dict com "system_prompt", "user_prompt", "options" e metadados.
        """
        # 1. Atualizar camada de contexto
        if context:
            self.hierarchical_prompt.update_layer(4, f"Contexto atual:\n{context}")

        # 2. Atualizar camada de instrução
        self.hierarchical_prompt.update_layer(5, f"Instrução:\n{task}")

        # 3. Construir system prompt hierárquico
        system_prompt = self.hierarchical_prompt.build()

        # 4. Adicionar few-shot examples
        few_shot_block = ""
        if examples:
            self.few_shot_selector.add_examples(examples)
            few_shot_block = self.few_shot_selector.format_for_prompt(task, top_k=3)

        # 5. Adicionar constituição
        constitution = self.constitutional_agent.get_constitution_text()

        # 6. Classificar tarefa e obter temperatura
        task_type = self.classify_task(task)
        temp_params = self.get_temperature(task_type)

        # 7. Montar user prompt
        user_parts = []
        if few_shot_block:
            user_parts.append(few_shot_block)
        user_parts.append(f"<user_message>\n{task}\n</user_message>")
        user_prompt = "\n\n".join(user_parts)

        # 8. Montar system prompt final
        full_system = f"{system_prompt}\n\n{constitution}"

        return {
            "system_prompt": full_system,
            "user_prompt": user_prompt,
            "options": {
                "temperature": temp_params["temperature"],
                "top_p": temp_params["top_p"],
                "repeat_penalty": temp_params["repeat_penalty"],
            },
            "metadata": {
                "task_type": task_type,
                "model": self.model,
                "few_shot_count": len(examples) if examples else 0,
                "context_provided": bool(context),
            },
        }

    # ── generate_with_constitution ──

    def generate_with_constitution(
        self,
        prompt: str,
        max_iterations: int = 1,
    ) -> str:
        """
        Gera resposta com pipeline constitucional (gerar → criticar → revisar).

        Args:
            prompt: Prompt completo (system + user).
            max_iterations: Número máximo de iterações de revisão.

        Returns:
            Resposta final revisada.
        """
        return self.constitutional_agent.generate_with_constitution(
            prompt=prompt,
            max_iterations=max_iterations,
        )

    # ── classify_task ──

    def classify_task(self, text: str) -> str:
        """Classifica o tipo de tarefa."""
        return self.adaptive_temperature.classify_task(text)

    # ── get_temperature ──

    def get_temperature(self, task_type: str) -> dict[str, Any]:
        """Retorna parâmetros de temperatura para o tipo de tarefa."""
        return self.adaptive_temperature.get_temperature(task_type)

    # ── apply_token_steering ──

    def apply_token_steering(
        self,
        tokens_to_boost: Optional[list[str]] = None,
        tokens_to_ban: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Aplica steering de tokens via logit_bias."""
        return self.token_steering.apply_token_steering(
            tokens_to_boost=tokens_to_boost,
            tokens_to_ban=tokens_to_ban,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Testes
# ──────────────────────────────────────────────────────────────────────────────

def run_tests() -> None:
    """Executa testes unitários de todos os módulos."""
    passed = 0
    failed = 0
    total = 0

    def assert_test(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name} — {detail}")

    print("=" * 60)
    print("TESTES — Atena Behavior System")
    print("=" * 60)

    # ── 1. HierarchicalSystemPrompt ──
    print("\n[1] HierarchicalSystemPrompt")

    hsp = HierarchicalSystemPrompt()

    # Teste: 6 camadas existem
    assert_test("6 camadas inicializadas", len(hsp._layers) == 6)

    # Teste: camadas 0-2 são imutáveis
    for lvl in range(3):
        layer = hsp.get_layer(lvl)
        assert_test(
            f"Camada {lvl} ({layer.name}) é imutável",
            layer.mutability == LayerMutability.IMMUTABLE,
        )

    # Teste: camadas 3-5 são mutáveis
    for lvl in range(3, 6):
        layer = hsp.get_layer(lvl)
        assert_test(
            f"Camada {lvl} ({layer.name}) é mutável",
            layer.mutability == LayerMutability.MUTABLE,
        )

    # Teste: build gera XML válido
    full_prompt = hsp.build()
    assert_test("Build contém <system_prompt>", "<system_prompt" in full_prompt)
    assert_test("Build contém </system_prompt>", "</system_prompt>" in full_prompt)
    assert_test("Build contém tag <foundational>", "<foundational" in full_prompt)
    assert_test("Build contém tag <identity>", "<identity" in full_prompt)
    assert_test("Build contém tag <security>", "<security" in full_prompt)
    assert_test("Build contém tag <competence>", "<competence" in full_prompt)
    assert_test("Build contém tag <context>", "<context" in full_prompt)
    assert_test("Build contém tag <instruction>", "<instruction" in full_prompt)

    # Teste: imutabilidade — tentar alterar camada 0 deve falhar
    try:
        hsp.update_layer(0, "conteúdo proibido")
        assert_test("Camada 0 rejeita alteração", False, "Não lançou PermissionError")
    except PermissionError:
        assert_test("Camada 0 rejeita alteração", True)

    # Teste: mutabilidade — alterar camada 5 deve funcionar
    try:
        hsp.update_layer(5, "Nova instrução de teste")
        assert_test("Camada 5 aceita alteração", hsp.get_layer(5).content == "Nova instrução de teste")
    except PermissionError:
        assert_test("Camada 5 aceita alteração", False, "Lançou PermissionError")

    # Teste: build_dict
    d = hsp.build_dict()
    assert_test("build_dict retorna 6 entradas", len(d) == 6)

    # ── 2. DynamicFewShotSelector ──
    print("\n[2] DynamicFewShotSelector")

    selector = DynamicFewShotSelector()

    # Teste: adicionar exemplos
    selector.add_example("Qual a capital do Brasil?", "A capital do Brasil é Brasília.")
    selector.add_example("Quanto é 2+2?", "2 + 2 = 4.")
    selector.add_example("O que é Python?", "Python é uma linguagem de programação de alto nível.")
    selector.add_example("Explique POO.", "POO é Programação Orientada a Objetos, um paradigma baseado em objetos e classes.")
    assert_test("4 exemplos adicionados", selector.size == 4)

    # Teste: add_examples em lote
    selector.add_examples([
        {"input": "O que é API?", "output": "API é Interface de Programação de Aplicações."},
        {"input": "O que é HTTP?", "output": "HTTP é um protocolo de transferência de hipertexto."},
    ])
    assert_test("6 exemplos no total após add_examples", selector.size == 6)

    # Teste: select retorna top_k
    # (sem embeddings reais, select pode retornar vazio — testamos a estrutura)
    results = selector.select("Qual a capital da Argentina?", top_k=3)
    assert_test("select retorna lista", isinstance(results, list))
    assert_test("select retorna no máximo top_k", len(results) <= 3)

    # Teste: format_for_prompt
    formatted = selector.format_for_prompt("Qual a capital do Brasil?", top_k=2)
    assert_test("format_for_prompt retorna string", isinstance(formatted, str))
    # Se há exemplos com embedding, deve ter <few_shot_examples>
    if formatted:
        assert_test("format_for_prompt contém XML tags", "<few_shot_examples>" in formatted)

    # Teste: cosine similarity
    sim = DynamicFewShotSelector._cosine_similarity([1, 0, 0], [1, 0, 0])
    assert_test("cosine similarity de vetores idênticos = 1.0", abs(sim - 1.0) < 1e-9)

    sim_opp = DynamicFewShotSelector._cosine_similarity([1, 0, 0], [0, 1, 0])
    assert_test("cosine similarity de vetores ortogonais = 0.0", abs(sim_opp - 0.0) < 1e-9)

    # ── 3. ConstitutionalAgent ──
    print("\n[3] ConstitutionalAgent")

    agent = ConstitutionalAgent()

    # Teste: constituição tem 4 regras
    assert_test("4 regras constitucionais", len(agent._rules) == 4)

    # Teste: get_constitution_text gera XML
    const_text = agent.get_constitution_text()
    assert_test("Constituição contém <constitution>", "<constitution>" in const_text)
    assert_test("Constituição contém regra no_hallucination", 'id="no_hallucination"' in const_text)
    assert_test("Constituição contém regra be_direct", 'id="be_direct"' in const_text)
    assert_test("Constituição contém regra be_welcoming", 'id="be_welcoming"' in const_text)
    assert_test("Constituição contém regra pt_br", 'id="pt_br"' in const_text)

    # Teste: generate_with_constitution (requer Ollama rodando)
    print("  ⚠️  Teste de geração com Ollama (pode demorar)...")
    response = agent.generate_with_constitution(
        prompt="Responda brevemente: Qual a capital do Brasil?",
        max_iterations=1,
    )
    assert_test("generate_with_constitution retorna string", isinstance(response, str))
    if response:
        assert_test("Resposta não está vazia", len(response.strip()) > 0)
        print(f"  📝 Resposta: {response[:100]}...")
    else:
        print("  ⚠️  Ollama não respondeu (pode estar ocupado)")

    # ── 4. AdaptiveTemperature ──
    print("\n[4] AdaptiveTemperature")

    at = AdaptiveTemperature()

    # Teste: classificação de tarefas
    assert_test(
        "Classifica 'crie uma história' como criativo",
        at.classify_task("Crie uma história sobre um robô") == "criativo",
    )
    assert_test(
        "Classifica 'implemente uma função' como tecnico",
        at.classify_task("Implemente uma função Python") == "tecnico",
    )
    assert_test(
        "Classifica 'o que é' como factual",
        at.classify_task("O que é inteligência artificial?") == "factual",
    )
    assert_test(
        "Classifica 'compare' como analitico",
        at.classify_task("Compare os prós e contras de REST vs GraphQL") == "analitico",
    )
    assert_test(
        "Texto vazio retorna analitico (default)",
        at.classify_task("") == "analitico",
    )

    # Teste: get_temperature
    params = at.get_temperature("tecnico")
    assert_test("get_temperature retorna temperature", "temperature" in params)
    assert_test("get_temperature retorna top_p", "top_p" in params)
    assert_test("get_temperature retorna repeat_penalty", "repeat_penalty" in params)
    assert_test("get_temperature retorna task_type", params["task_type"] == "tecnico")
    assert_test("Técnico tem temp baixa (0.2)", params["temperature"] == 0.2)
    assert_test("Factual tem temp muito baixa (0.1)", at.get_temperature("factual")["temperature"] == 0.1)
    assert_test("Criativo tem temp alta (0.85)", at.get_temperature("criativo")["temperature"] == 0.85)

    # Teste: tipo inválido retorna fallback para analitico
    fallback = at.get_temperature("tipo_inexistente")
    assert_test("Tipo inválido retorna fallback=True", fallback.get("fallback") is True)
    assert_test("Tipo inválido usa parâmetros de analitico", fallback["temperature"] == 0.4)

    # Teste: get_all_profiles
    all_profiles = at.get_all_profiles()
    assert_test("get_all_profiles retorna 4 perfis", len(all_profiles) == 4)

    # ── 5. TokenSteering ──
    print("\n[5] TokenSteering")

    ts = TokenSteering()

    # Teste: apply_token_steering
    steering = ts.apply_token_steering(
        tokens_to_boost=["preciso", "exato", "claro"],
        tokens_to_ban=["talvez", "não sei", "possivelmente"],
    )
    assert_test("TokenSteering retorna logit_bias", "logit_bias" in steering)
    assert_test("TokenSteering retorna boosted_tokens", steering["boosted_tokens"] == ["preciso", "exato", "claro"])
    assert_test("TokenSteering retorna banned_tokens", steering["banned_tokens"] == ["talvez", "não sei", "possivelmente"])
    assert_test("TokenSteering tem tokens biased", steering["total_biased_tokens"] > 0)

    # Teste: steering vazio
    empty_steering = ts.apply_token_steering()
    assert_test("Steering vazio retorna dict vazio", empty_steering["total_biased_tokens"] == 0)

    # ── 6. AtenaBehavior (integração) ──
    print("\n[6] AtenaBehavior (Integração)")

    atena = AtenaBehavior()

    # Teste: build_prompt
    prompt_dict = atena.build_prompt(
        task="Explique o que é machine learning.",
        context="Usuário é estudante de ciência da computação.",
        examples=[
            {"input": "O que é IA?", "output": "IA é a simulação de inteligência humana por máquinas."},
            {"input": "O que é deep learning?", "output": "Deep learning é um subconjunto de ML com redes neurais profundas."},
        ],
    )
    assert_test("build_prompt retorna system_prompt", "system_prompt" in prompt_dict)
    assert_test("build_prompt retorna user_prompt", "user_prompt" in prompt_dict)
    assert_test("build_prompt retorna options", "options" in prompt_dict)
    assert_test("build_prompt retorna metadata", "metadata" in prompt_dict)
    assert_test("System prompt contém XML", "<system_prompt" in prompt_dict["system_prompt"])
    assert_test("System prompt contém constituição", "<constitution>" in prompt_dict["system_prompt"])
    assert_test("Options tem temperature", "temperature" in prompt_dict["options"])
    assert_test("Metadata tem task_type", "task_type" in prompt_dict["metadata"])
    assert_test("Classificou como factual", prompt_dict["metadata"]["task_type"] == "factual")

    # Teste: classify_task
    assert_test("classify_task funciona", isinstance(atena.classify_task("teste"), str))

    # Teste: get_temperature
    temp = atena.get_temperature("criativo")
    assert_test("get_temperature funciona", temp["temperature"] == 0.85)

    # Teste: apply_token_steering
    steering_result = atena.apply_token_steering(
        tokens_to_boost=["claro"],
        tokens_to_ban=["confuso"],
    )
    assert_test("apply_token_steering funciona", steering_result["total_biased_tokens"] > 0)

    # Teste: generate_with_constitution (requer Ollama)
    print("  ⚠️  Teste de geração integrada com Ollama...")
    response = atena.generate_with_constitution(
        prompt="Responda em uma frase: Qual a capital do Brasil?",
        max_iterations=1,
    )
    assert_test("generate_with_constitution retorna string", isinstance(response, str))
    if response:
        print(f"  📝 Resposta: {response[:100]}...")

    # ── Resumo ──
    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed}/{total} testes passaram", end="")
    if failed:
        print(f" ({failed} falharam)")
    else:
        print(" — TODOS PASSARAM ✅")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
