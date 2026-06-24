#!/usr/bin/env python3
"""
reflection_engine.py — Auto-crítica após cada resposta.

Verifica consistência, completude e segurança da resposta gerada.
Gera um relatório de reflexão que pode ser usado para melhorar
a resposta ou sinalizar problemas.

Critérios avaliados:
  - Consistência: a resposta contradiz a si mesma?
  - Completude: todos os aspectos da pergunta foram cobertos?
  - Segurança: a resposta contém conselhos perigosos ou imprecisos?
  - Clareza: a resposta é compreensível?
  - Ação: a resposta é acionável?

Uso:
  from reflection_engine import reflect
  report = reflect(pergunta, resposta)
  if not report["passed"]:
      print("Revisar:", report["issues"])
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Severity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class CheckType(Enum):
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    SAFETY = "safety"
    CLARITY = "clarity"
    ACTIONABILITY = "actionability"


@dataclass
class ReflectionIssue:
    check: CheckType
    severity: Severity
    message: str
    suggestion: str = ""
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "check": self.check.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
        }


@dataclass
class ReflectionReport:
    question: str
    answer: str
    issues: list[ReflectionIssue] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    overall_score: float = 0.0  # 0.0 a 1.0
    passed: bool = True

    def add(self, check: CheckType, severity: Severity, message: str,
            suggestion: str = "", evidence: str = ""):
        self.issues.append(ReflectionIssue(
            check=check, severity=severity,
            message=message, suggestion=suggestion, evidence=evidence,
        ))

    def compute_score(self) -> float:
        if not self.issues:
            self.overall_score = 1.0
            self.passed = True
            return 1.0

        penalty = 0.0
        for issue in self.issues:
            if issue.severity == Severity.CRITICAL:
                penalty += 0.35
            elif issue.severity == Severity.WARNING:
                penalty += 0.15
            elif issue.severity == Severity.INFO:
                penalty += 0.05

        self.overall_score = max(0.0, 1.0 - penalty)
        self.passed = not any(i.severity == Severity.CRITICAL for i in self.issues)
        return self.overall_score

    def summary(self) -> str:
        self.compute_score()
        status = "✅ PASSOU" if self.passed else "❌ FALHOU"
        lines = [
            f"🔍 Reflection Report — {status} (score: {self.overall_score:.2f})",
            f"   Pergunta: {self.question[:80]}...",
            f"   Resposta: {len(self.answer)} chars",
        ]
        if self.issues:
            lines.append(f"   Issues ({len(self.issues)}):")
            for issue in self.issues:
                icon = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}[issue.severity.value]
                lines.append(f"     {icon} [{issue.check.value}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"        → {issue.suggestion}")
        else:
            lines.append("   Nenhum problema detectado.")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        self.compute_score()
        return {
            "question": self.question[:200],
            "answer_length": len(self.answer),
            "overall_score": round(self.overall_score, 3),
            "passed": self.passed,
            "timestamp": self.timestamp,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ── Checkers individuais ────────────────────────────────────────────

class ConsistencyChecker:
    """Verifica se a resposta não contradiz a si mesma."""

    # Palavras que indicam contradição
    CONTRAST_MARKERS = [
        "porém", "contudo", "entretanto", "mas", "no entanto",
        "por outro lado", "em contrapartida", "apesar de",
    ]

    def check(self, question: str, answer: str) -> list[ReflectionIssue]:
        issues = []
        answer_lower = answer.lower()

        # Detectar afirmações absolutas seguidas de exceções
        absolute_patterns = [
            r"\b(sempre|nunca|todos|nenhum|todo)\b.*\b(exceção|exceto|menos)\b",
            r"\b(all|never|always|every|none)\b.*\b(except|but)\b",
        ]
        for pattern in absolute_patterns:
            matches = re.findall(pattern, answer_lower, re.DOTALL)
            if matches:
                issues.append(ReflectionIssue(
                    check=CheckType.CONSISTENCY,
                    severity=Severity.WARNING,
                    message="Afirmação absoluta com exceção detectada — possível contradição.",
                    suggestion="Reformular para evitar absolutos ou esclarecer a exceção.",
                    evidence=matches[0][:100] if matches else "",
                ))

        # Detectar negações duplas confusas
        double_neg = re.findall(r"\b(não\s+\w+\s+não|nem\s+\w+\s+nem)\b", answer_lower)
        if double_neg:
            issues.append(ReflectionIssue(
                check=CheckType.CONSISTENCY,
                severity=Severity.INFO,
                message="Dupla negação detectada — pode confundir.",
                suggestion="Simplificar para afirmação positiva.",
            ))

        return issues


class CompletenessChecker:
    """Verifica se a resposta cobre todos os aspectos da pergunta."""

    # Palavras interrogativas que indicam sub-perguntas
    QUESTION_WORDS = [
        "o que", "como", "quando", "onde", "por que", "porque",
        "qual", "quais", "quem", "quanto", "quantos",
    ]

    def check(self, question: str, answer: str) -> list[ReflectionIssue]:
        issues = []

        # Contar quantas perguntas foram feitas
        question_lower = question.lower()
        num_questions = question.count("?") + question.count("？")
        if num_questions == 0:
            num_questions = 1

        # Verificar se a resposta tem seções correspondentes
        answer_sentences = re.split(r'[.!?]\s+', answer)
        answer_sentences = [s for s in answer_sentences if len(s.strip()) > 10]

        if num_questions > 1 and len(answer_sentences) < num_questions:
            issues.append(ReflectionIssue(
                check=CheckType.COMPLETENESS,
                severity=Severity.WARNING,
                message=f"Pergunta tem {num_questions} sub-perguntas mas resposta tem poucas sentenças ({len(answer_sentences)}).",
                suggestion="Verificar se todos os aspectos da pergunta foram respondidos.",
            ))

        # Detectar perguntas "como" sem passos
        if "como" in question_lower and "?" in question:
            has_steps = bool(re.search(r'\b(passo|etapa|1[.)]|[1-9][.]|primeiro|depois|em seguida)\b', answer.lower()))
            if not has_steps and len(answer) > 200:
                issues.append(ReflectionIssue(
                    check=CheckType.COMPLETENESS,
                    severity=Severity.INFO,
                    message="Pergunta 'como' sem passos sequenciais claros.",
                    suggestion="Adicionar passos numerados ou sequência lógica.",
                ))

        # Resposta muito curta para pergunta complexa
        if len(question) > 100 and len(answer) < 100:
            issues.append(ReflectionIssue(
                check=CheckType.COMPLETENESS,
                severity=Severity.WARNING,
                message="Resposta muito curta para pergunta complexa.",
                suggestion="Expandir a resposta com mais detalhes e exemplos.",
            ))

        return issues


class SafetyChecker:
    """Verifica se a resposta contém conselhos potencialmente perigosos."""

    # Padrões de risco
    RISK_PATTERNS = [
        (r"\b(rm\s+-rf|del\s+/s|format\s+c:)\b", "Comando destrutivo detectado"),
        (r"\b(drop\s+table|drop\s+database)\b", "Comando de destruição de banco de dados"),
        (r"\b(sudo\s+chmod\s+777|chmod\s+-R\s+777)\b", "Permissão perigosa (777)"),
        (r"\b(eval\s*\(|exec\s*\()\b", "Uso de eval/exec — risco de injeção"),
        (r'\b(senha\s*=\s*["\'][^"\']+["\'])\b', "Senha hardcoded detectada"),
        (r'\b(api[_-]?key\s*=\s*["\'][^"\']{8,}["\'])\b', "API key exposta no código"),
        (r"\b(desabilitar\s+(firewall|antivírus|antivirus|segurança))\b", "Sugestão de desabilitar segurança"),
        (r"\b(disable\s+(firewall|antivirus|security))\b", "Sugestão de desabilitar segurança (EN)"),
    ]

    def check(self, question: str, answer: str) -> list[ReflectionIssue]:
        issues = []
        answer_lower = answer.lower()

        for pattern, message in self.RISK_PATTERNS:
            matches = re.findall(pattern, answer_lower)
            if matches:
                issues.append(ReflectionIssue(
                    check=CheckType.SAFETY,
                    severity=Severity.CRITICAL,
                    message=message,
                    suggestion="Adicionar aviso de segurança ou sugerir alternativa segura.",
                    evidence=matches[0][:80] if matches else "",
                ))

        # Detectar conselho médico sem disclaimer
        medical_terms = ["remédio", "medicamento", "dosagem", "tratamento", "diagnóstico",
                         "prescrever", "receita médica"]
        if any(term in answer_lower for term in medical_terms):
            has_disclaimer = any(term in answer_lower for term in [
                "consulte um médico", "profissional de saúde", "não é aconselhamento médico",
                "consult a doctor", "medical advice"
            ])
            if not has_disclaimer:
                issues.append(ReflectionIssue(
                    check=CheckType.SAFETY,
                    severity=Severity.WARNING,
                    message="Conteúdo médico detectado sem disclaimer.",
                    suggestion="Adicionar: 'Consulte um profissional de saúde para orientação.'",
                ))

        return issues


class ClarityChecker:
    """Verifica clareza e legibilidade da resposta."""

    def check(self, question: str, answer: str) -> list[ReflectionIssue]:
        issues = []

        # Sentenças muito longas (> 40 palavras)
        sentences = re.split(r'[.!?]\s+', answer)
        long_sentences = [s for s in sentences if len(s.split()) > 40]
        if long_sentences:
            issues.append(ReflectionIssue(
                check=CheckType.CLARITY,
                severity=Severity.INFO,
                message=f"{len(long_sentences)} sentença(s) muito longa(s) (>40 palavras).",
                suggestion="Dividir sentenças longas em partes menores.",
            ))

        # Jargão técnico sem explicação (heurística simples)
        jargon_pattern = r'\b(API|SDK|ORM|CRUD|REST|GraphQL|WebSocket|OAuth|JWT|CI/CD|DNS|SSL|TLS)\b'
        jargon_found = re.findall(jargon_pattern, answer)
        if len(jargon_found) > 3:
            unique_jargon = set(jargon_found)
            issues.append(ReflectionIssue(
                check=CheckType.CLARITY,
                severity=Severity.INFO,
                message=f"Muitos termos técnicos sem explicação: {', '.join(unique_jargon)}.",
                suggestion="Adicionar breve explicação ou glossário para termos técnicos.",
            ))

        # Resposta sem estrutura (sem parágrafos ou listas)
        if len(answer) > 300 and "\n" not in answer:
            issues.append(ReflectionIssue(
                check=CheckType.CLARITY,
                severity=Severity.INFO,
                message="Resposta longa sem quebras de linha ou estrutura.",
                suggestion="Adicionar parágrafos, listas ou headers para melhor legibilidade.",
            ))

        return issues


class ActionabilityChecker:
    """Verifica se a resposta é acionável (pode ser posta em prática)."""

    def check(self, question: str, answer: str) -> list[ReflectionIssue]:
        issues = []
        answer_lower = answer.lower()
        question_lower = question.lower()

        # Perguntas "como" devem ter ações concretas
        if "como" in question_lower and "?" in question:
            action_indicators = [
                "passo", "etapa", "execute", "rode", "instale", "configure",
                "crie", "adicione", "remova", "altere", "modifique",
                "step", "run", "install", "create", "add", "remove",
            ]
            has_actions = any(ind in answer_lower for ind in action_indicators)
            if not has_actions:
                issues.append(ReflectionIssue(
                    check=CheckType.ACTIONABILITY,
                    severity=Severity.WARNING,
                    message="Pergunta 'como' sem ações concretas detectadas.",
                    suggestion="Incluir passos práticos e comandos específicos.",
                ))

        # Detectar respostas puramente teóricas para perguntas práticas
        if "?" in question and len(answer) > 200:
            vague_phrases = [
                "depende do contexto", "é relativo", "pode variar",
                "não há resposta certa", "é subjetivo",
            ]
            vague_count = sum(1 for p in vague_phrases if p in answer_lower)
            if vague_count >= 2:
                issues.append(ReflectionIssue(
                    check=CheckType.ACTIONABILITY,
                    severity=Severity.WARNING,
                    message="Resposta muito vaga para uma pergunta que espera orientação prática.",
                    suggestion="Adicionar exemplos concretos ou recomendações específicas.",
                ))

        return issues


# ── Motor principal ─────────────────────────────────────────────────

# Instâncias únicas dos checkers
_CONSISTENCY = ConsistencyChecker()
_COMPLETENESS = CompletenessChecker()
_SAFETY = SafetyChecker()
_CLARITY = ClarityChecker()
_ACTIONABILITY = ActionabilityChecker()

ALL_CHECKERS = [
    ("consistency", _CONSISTENCY),
    ("completeness", _COMPLETENESS),
    ("safety", _SAFETY),
    ("clarity", _CLARITY),
    ("actionability", _ACTIONABILITY),
]


def reflect(
    question: str,
    answer: str,
    checks: Optional[list[str]] = None,
) -> ReflectionReport:
    """
    Executa auto-crítica completa de uma resposta.

    Args:
        question: pergunta original
        answer: resposta gerada
        checks: lista de checks a executar (default: todos)
                Opções: consistency, completeness, safety, clarity, actionability

    Returns:
        ReflectionReport com issues e score
    """
    report = ReflectionReport(question=question, answer=answer)

    active_checks = ALL_CHECKERS
    if checks:
        active_checks = [(name, chk) for name, chk in ALL_CHECKERS if name in checks]

    for name, checker in active_checks:
        found_issues = checker.check(question, answer)
        for issue in found_issues:
            report.issues.append(issue)

    report.compute_score()
    return report


def quick_check(question: str, answer: str) -> bool:
    """Verificação rápida — retorna True se passou nos checks críticos."""
    report = reflect(question, answer, checks=["safety", "consistency"])
    return report.passed


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("=== Reflection Engine Demo ===\n")

        # Exemplo 1: resposta com problemas
        q1 = "Como configurar HTTPS no servidor Nginx?"
        a1 = """
        Para configurar HTTPS no Nginx, você deve sempre usar SSL.
        Porém, em alguns casos você pode não usar SSL.
        Execute: sudo chmod 777 /etc/nginx
        Depois reinicie o serviço.
        """

        report1 = reflect(q1, a1)
        print(report1.summary())
        print()

        # Exposta 2: resposta boa
        q2 = "O que é Python?"
        a2 = """
        Python é uma linguagem de programação de alto nível, interpretada e multi-paradigma.
        Foi criada por Guido van Rossum e lançada em 1991.

        Características principais:
        - Sintaxe simples e legível
        - Tipagem dinâmica
        - Suporte a orientação a objetos, programação funcional e imperativa
        - Grande ecossistema de bibliotecas

        É amplamente usada em desenvolvimento web, ciência de dados, automação e IA.
        """

        report2 = reflect(q2, a2)
        print(report2.summary())
        print()

        # JSON output
        print("--- JSON Report (exemplo 1) ---")
        print(report1.to_json())

    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Uso: python reflection_engine.py [--demo|--help]")
    else:
        print("Reflection Engine v1.0")
        print("Importe: from reflection_engine import reflect, quick_check")
