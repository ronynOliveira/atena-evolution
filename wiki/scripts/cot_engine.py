#!/usr/bin/env python3
"""
cot_engine.py — Chain of Thought Engine para o Koldi

Implementa raciocínio em árvore (não linear) com:
- Decomposição de problemas em sub-pontos
- Avaliação de confiança por ramo
- Seleção do melhor caminho
- Registro do processo para auditoria
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class Confidence(Enum):
    CERTO = "certo"
    PROVAVEL = "provavel"
    INCERTO = "incerto"
    CHUTE = "chute"


@dataclass
class ThoughtNode:
    """Um nó na árvore de raciocínio."""
    id: str
    content: str
    confidence: Confidence = Confidence.INCERTO
    children: list = field(default_factory=list)
    parent_id: Optional[str] = None
    is_solution: bool = False
    metadata: dict = field(default_factory=dict)

    def add_child(self, content: str, confidence: Confidence = Confidence.INCERTO) -> 'ThoughtNode':
        child_id = hashlib.md5(f"{self.id}:{content}:{time.time()}".encode()).hexdigest()[:8]
        child = ThoughtNode(id=child_id, content=content, confidence=confidence, parent_id=self.id)
        self.children.append(child)
        return child

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "confidence": self.confidence.value,
            "is_solution": self.is_solution,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class CoTResult:
    """Resultado de uma sessão de Chain of Thought."""
    problem: str
    root: ThoughtNode
    best_path: list = field(default_factory=list)
    conclusion: str = ""
    confidence: Confidence = Confidence.INCERTO
    reasoning_time: float = 0.0
    branches_explored: int = 0

    def to_dict(self) -> dict:
        return {
            "problem": self.problem,
            "conclusion": self.conclusion,
            "confidence": self.confidence.value,
            "reasoning_time_s": round(self.reasoning_time, 2),
            "branches_explored": self.branches_explored,
            "tree": self.root.to_dict(),
            "best_path": [n.content for n in self.best_path],
        }


class CoTEngine:
    """
    Chain of Thought com árvore de raciocínio.

    Uso:
        engine = CoTEngine()
        result = engine.reason(
            problem="Como implementar X?",
            max_depth=3,
            max_branches=4
        )
        print(result.conclusion)
    """

    def __init__(self, save_dir: Optional[str] = None):
        self.save_dir = Path(save_dir) if save_dir else Path.home() / ".hermes" / "cot_cache"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._session_log: list = []

    def reason(
        self,
        problem: str,
        context: str = "",
        max_depth: int = 3,
        max_branches: int = 4,
        save: bool = True,
    ) -> CoTResult:
        """
        Executa Chain of Thought sobre um problema.

        Na prática, este engine estrutura o raciocínio para que o LLM
        preencha os nós. O engine gerencia a árvore e seleciona o melhor caminho.
        """
        start = time.time()
        root_id = hashlib.md5(f"{problem}:{time.time()}".encode()).hexdigest()[:8]
        root = ThoughtNode(id=root_id, content=problem)

        # Estrutura o problema em sub-pontos (decomposição)
        sub_problems = self._decompose(problem, context, max_branches)

        branches_explored = 0
        best_path = []
        best_confidence = Confidence.CHUTE
        conclusion = ""

        for sub in sub_problems:
            if branches_explored >= max_branches:
                break

            child = root.add_child(sub["question"], Confidence(sub.get("confidence", "incerto")))
            branches_explored += 1

            # Explora sub-profundidade
            self._explore(child, sub.get("analysis", ""), max_depth - 1, 2)

            # Avalia se é solução
            if sub.get("is_solution", False):
                child.is_solution = True
                if self._confidence_rank(child.confidence) > self._confidence_rank(best_confidence):
                    best_confidence = child.confidence
                    best_path = self._get_path(child)
                    conclusion = sub.get("answer", child.content)

        # Se nenhuma solução clara, pega o melhor ramo
        if not conclusion and root.children:
            best = max(root.children, key=lambda c: self._confidence_rank(c.confidence))
            best_path = self._get_path(best)
            conclusion = f"Melhor abordagem identificada: {best.content} (confiança: {best.confidence.value})"

        elapsed = time.time() - start

        result = CoTResult(
            problem=problem,
            root=root,
            best_path=best_path,
            conclusion=conclusion,
            confidence=best_confidence,
            reasoning_time=elapsed,
            branches_explored=branches_explored,
        )

        if save:
            self._save(result)

        return result

    def _decompose(self, problem: str, context: str, max_branches: int) -> list:
        """
        Decompõe um problema em sub-pontos.
        Na integração real com LLM, isto seria um call ao modelo.
        Aqui retornamos a estrutura para o LLM preencher.
        """
        return [
            {
                "question": f"Qual o objetivo principal de: {problem}?",
                "analysis": "Decomposição do objetivo",
                "confidence": "provavel",
                "is_solution": False,
            },
            {
                "question": "Quais são os sub-problemas independentes?",
                "analysis": "Decomposição em partes",
                "confidence": "provavel",
                "is_solution": False,
            },
            {
                "question": "Qual a abordagem mais direta?",
                "analysis": "Solução direta",
                "confidence": "incerto",
                "is_solution": True,
                "answer": "A ser determinado pelo LLM",
            },
            {
                "question": "Quais são os riscos e limitações?",
                "analysis": "Análise de riscos",
                "confidence": "incerto",
                "is_solution": False,
            },
        ][:max_branches]

    def _explore(self, node: ThoughtNode, analysis: str, depth: int, max_children: int):
        """Explora um ramo até a profundidade máxima."""
        if depth <= 0:
            return

        # Simula sub-análises (na integração real, o LLM preencheria)
        sub_analyses = [
            f"Análise detalhada de: {node.content[:50]}...",
            f"Alternativa para: {node.content[:50]}...",
        ][:max_children]

        for sa in sub_analyses:
            child = node.add_child(sa, Confidence.INCERTO)
            self._explore(child, sa, depth - 1, max_children)

    def _confidence_rank(self, c: Confidence) -> int:
        return {"chute": 0, "incerto": 1, "provavel": 2, "certo": 3}.get(c.value, 0)

    def _get_path(self, node: ThoughtNode) -> list:
        """Retorna o caminho da raiz até este nó."""
        path = [node]
        current = node
        while current.parent_id:
            # Simplificado — na versão real, buscaria o pai na árvore
            break
        return list(reversed(path))

    def _save(self, result: CoTResult):
        """Salva resultado para auditoria e aprendizado."""
        ts = int(time.time())
        f = self.save_dir / f"cot_{ts}.json"
        f.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def get_history(self, limit: int = 10) -> list:
        """Retorna histórico de sessões CoT."""
        files = sorted(self.save_dir.glob("cot_*.json"), reverse=True)[:limit]
        return [json.loads(f.read_text(encoding="utf-8")) for f in files]


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    import sys

    if len(sys.argv) < 2:
        print("Uso: cot_engine.py <comando> [args]")
        print("Comandos:")
        print("  reason <problema>     — Executa Chain of Thought")
        print("  history [n]           — Mostra histórico")
        print("  demo                  — Executa demonstração")
        sys.exit(1)

    engine = CoTEngine()
    cmd = sys.argv[1]

    if cmd == "reason":
        problem = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Problema de demonstração"
        result = engine.reason(problem)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    elif cmd == "history":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        history = engine.get_history(n)
        for h in history:
            print(f"[{h.get('reasoning_time_s', '?')}s] {h['problem'][:80]}")
            print(f"  → {h['conclusion'][:120]}")
            print()

    elif cmd == "demo":
        print("=== CoT Engine Demo ===\n")
        result = engine.reason(
            problem="Como melhorar a segurança do plugin koldi-browser?",
            context="Plugin de navegador com Kimi WebBridge e Chrome CDP",
            max_depth=2,
            max_branches=3,
        )
        print(f"Problema: {result.problem}")
        print(f"Conclusão: {result.conclusion}")
        print(f"Confiança: {result.confidence.value}")
        print(f"Ramos explorados: {result.branches_explored}")
        print(f"Tempo: {result.reasoning_time:.2f}s")
        print(f"\nÁrvore de raciocínio:")
        _print_tree(result.root, indent=0)

    else:
        print(f"Comando desconhecido: {cmd}")


def _print_tree(node: ThoughtNode, indent: int = 0):
    prefix = "  " * indent + ("├─ " if indent > 0 else "")
    marker = " ★" if node.is_solution else ""
    print(f"{prefix}[{node.confidence.value}] {node.content[:80]}{marker}")
    for child in node.children:
        _print_tree(child, indent + 1)


if __name__ == "__main__":
    main()
