#!/usr/bin/env python3
"""
metacog_engine.py — Monitoramento do próprio processo cognitivo.

Monitora e registra o estado cognitivo durante o raciocínio, ajudando a decidir:
  - Quando duvidar (baixa confiança, inconsistências detectadas)
  - Quando pedir ajuda (fora do conhecimento, problema complexo demais)
  - Quando simplificar (público leigo, conceito pode ser simplificado)
  - Quando aprofundar (público técnico, espaço para mais detalhe)
  - Quando parar (resposta suficiente, diminishing returns)

Estados cognitivos rastreados:
  - confidence: confiança atual no raciocínio [0.0, 1.0]
  - uncertainty: nível de incerteza percebida
  - complexity: complexidade estimada do problema
  - knowledge_gap: lacunas de conhecimento detectadas
  - fatigue: fadiga cognitiva (baseada em profundidade do raciocínio)
  - mode: modo atual (explorando | refinando | concluindo | travado)

Uso:
  from metacog_engine import Metacog
  cog = Metacog("resolver bug de memória")
  cog.update(confidence=0.3, reason="não conheço esta stack")
  decision = cog.decide()
  # decision = {"action": "ask_for_help", "reason": "..."}
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class CogMode(Enum):
    EXPLORING = "explorando"
    REFINING = "refinando"
    CONCLUDING = "concluindo"
    STUCK = "travado"
    ASKING = "pedindo_ajuda"


class CogAction(Enum):
    CONTINUE = "continue"
    DEEPER = "go_deeper"
    SIMPLIFY = "simplify"
    ASK_HELP = "ask_for_help"
    STOP = "stop"
    VERIFY = "verify"
    BACKTRACK = "backtrack"
    EXPLORE_ALT = "explore_alternative"


@dataclass
class CogDecision:
    """Decisão metacognitiva."""
    action: CogAction
    reason: str
    confidence: float
    suggestions: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self) -> str:
        action_icons = {
            CogAction.CONTINUE: "▶",
            CogAction.DEEPER: "🔍",
            CogAction.SIMPLIFY: "📝",
            CogAction.ASK_HELP: "🙋",
            CogAction.STOP: "⏹",
            CogAction.VERIFY: "✅",
            CogAction.BACKTRACK: "↩",
            CogAction.EXPLORE_ALT: "🔀",
        }
        icon = action_icons.get(self.action, "?")
        lines = [f"{icon} [{self.action.value}] {self.reason} (confiança: {self.confidence:.2f})"]
        if self.suggestions:
            for s in self.suggestions:
                lines.append(f"   → {s}")
        return "\n".join(lines)


@dataclass
class CogEvent:
    """Evento no log metacognitivo."""
    event_type: str
    description: str
    confidence_before: float = 0.5
    confidence_after: float = 0.5
    mode: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "type": self.event_type,
            "description": self.description,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "mode": self.mode,
            "timestamp": self.timestamp,
        }


class Metacog:
    """
    Motor metacognitivo — monitora o próprio processo de raciocínio.

    Mantém estado cognitivo e toma decisões sobre como proceder.
    Registra histórico de eventos para análise posterior.

    Exemplo:
        cog = Metacog("debugar memory leak")
        cog.update(confidence=0.4, reason="problema complexo, pouca info")
        decision = cog.decide()
        # decision.action = CogAction.ASK_HELP
    """

    # Limiares configuráveis
    LOW_CONFIDENCE = 0.3
    HIGH_CONFIDENCE = 0.8
    HIGH_UNCERTAINTY = 0.7
    HIGH_COMPLEXITY = 0.8
    FATIGUE_THRESHOLD = 5  # número de iterações antes de sugerir parar
    STUCK_THRESHOLD = 3    # iterações sem progresso

    def __init__(self, task: str, audience: str = "geral"):
        self.task = task
        self.audience = audience  # iniciante, intermediário, avançado, geral

        # Estado cognitivo
        self.confidence: float = 0.5
        self.uncertainty: float = 0.5
        self.complexity: float = 0.5
        self.fatigue: int = 0
        self.mode: CogMode = CogMode.EXPLORING

        # Rastreamento
        self.knowledge_gaps: list[str] = []
        self.assumptions: list[str] = []
        self.progress_markers: list[str] = []
        self.events: list[CogEvent] = []
        self.iterations: int = 0
        self.stuck_count: int = 0
        self.last_confidence: float = 0.5

        # Histórico de decisões
        self.decisions: list[CogDecision] = []

        self._log_event("init", f"Iniciando raciocínio: {task}")

    # ── API Principal ──────────────────────────────────────────────

    def update(
        self,
        confidence: Optional[float] = None,
        uncertainty: Optional[float] = None,
        complexity: Optional[float] = None,
        reason: str = "",
    ):
        """
        Atualiza o estado cognitivo.

        Args:
            confidence: nova confiança [0.0, 1.0]
            uncertainty: nova incerteza [0.0, 1.0]
            complexity: nova complexidade percebida [0.0, 1.0]
            reason: motivo da atualização (para log)
        """
        old_conf = self.confidence

        if confidence is not None:
            self.confidence = max(0.0, min(1.0, confidence))
        if uncertainty is not None:
            self.uncertainty = max(0.0, min(1.0, uncertainty))
        if complexity is not None:
            self.complexity = max(0.0, min(1.0, complexity))

        self.iterations += 1
        self.fatigue += 1

        # Detectar se está travado (confiança não muda)
        if abs(self.confidence - self.last_confidence) < 0.05:
            self.stuck_count += 1
        else:
            self.stuck_count = 0

        self.last_confidence = self.confidence

        # Atualizar modo automaticamente
        self._update_mode()

        self._log_event(
            "update",
            reason or f"confiança: {old_conf:.2f} → {self.confidence:.2f}",
            confidence_before=old_conf,
            confidence_after=self.confidence,
        )

    def add_knowledge_gap(self, gap: str):
        """Registra uma lacuna de conhecimento detectada."""
        self.knowledge_gaps.append(gap)
        self._log_event("knowledge_gap", f"Lacuna: {gap}")

    def add_assumption(self, assumption: str):
        """Registra uma suposição feita durante o raciocínio."""
        self.assumptions.append(assumption)
        self._log_event("assumption", f"Suposição: {assumption}")

    def add_progress(self, marker: str):
        """Registra um marco de progresso."""
        self.progress_markers.append(marker)
        self.stuck_count = 0  # Reset stuck counter
        self._log_event("progress", f"Progresso: {marker}")

    def decide(self) -> CogDecision:
        """
        Toma uma decisão metacognitiva baseada no estado atual.

        Retorna CogDecision com a ação recomendada e justificativa.

        Lógica de decisão:
          1. Se travado há muito tempo → pedir ajuda ou explorar alternativa
          2. Se confiança muito baixa → pedir ajuda
          3. Se incerteza alta → verificar antes de concluir
          4. Se fadiga alta → parar ou simplificar
          5. Se confiança alta e incerteza baixa → concluir
          6. Se complexidade alta e público iniciante → simplificar
          7. Se público avançado e resposta superficial → aprofundar
          8. Caso contrário → continuar refinando
        """
        # 1. Travado
        if self.stuck_count >= self.STUCK_THRESHOLD:
            self.mode = CogMode.STUCK
            if self.stuck_count >= self.STUCK_THRESHOLD * 2:
                decision = CogDecision(
                    action=CogAction.ASK_HELP,
                    reason=f"Travado há {self.stuck_count} iterações sem progresso.",
                    confidence=self.confidence,
                    suggestions=[
                        "Reformular o problema",
                        "Buscar informação externa",
                        "Pedir contexto adicional ao usuário",
                        "Tentar abordagem completamente diferente",
                    ],
                )
            else:
                decision = CogDecision(
                    action=CogAction.EXPLORE_ALT,
                    reason=f"Sem progresso há {self.stuck_count} iterações.",
                    confidence=self.confidence,
                    suggestions=[
                        "Mudar perspectiva",
                        "Tentar analogia diferente",
                        "Decompor em subproblemas menores",
                    ],
                )
            self.decisions.append(decision)
            return decision

        # 2. Confiança muito baixa
        if self.confidence < self.LOW_CONFIDENCE:
            if self.knowledge_gaps:
                gaps_str = "; ".join(self.knowledge_gaps[:3])
                decision = CogDecision(
                    action=CogAction.ASK_HELP,
                    reason=f"Confiança baixa ({self.confidence:.2f}) com lacunas: {gaps_str}",
                    confidence=self.confidence,
                    suggestions=[
                        "Pesquisar tópicos desconhecidos",
                        "Pedir exemplos ou contexto",
                        "Admitir limitação ao usuário",
                    ],
                )
            else:
                decision = CogDecision(
                    action=CogAction.VERIFY,
                    reason=f"Confiança baixa ({self.confidence:.2f}) — verificar antes de prosseguir.",
                    confidence=self.confidence,
                    suggestions=[
                        "Checar fatos e suposições",
                        "Buscar contraexemplos",
                        "Testar com exemplo concreto",
                    ],
                )
            self.decisions.append(decision)
            return decision

        # 3. Incerteza alta
        if self.uncertainty > self.HIGH_UNCERTAINTY:
            decision = CogDecision(
                action=CogAction.VERIFY,
                reason=f"Incerteza alta ({self.uncertainty:.2f}) — validar antes de concluir.",
                confidence=self.confidence,
                suggestions=[
                    "Listar o que é certeza vs. suposição",
                    "Buscar validação externa",
                    "Adicionar disclaimers na resposta",
                ],
            )
            self.decisions.append(decision)
            return decision

        # 4. Fadiga alta
        if self.fatigue >= self.FATIGUE_THRESHOLD:
            if self.confidence >= self.HIGH_CONFIDENCE:
                decision = CogDecision(
                    action=CogAction.STOP,
                    reason=f"Fadiga alta ({self.fatigue} iterações) mas confiança suficiente ({self.confidence:.2f}).",
                    confidence=self.confidence,
                    suggestions=[
                        "Concluir com o que tem",
                        "Marcar pontos para revisão futura",
                    ],
                )
            else:
                decision = CogDecision(
                    action=CogAction.SIMPLIFY,
                    reason=f"Fadiga alta ({self.fatigue} iterações) e confiança ainda baixa.",
                    confidence=self.confidence,
                    suggestions=[
                        "Simplificar a resposta",
                        "Focar no essencial",
                        "Adicionar nota sobre limitações",
                    ],
                )
            self.decisions.append(decision)
            return decision

        # 5. Confiança alta e incerteza baixa → concluir
        if self.confidence >= self.HIGH_CONFIDENCE and self.uncertainty < 0.4:
            self.mode = CogMode.CONCLUDING
            decision = CogDecision(
                action=CogAction.STOP,
                reason=f"Confiança alta ({self.confidence:.2f}) e incerteza baixa ({self.uncertainty:.2f}) — resposta pronta.",
                confidence=self.confidence,
                suggestions=["Finalizar e apresentar resposta."],
            )
            self.decisions.append(decision)
            return decision

        # 6. Complexidade alta + público iniciante → simplificar
        if self.complexity > 0.6 and self.audience in ("iniciante", "geral"):
            decision = CogDecision(
                action=CogAction.SIMPLIFY,
                reason=f"Problema complexo ({self.complexity:.2f}) para público {self.audience}.",
                confidence=self.confidence,
                suggestions=[
                    "Usar analogias",
                    "Evitar jargão técnico",
                    "Dividir em partes menores",
                    "Dar exemplos concretos",
                ],
            )
            self.decisions.append(decision)
            return decision

        # 7. Público avançado + resposta superficial → aprofundar
        if self.audience == "avancado" and self.complexity < 0.4 and self.confidence > 0.6:
            decision = CogDecision(
                action=CogAction.DEEPER,
                reason=f"Público avançado pode receber mais detalhe.",
                confidence=self.confidence,
                suggestions=[
                    "Adicionar detalhes de implementação",
                    "Mencionar edge cases",
                    "Incluir referências e trade-offs",
                ],
            )
            self.decisions.append(decision)
            return decision

        # 8. Padrão: continuar refinando
        self.mode = CogMode.REFINING
        decision = CogDecision(
            action=CogAction.CONTINUE,
            reason=f"Continuando refinamento (confiança: {self.confidence:.2f}, incerteza: {self.uncertainty:.2f}).",
            confidence=self.confidence,
            suggestions=[
                "Próximo passo lógico do raciocínio",
                "Verificar consistência interna",
            ],
        )
        self.decisions.append(decision)
        return decision

    def status(self) -> str:
        """Retorna resumo do estado metacognitivo atual."""
        mode_icons = {
            CogMode.EXPLORING: "🔍",
            CogMode.REFINING: "⚙️",
            CogMode.CONCLUDING: "✅",
            CogMode.STUCK: "🚫",
            CogMode.ASKING: "🙋",
        }
        icon = mode_icons.get(self.mode, "?")

        conf_bar = "█" * int(self.confidence * 10) + "░" * (10 - int(self.confidence * 10))
        unc_bar = "█" * int(self.uncertainty * 10) + "░" * (10 - int(self.uncertainty * 10))
        comp_bar = "█" * int(self.complexity * 10) + "░" * (10 - int(self.complexity * 10))

        lines = [
            f"🧠 Metacog Status — {icon} {self.mode.value.upper()}",
            f"   Tarefa: {self.task}",
            f"   Público: {self.audience}",
            f"   Iterações: {self.iterations} | Fadiga: {self.fatigue} | Travado: {self.stuck_count}",
            f"   Confiança:  [{conf_bar}] {self.confidence:.2f}",
            f"   Incerteza:  [{unc_bar}] {self.uncertainty:.2f}",
            f"   Complexidade: [{comp_bar}] {self.complexity:.2f}",
        ]

        if self.knowledge_gaps:
            lines.append(f"   Lacunas ({len(self.knowledge_gaps)}):")
            for gap in self.knowledge_gaps[:3]:
                lines.append(f"     • {gap}")

        if self.assumptions:
            lines.append(f"   Suposições ({len(self.assumptions)}):")
            for asm in self.assumptions[:3]:
                lines.append(f"     • {asm}")

        if self.progress_markers:
            lines.append(f"   Progresso:")
            for m in self.progress_markers[-3:]:
                lines.append(f"     ✓ {m}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "audience": self.audience,
            "state": {
                "confidence": round(self.confidence, 3),
                "uncertainty": round(self.uncertainty, 3),
                "complexity": round(self.complexity, 3),
                "fatigue": self.fatigue,
                "mode": self.mode.value,
                "iterations": self.iterations,
                "stuck_count": self.stuck_count,
            },
            "knowledge_gaps": self.knowledge_gaps,
            "assumptions": self.assumptions,
            "progress_markers": self.progress_markers,
            "decisions_count": len(self.decisions),
            "events_count": len(self.events),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def get_decision_history(self) -> list[CogDecision]:
        """Retorna histórico de decisões."""
        return list(self.decisions)

    def reset_fatigue(self):
        """Reseta contador de fadiga (ex: após pausa ou mudança de abordagem)."""
        self.fatigue = 0
        self._log_event("reset_fatigue", "Fadiga resetada")

    # ── Internos ───────────────────────────────────────────────────

    def _update_mode(self):
        """Atualiza modo cognitivo baseado no estado."""
        if self.stuck_count >= self.STUCK_THRESHOLD:
            self.mode = CogMode.STUCK
        elif self.confidence >= self.HIGH_CONFIDENCE and self.uncertainty < 0.4:
            self.mode = CogMode.CONCLUDING
        elif self.confidence > 0.5:
            self.mode = CogMode.REFINING
        else:
            self.mode = CogMode.EXPLORING

    def _log_event(self, event_type: str, description: str,
                   confidence_before: float = 0.5, confidence_after: float = 0.5):
        self.events.append(CogEvent(
            event_type=event_type,
            description=description,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            mode=self.mode.value,
        ))


# ── Função de conveniência ──────────────────────────────────────────

def should_i_ask_for_help(task: str, confidence: float, iterations: int = 0) -> bool:
    """Função rápida: devo pedir ajuda?"""
    cog = Metacog(task)
    cog.confidence = confidence
    cog.iterations = iterations
    cog.fatigue = iterations
    decision = cog.decide()
    return decision.action in (CogAction.ASK_HELP, CogAction.EXPLORE_ALT)


def should_i_simplify(task: str, audience: str, complexity: float) -> bool:
    """Função rápida: devo simplificar?"""
    cog = Metacog(task, audience=audience)
    cog.complexity = complexity
    decision = cog.decide()
    return decision.action == CogAction.SIMPLIFY


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("=== Metacog Engine Demo ===\n")

        # Cenário 1: problema difícil, confiança baixa
        print("--- Cenário 1: Bug complexo, pouca info ---")
        cog = Metacog("Debugar memory leak em produção", audience="avancado")
        cog.update(confidence=0.25, uncertainty=0.8, complexity=0.9,
                   reason="Pouca informação sobre o ambiente")
        cog.add_knowledge_gap("Não conheço a stack específica")
        cog.add_knowledge_gap("Sem acesso aos logs completos")
        cog.add_assumption("Pode ser leak no pool de conexões")

        print(cog.status())
        print()
        decision = cog.decide()
        print(decision)
        print()

        # Cenário 2: progresso gradual
        print("--- Cenário 2: Progresso gradual ---")
        cog2 = Metacog("Explicar recursão para iniciante", audience="iniciante")
        cog2.update(confidence=0.6, uncertainty=0.4, complexity=0.5,
                    reason="Conheço bem o conceito")
        cog2.add_progress("Entendi o público-alvo")
        cog2.add_progress("Escolhi analogia de bonecas russas")

        # Simular iterações
        for i in range(3):
            cog2.update(confidence=0.6 + i * 0.1, uncertainty=0.4 - i * 0.1,
                        reason=f"Iteração {i + 1}: refinando explicação")
            cog2.add_progress(f"Passo {i + 1} completo")

        print(cog2.status())
        print()
        decision2 = cog2.decide()
        print(decision2)
        print()

        # Cenário 3: travado
        print("--- Cenário 3: Travado ---")
        cog3 = Metacog("Otimizar query SQL complexa", audience="intermediario")
        for i in range(5):
            cog3.update(confidence=0.45, uncertainty=0.6,
                        reason=f"Tentativa {i + 1} sem progresso")

        print(cog3.status())
        print()
        decision3 = cog3.decide()
        print(decision3)
        print()

        # JSON output
        print("--- JSON (cenário 1) ---")
        print(cog.to_json())

    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Uso: python metacog_engine.py [--demo|--help]")
    else:
        print("Metacog Engine v1.0")
        print("Importe: from metacog_engine import Metacog, should_i_ask_for_help")
