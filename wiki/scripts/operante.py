#!/usr/bin/env python3
"""
===============================================================
 OPERANTE.PY — Sistema de Condicionamento Operante para Agentes
===============================================================

Inspirado no behaviorismo de Skinner, este sistema implementa cinco
mecanismos fundamentais:

  1) BehaviorTracker  — registra cada ação e seu resultado
  2) ReinforcementLearning — ajusta pesos de estratégias
  3) PunishmentAvoidance — identifica padrões que levam a erros
  4) RewardSeeking — identifica padrões que levam a sucesso
  5) ExtinctionProtocol — remove comportamentos que falham

Uso:
  python operante.py track <action> <outcome> [metric]
  python operante.py report [last_n]
  python operante.py suggest <context>
  python operante.py avoid <context>
  python operante.py dashboard
  python operante.py decay [days]
  python operante.py extinguish [threshold]

Dados persistidos em: operante_data.json  (no mesmo diretório)
===============================================================
"""

import json
import os
import sys
import math
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ── Configuração de caminhos ──────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "operante_data.json"
LESSONS_FILE = SCRIPT_DIR.parent / "lessons.jsonl"

# ── Hiperparâmetros do condicionamento operante ───────────────
LR_ALPHA = 0.30          # Taxa de aprendizado (ajuste de peso)
LR_GAMMA = 0.15          # Fator de desconto para recompensas futuras
DECAY_HALFLIFE = 14      # Meia-vida dos scores (dias)
EXTINCTION_THRESHOLD = 0.08   # Peso abaixo do qual é extinto
EXTINCTION_CONSECUTIVE_FAILS = 3  # Fracassos consecutivos para extinção
MIN_SAMPLES_FOR_EXTINCTION = 5    # Mínimo de amostras antes de extinguir
PUNISHMENT_LEARNING_BOOST = 1.8   # Multiplicador de aprendizado por punição
REWARD_CONFIDENCE_MIN = 0.6       # Confiança mínima para sugerir reforço


# ═══════════════════════════════════════════════════════════════
#  DATA STORE — carregamento / persistência
# ═══════════════════════════════════════════════════════════════

def _now_iso():
    return datetime.now().isoformat(timespec="seconds")

def _default_data():
    return {
        "version": 1,
        "behaviors": {},          # action_hash → BehaviorEntry
        "avoidance_rules": [],    # PunishmentAvoidance
        "reward_patterns": [],    # RewardSeeking
        "total_tracked": 0,
        "created_at": _now_iso(),
    }

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_data()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════

def _hash(action: str, context: str = "") -> str:
    """Hash determinístico para identificar um comportamento."""
    raw = f"{action.lower().strip()}::{context.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def _parse_timestamp(ts):
    if ts is None:
        return datetime.now()
    if isinstance(ts, str):
        return datetime.fromisoformat(ts)
    return datetime.now()

def _days_since(ts):
    return (datetime.now() - _parse_timestamp(ts)).total_seconds() / 86400.0

def _decay(weight: str = None, days: float = None) -> float:
    """Decaimento exponencial baseado na meia-vida."""
    if days is None:
        days = DECAY_HALFLIFE
    return weight * (0.5 ** (days / DECAY_HALFLIFE))


# ═══════════════════════════════════════════════════════════════
#  1) BEHAVIOR TRACKER
# ═══════════════════════════════════════════════════════════════

class BehaviorTracker:
    """
    Registra cada ação executada, seu contexto, resultado e métrica.
    Mantém um histórico por comportamento identificado por hash.
    """

    OUTCOME_SCORES = {
        "success":  1.0,
        "partial":  0.3,
        "failure": -1.0,
        "error":   -1.5,
        "timeout": -0.8,
        "abort":   -0.5,
    }

    def __init__(self, data: dict):
        self.data = data

    def record(self, action: str, outcome: str, metric: float = None,
               context: str = "", strategy: str = "default") -> dict:
        """
        Registra um comportamento.

        Args:
            action:     Descrição da ação (ex: "run_tests")
            outcome:    success | partial | failure | error | timeout | abort
            metric:     Valor numérico opcional (0.0-1.0) medindo qualidade
            context:    Contexto onde a ação foi executada
            strategy:   Nome da estratégia usada

        Returns:
            dict com o registro criado
        """
        h = _hash(action, context)
        ts = _now_iso()
        score = self.OUTCOME_SCORES.get(outcome.lower(), 0.0)
        if metric is not None:
            # Mistura score do outcome com métrica contínua
            score = 0.4 * score + 0.6 * max(-1.5, min(1.5, entry.get("weight", 0.0)))
            score = round(max(-1.5, min(1.5, score)), 4)

        entry = self.data["behaviors"].get(h, {
            "action": action,
            "context": context,
            "first_seen": ts,
            "count": 0,
            "successes": 0,
            "failures": 0,
            "weight": 0.0,  # Peso condicionamento operante
            "history": [],
            "strategies": defaultdict(lambda: {"uses": 0, "score_sum": 0.0}),
        })

        entry["action"] = action
        entry["context"] = context
        entry["count"] = entry.get("count", 0) + 1
        if outcome.lower() in ("success", "partial"):
            entry["successes"] = entry.get("successes", 0) + 1
        else:
            entry["failures"] = entry.get("failures", 0) + 1

        # Converter defaultdict para dict normal se necessário
        if isinstance(entry.get("strategies"), defaultdict):
            entry["strategies"] = dict(entry["strategies"]) if entry["strategies"] else {}

        st = entry["strategies"].get(strategy, {"uses": 0, "score_sum": 0.0})
        st["uses"] += 1
        st["score_sum"] += score
        st["avg"] = round(st["score_sum"] / st["uses"], 4)
        entry["strategies"][strategy] = st

        # Peso com decaimento + atualização
        prev_weight = entry.get("weight", 0.0)
        elapsed = _days_since(entry.get("last_updated", entry.get("first_seen")))
        decayed_prev = prev_weight * (0.5 ** (max(elapsed, 0) / DECAY_HALFLIFE))
        entry["weight"] = round(decayed_prev + LR_ALPHA * score, 4)
        entry["last_updated"] = ts

        # Histórico (mantém últimas 50)
        entry["history"] = entry.get("history", [])[-49:]
        entry["history"].append({
            "ts": ts,
            "outcome": outcome,
            "metric": metric,
            "strategy": strategy,
            "score": score,
        })

        self.data["behaviors"][h] = entry
        self.data["total_tracked"] = self.data.get("total_tracked", 0) + 1
        return entry

    def get_behavior(self, h: str) -> dict:
        return self.data["behaviors"].get(h)

    def all_behaviors(self) -> dict:
        return self.data.get("behaviors", {})

    def summary(self) -> dict:
        behaviors = self.all_behaviors()
        total = len(behaviors)
        weights = [b.get("weight", 0) for b in behaviors.values()]
        avg_w = round(sum(weights) / len(weights), 4) if weights else 0
        reinforced = sum(1 for w in weights if w > 0.3)
        extinguished = sum(1 for w in weights if w < EXTINCTION_THRESHOLD)
        return total, avg_w, reinforced, extinguished


# ═══════════════════════════════════════════════════════════════
#  2) REINFORCEMENT LEARNING (ajuste de pesos)
# ═══════════════════════════════════════════════════════════════

class ReinforcementLearning:
    """
    Ajusta pesos de estratégias baseado em resultados passados.
    Usa Q-learning simplificado: Q(s,a) += α * (r + γ*maxQ(s') - Q(s,a))
    """

    def __init__(self, data: dict, tracker: BehaviorTracker):
        self.data = data
        self.tracker = tracker

    def update(self, behavior_hash: str):
        """Atualiza o peso de um comportamento após observação de resultado."""
        entry = self.tracker.get_behavior(behavior_hash)
        if not entry:
            return

        history = entry.get("history", [])
        if len(history) < 1:
            return

        # Usa os últimos fatos para calcular recompensa futura estimada
        r = history[-1].get("score", 0)

        # max Q(s') — média dos scores de estrategias similares no histórico
        future_scores = [h.get("score", 0) for h in history[-5:] if h != history[-1]]
        max_q_future = max(future_scores) if future_scores else 0

        q_current = entry.get("weight", 0)
        new_q = q_current + LR_ALPHA * (r + LR_GAMMA * max_q_future - q_current)
        entry["weight"] = round(max(-2.0, min(2.0, new_q)), 4)
        entry["q_value"] = entry["weight"]  # compatibilidade

    def rank_strategies(self, action: str, context: str = "") -> list:
        """Ranqueia estratégias por comportamento / contexto."""
        h = _hash(action, context)
        entry = self.tracker.get_behavior(h)
        if not entry:
            return []
        strategies = entry.get("strategies", {})
        ranked = sorted(strategies.items(), key=lambda x: x[1].get("avg", 0), reverse=True)
        return ranked


# ═══════════════════════════════════════════════════════════════
#  3) PUNISHMENT AVOIDANCE
# ═══════════════════════════════════════════════════════════════

class PunishmentAvoidance:
    """
    Identifica padrões que levam a erros e cria regras de evitação.
    Detecta: sequências str(timeout, timeout, timeout) → regra
    """

    def __init__(self, data: dict, tracker: BehaviorTracker):
        self.data = data
        self.tracker = tracker

    def analyze(self) -> list:
        """
        Analisa o histórico de comportamentos e gera regras de evitação.
        Retorna lista de regras criadas.
        """
        new_rules = []
        behaviors = self.tracker.all_behaviors()

        for h, entry in behaviors.items():
            history = entry.get("history", [])
            if len(history) < 3:
                continue

            # Detecta streak de fracassos recentes
            recent = history[-EXTINCTION_CONSECUTIVE_FAILS:]
            fails = [h_ for h_ in recent if h_.get("outcome") in ("failure", "error", "timeout")]
            if len(fails) >= EXTINCTION_CONSECUTIVE_FAILS:
                rule = {
                    "id": f"avoid_{h}",
                    "action": entry["action"],
                    "context": entry.get("context", ""),
                    "reason": f"{EXTINCTION_CONSECUTIVE_FAILS}+ fracassos consecutivos",
                    "created_at": _now_iso(),
                    "active": True,
                    "weight_delta": round(
                        PUNISHMENT_LEARNING_BOOST * abs(entry.get("weight", 0)), 4
                    ),
                }
                # Apenas cria se não existe regra idêntica
                existing = [r for r in self.data.get("avoidance_rules", [])
                           if r["id"] == rule["id"] and r.get("active")]
                if not existing:
                    self.data.setdefault("avoidance_rules", []).append(rule)
                    new_rules.append(rule)

            # Detecta contextos específicos que falham
            strategies_bad = entry.get("strategies", {})
            for strat, stats in strategies_bad.items():
                if stats.get("uses", 0) >= 3 and stats.get("avg", 0) < -0.4:
                    rule_id = f"avoid_{h}_strat_{strat}"
                    existing = [r for r in self.data.get("avoidance_rules", [])
                               if r["id"] == rule_id and r.get("active")]
                    if not existing:
                        rule = {
                            "id": rule_id,
                            "action": entry["action"],
                            "context": entry.get("context", ""),
                            "reason": f"Estratégia '{strat}' com avg {stats['avg']} < -0.4",
                            "created_at": _now_iso(),
                            "active": True,
                            "weight_delta": round(
                                PUNISHMENT_LEARNING_BOOST * abs(stats["avg"]), 4
                            ),
                        }
                        self.data["avoidance_rules"].append(rule)
                        new_rules.append(rule)

        return new_rules

    def get_active_rules(self) -> list:
        return [r for r in self.data.get("avoidance_rules", []) if r.get("active")]

    def check(self, action: str, context: str = "") -> list:
        """Verifica se uma ação+contexto corresponde a alguma regra de evitação."""
        active = self.get_active_rules()
        hits = []
        for rule in active:
            action_match = rule["action"].lower() in action.lower() or action.lower() in rule["action"].lower()
            ctx_match = (not rule.get("context") or
                        rule["context"].lower() in context.lower() or
                        context.lower() in rule["context"].lower())
            if action_match and ctx_match:
                hits.append(rule)
        return hits

    def deactivate_rule(self, rule_id: str):
        for r in self.data.get("avoidance_rules", []):
            if r["id"] == rule_id:
                r["active"] = False
                r["deactivated_at"] = _now_iso()


# ═══════════════════════════════════════════════════════════════
#  4) REWARD SEEKING
# ═══════════════════════════════════════════════════════════════

class RewardSeeking:
    """
    Identifica padrões que levam a sucesso e reforça estratégias.
    """

    def __init__(self, data: dict, tracker: BehaviorTracker):
        self.data = data
        self.tracker = tracker

    def find_patterns(self) -> list:
        """Identifica comportamentos com peso alto e gera reforços."""
        patterns = []
        behaviors = self.tracker.all_behaviors()

        for h, entry in behaviors.items():
            if entry.get("weight", 0) <= 0.3:
                continue
            if entry.get("count", 0) < 3:
                continue

            # Confiança proporcional a log(count)
            confidence = min(1.0, math.log(entry["count"] + 1) / math.log(20))
            if confidence < REWARD_CONFIDENCE_MIN:
                continue

            # Identifica a melhor estratégia
            strategies = entry.get("strategies", {})
            best_strat = max(strategies.items(), key=lambda x: x[1].get("avg", 0), default=(None, {}))

            pattern = {
                "id": f"reward_{h}",
                "action": entry["action"],
                "context": entry.get("context", ""),
                "weight": entry["weight"],
                "confidence": round(confidence, 3),
                "best_strategy": best_strat[0] if best_strat[0] else "default",
                "success_rate": round(
                    entry.get("successes", 0) / max(entry.get("count", 1), 1), 3
                ),
                "created_at": _now_iso(),
                "active": True,
            }

            existing_ids = {p["id"]: i for i, p in enumerate(self.data.get("reward_patterns", []))}
            if pattern["id"] in existing_ids:
                idx = existing_ids[pattern["id"]]
                old = self.data["reward_patterns"][idx]
                if old.get("weight", 0) <= pattern["weight"]:
                    self.data["reward_patterns"][idx] = pattern
            else:
                self.data.setdefault("reward_patterns", []).append(pattern)
            patterns.append(pattern)

        return patterns

    def get_top_patterns(self, n: int = 10) -> list:
        patterns = [p for p in self.data.get("reward_patterns", []) if p.get("active")]
        patterns.sort(key=lambda x: x.get("weight", 0) * x.get("confidence", 0), reverse=True)
        return patterns[:n]

    def suggest_strategy(self, action: str, context: str = "") -> str:
        """Sugere a melhor estratégia conhecida para uma ação+contexto."""
        h = _hash(action, context)
        entry = self.tracker.get_behavior(h)
        if not entry or not entry.get("strategies"):
            return None
        ranked = sorted(
            entry["strategies"].items(),
            key=lambda x: x[1].get("avg", 0),
            reverse=True
        )
        if ranked and ranked[0][1].get("avg", 0) > 0:
            return ranked[0][0]
        return None


# ═══════════════════════════════════════════════════════════════
#  5) EXTINCTION PROTOCOL
# ═══════════════════════════════════════════════════════════════

class ExtinctionProtocol:
    """
    Remove comportamentos que consistentemente falham.
    - Peso muito baixo após amostras suficientes
    - Fracassos consecutivos
    - Nunca usado nos últimos N dias
    """

    def __init__(self, data: dict, tracker: BehaviorTracker):
        self.data = data
        self.tracker = tracker
        self.extinguished = []

    def evaluate(self, threshold: float = None) -> list:
        """
        Avalia comportamentos para possível extinção.
        Retorna lista de comportamentos extintos (ou marcados para).
        """
        if threshold is None:
            threshold = EXTINCTION_THRESHOLD
        self.extinguished = []
        behaviors = self.tracker.all_behaviors()

        for h, entry in behaviors.items():
            count = entry.get("count", 0)
            weight = entry.get("weight", 0)
            last = entry.get("last_updated", entry.get("first_seen"))
            history = entry.get("history", [])

            # Critério 1: peso baixo com amostras suficientes
            never_reinforced = weight < threshold and count >= MIN_SAMPLES_FOR_EXTINCTION

            # Critério 2: todos os últimos N foram fracassos
            recent = history[-MIN_SAMPLES_FOR_EXTINCTION:]
            all_failed = (len(recent) >= MIN_SAMPLES_FOR_EXTINCTION and
                         all(r.get("outcome") in ("failure", "error", "timeout") for r in recent))

            # Critério 3: peso negativo alto
            strongly_negative = weight < -1.0 and count >= 3

            should_extinguish = never_reinforced or all_failed or strongly_negative

            if should_extinguish and not entry.get("extinguished"):
                entry["extinguished"] = True
                entry["extinguished_at"] = _now_iso()
                reason = []
                if never_reinforced:
                    reason.append(f"peso {weight} < {threshold} com {count} usos")
                if all_failed:
                    reason.append(f"{MIN_SAMPLES_FOR_EXTINCTION}+ fracassos consecutivos")
                if strongly_negative:
                    reason.append(f"peso fortemente negativo ({weight})")
                entry["extinction_reason"] = "; ".join(reason)
                self.extinguished.append((h, entry))

        return self.extinguished

    def get_extinguished(self) -> list:
        return [(h, b) for h, b in self.tracker.all_behaviors().items()
                if b.get("extinguished")]

    def get_active(self) -> list:
        return [(h, b) for h, b in self.tracker.all_behaviors().items()
                if not b.get("extinguished")]


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD — visualização ASCII
# ═══════════════════════════════════════════════════════════════

class Dashboard:
    """Dashboard ASCII para visualizar condicionamento operante."""

    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

    BAR_FILLED = "█"
    BAR_EMPTY  = "░"

    def __init__(self, data, tracker, rl, pa, rs, ep):
        self.data = data
        self.tracker = tracker
        self.rl = rl
        self.pa = pa
        self.rs = rs
        self.ep = ep

    def _bar(self, value, width=20, min_val=-1.5, max_val=1.5):
        """Gera barra colorida proporcional ao valor."""
        ratio = (value - min_val) / (max_val - min_val)
        ratio = max(0, min(1, ratio))
        filled = int(ratio * width)
        if value >= 0.3:
            color = self.GREEN
        elif value <= -0.3:
            color = self.RED
        else:
            color = self.YELLOW
        bar = color + (self.BAR_FILLED * filled) + self.DIM + (self.BAR_EMPTY * (width - filled)) + self.RESET
        return bar

    def _color_value(self, v):
        if v >= 0.3:
            return f"{self.GREEN}{v:+.4f}{self.RESET}"
        elif v <= -0.3:
            return f"{self.RED}{v:+.4f}{self.RESET}"
        return f"{self.YELLOW}{v:+.4f}{self.RESET}"

    def render(self):
        os.system("")  # Ativa ANSI no Windows

        total, avg_w, reinforced, extinguished_count = self.tracker.summary()
        active_behaviors = self.ep.get_active()
        extinguished = self.ep.get_extinguished()
        top_rewards = self.rs.get_top_patterns(10)
        avoid_rules = self.pa.get_active_rules()

        # ── Cabeçalho ─────────────────────────────────────
        print()
        print(f"  {self.BOLD}{self.CYAN}╔══════════════════════════════════════════════════════════╗{self.RESET}")
        print(f"  {self.BOLD}{self.CYAN}║    🧠 PAINEL DE CONDICIONAMENTO OPERANTE — Koldi        ║{self.RESET}")
        print(f"  {self.BOLD}{self.CYAN}╚══════════════════════════════════════════════════════════╝{self.RESET}")
        print(f"  {self.DIM}  {total} comportamentos rastreados  |  "
              f"avg peso: {avg_w:+.4f}  |  "
              f"criado: {self.data.get('created_at', '?')[:10]}{self.RESET}")

        # ── Estatísticas gerais ──────────────────────────
        print(f"\n  {self.BOLD}┌─ ESTATÍSTICAS ─────────────────────────────────────┐{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}  Total rastreados:      {self.CYAN}{self.data.get('total_tracked', 0)}{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}  Comportamentos únicos:  {self.CYAN}{total}{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}  Reforçados (w>0.3):     {self.GREEN}{reinforced}{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}  Extintos (w<0.08):      {self.RED}{extinguished_count}{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}  Regras de evitação:     {self.YELLOW}{len(avoid_rules)}{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}  Padrões recompensados:  {self.GREEN}{len(top_rewards)}{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}")
        print(f"  {self.BOLD}└───────────────────────────────────────────────────┘{self.RESET}")

        # ── Comportamentos reforçados ─────────────────────
        print(f"\n  {self.BOLD}{self.GREEN}┌─ COMPORTAMENTOS REFORÇADOS (os 10 melhores) ─────────┐{self.RESET}")
        if top_rewards:
            print(f"  {self.BOLD}{self.GREEN}│{self.RESET}")
            for i, p in enumerate(top_rewards, 1):
                action_short = p["action"][:35]
                ctx = p.get("context", "")[:20]
                conf = p.get("confidence", 0)
                strat = p.get("best_strategy", "default")
                print(f"  {self.BOLD}{self.GREEN}│{self.RESET}  {i:2d}. {action_short:<35} {self._bar(p['weight'])} {self._color_value(p['weight'])}")
                print(f"  {self.BOLD}{self.GREEN}│{self.RESET}      strat={strat}  conf={conf:.2f}  ctx={ctx}")
        else:
            print(f"  {self.BOLD}{self.GREEN}│{self.RESET}  {self.DIM}Ainda não há comportamentos reforçados.{self.RESET}")
        print(f"  {self.BOLD}{self.GREEN}│{self.RESET}")
        print(f"  {self.BOLD}{self.GREEN}└───────────────────────────────────────────────────┘{self.RESET}")

        # ── Comportamentos extintos ──────────────────────
        print(f"\n  {self.BOLD}{self.RED}┌─ COMPORTAMENTOS EXTINTOS ───────────────────────────┐{self.RESET}")
        if extinguished:
            print(f"  {self.BOLD}{self.RED}│{self.RESET}")
            for h, e in extinguished:
                action_short = e["action"][:40]
                reason = e.get("extinction_reason", "")[:45]
                ext_at = e.get("extinguished_at", "")[:19]
                print(f"  {self.BOLD}{self.RED}│{self.RESET}  ✗ {action_short:<40} {self._color_value(e.get('weight', 0))}")
                print(f"  {self.BOLD}{self.RED}│{self.RESET}    {self.DIM}{reason}{self.RESET}")
                print(f"  {self.BOLD}{self.RED}│{self.RESET}    {self.DIM}extinto em {ext_at}{self.RESET}")
        else:
            print(f"  {self.BOLD}{self.RED}│{self.RESET}  {self.DIM}Nenhum comportamento extinto ainda.{self.RESET}")
        print(f"  {self.BOLD}{self.RED}│{self.RESET}")
        print(f"  {self.BOLD}{self.RED}└───────────────────────────────────────────────────┘{self.RESET}")

        # ── Regras de evitação ───────────────────────────
        print(f"\n  {self.BOLD}{self.YELLOW}┌─ REGRAS DE EVITAÇÃO (PunishmentAvoidance) ──────────┐{self.RESET}")
        if avoid_rules:
            print(f"  {self.BOLD}{self.YELLOW}│{self.RESET}")
            for r in avoid_rules[:10]:
                action_short = r["action"][:35]
                reason = r.get("reason", "")[:40]
                print(f"  {self.BOLD}{self.YELLOW}│{self.RESET}  ⚠ {action_short:<35}")
                print(f"  {self.BOLD}{self.YELLOW}│{self.RESET}    {self.DIM}{reason}{self.RESET}")
        else:
            print(f"  {self.BOLD}{self.YELLOW}│{self.RESET}  {self.DIM}Nenhuma regra de evitação ativa.{self.RESET}")
        print(f"  {self.BOLD}{self.YELLOW}│{self.RESET}")
        print(f"  {self.BOLD}{self.YELLOW}└───────────────────────────────────────────────────┘{self.RESET}")

        # ── Ranking completo por peso ────────────────────
        print(f"\n  {self.BOLD}┌─ TODOS COMPORTAMENTOS (POR PESO) ──────────────────┐{self.RESET}")
        all_b = self.tracker.all_behaviors()
        sorted_b = sorted(all_b.items(), key=lambda x: x[1].get("weight", 0), reverse=True)
        print(f"  {self.BOLD}│{self.RESET}")
        for h, e in sorted_b[:15]:
            status = f"{self.RED}[EXTINTO]{self.RESET}" if e.get("extinguished") else ""
            action_short = e["action"][:38]
            cnt = e.get("count", 0)
            w = e.get("weight", 0)
            print(f"  {self.BOLD}│{self.RESET}  {self._bar(w)} {self._color_value(w)}  {action_short:<38} n={cnt} {status}")
        if len(sorted_b) > 15:
            print(f"  {self.BOLD}│{self.RESET}  {self.DIM}... e mais {len(sorted_b) - 15} comportamentos{self.RESET}")
        print(f"  {self.BOLD}│{self.RESET}")
        print(f"  {self.BOLD}└───────────────────────────────────────────────────┘{self.RESET}")
        print()


# ═══════════════════════════════════════════════════════════════
#  CLI — interface de linha de comando
# ═══════════════════════════════════════════════════════════════

def build_systems(data):
    tracker = BehaviorTracker(data)
    rl = ReinforcementLearning(data, tracker)
    pa = PunishmentAvoidance(data, tracker)
    rs = RewardSeeking(data, tracker)
    ep = ExtinctionProtocol(data, tracker)
    dash = Dashboard(data, tracker, rl, pa, rs, ep)
    return tracker, rl, pa, rs, ep, dash


def cmd_track(args):
    """Registra um comportamento: operante.py track <action> <outcome> [metric] [context]"""
    if len(args) < 2:
        print("Uso: operante.py track <action> <outcome> [metric] [context] [strategy]")
        print("  outcome: success | partial | failure | error | timeout | abort")
        sys.exit(1)

    outcome = args[0]
    action = args[1] if len(args) > 1 else "unknown"

    # Permite args em qualquer ordem — detecta pelo dicionário de outcomes
    known_outcomes = set(BehaviorTracker.OUTCOME_SCORES.keys())
    if outcome.lower() in known_outcomes:
        action = args[1] if len(args) > 1 else "unknown"
    elif action.lower() in known_outcomes:
        outcome, action = action, outcome
    else:
        action = args[0]
        outcome = args[1] if len(args) > 1 else "partial"

    # Parse remaining args
    metric = None
    context = ""
    strategy = "default"

    remaining = args[2:] if len(args) > 2 else []
    for arg in remaining:
        try:
            metric = float(arg)
        except ValueError:
            if arg.startswith("ctx="):
                context = arg[4:]
            elif arg.startswith("strat="):
                strategy = arg[6:]
            else:
                context = context + " " + arg if context else arg

    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    # Formato mais amigável: operante.py track <action> <outcome> ...
    # Para simplificar, vamos inverter a lógica padrão:
    # operante.py track "run_tests" success
    if action.lower() in known_outcomes:
        action, outcome = args[0], args[1]

    entry = tracker.record(action=action, outcome=outcome, metric=metric,
                          context=context, strategy=strategy)
    rl.update(_hash(action, context))
    save_data(data)

    status_icon = "✅" if outcome in ("success", "partial") else "❌"
    print(f"{status_icon} Registrado: [{_hash(action, context)}] {action} → {outcome} "
          f"(peso={entry['weight']:+.4f}, n={entry['count']})")


def cmd_report(args):
    """Relatório geral: operante.py report [last_n]"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    last_n = int(args[0]) if args else 20

    print(f"\n📋 Últimos {last_n} registros:\n")
    print(f"{'ts':<22} {'hash':<12} {'action':<30} {'outcome':<10} {'score':>8} {'strategy'}")
    print("-" * 95)

    all_entries = sorted(
        tracker.all_behaviors().items(),
        key=lambda x: x[1].get("last_updated", x[1].get("first_seen", "")),
        reverse=True,
    )

    shown = 0
    for h, entry in all_entries:
        for h_ in reversed(entry.get("history", [])):
            if shown >= last_n:
                break
            ts = h_.get("ts", "")[:19]
            act = entry["action"][:30]
            out = h_.get("outcome", "")[:10]
            score = h_.get("score", 0)
            strat = h_.get("strategy", "default")
            icon = "✅" if out in ("success", "partial") else "❌"
            print(f"{ts:<22} {h:<12} {act:<30} {icon} {out:<8} {score:>+8.4f} {strat}")
            shown += 1
        if shown >= last_n:
            break


def cmd_suggest(args):
    """Sugere estratégia: operante.py suggest <action> [context]"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    if not args:
        print("Uso: operante.py suggest <action> [context]")
        sys.exit(1)

    action = args[0]
    context = " ".join(args[1:]) if len(args) > 1 else ""

    # Verifica evitações primeiro
    avoid_hits = pa.check(action, context)
    if avoid_hits:
        print(f"\n⚠ REGRAS DE EVITAÇÃO para '{action}':")
        for r in avoid_hits:
            print(f"   → {r['reason']}")
            print(f"     Redução de peso sugerida: -{r['weight_delta']:.4f}")
        print()

    # Reforços
    ranked = rl.rank_strategies(action, context)
    if ranked:
        print(f"\n🏆 Estratégias para '{action}':")
        for strat, stats in ranked:
            avg = stats.get("avg", 0)
            uses = stats.get("uses", 0)
            icon = "🟢" if avg > 0.3 else "🟡" if avg > -0.3 else "🔴"
            print(f"   {icon} {strat:<20} avg={avg:+.4f}  (n={uses})")
    else:
        print(f"\n📭 Nenhum histórico para '{action}'.")

    # Sugestão direta do RewardSeeking
    suggestion = rs.suggest_strategy(action, context)
    if suggestion:
        print(f"\n⭐ Estratégia recomendada: {suggestion}")
    else:
        print(f"\n💡 Use estratégia default e registre o resultado.")


def cmd_avoid(args):
    """Verifica evitações: operante.py avoid [action]"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    pa.analyze()  # Gera/atualiza regras
    save_data(data)

    rules = pa.get_active_rules()
    if not rules:
        print("✅ Nenhuma regra de evitação ativa.")
        return

    if args:
        action_query = " ".join(args)
        rules = [r for r in rules if r["action"].lower() in action_query.lower()]

    print(f"\n⚠ REGRAS DE EVITAÇÃO ATIVAS ({len(rules)}):\n")
    for r in rules:
        print(f"  [{r['id']}]")
        print(f"    Ação:     {r['action']}")
        if r.get("context"):
            print(f"    Contexto: {r['context']}")
        print(f"    Motivo:   {r['reason']}")
        print(f"    Criada:   {r['created_at'][:19]}")
        print(f"    Δ peso:   -{r['weight_delta']:.4f}")
        print()


def cmd_decay(args):
    """Aplica decaimento temporal: operante.py decay [days]"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    days = float(args[0]) if args else None
    behaviors = tracker.all_behaviors()
    decayed_count = 0

    for h, entry in behaviors.items():
        old_w = entry.get("weight", 0)
        timedelta_val = _days_since(entry.get("last_updated", entry.get("first_seen")))
        if days is not None:
            elapsed = days
        else:
            elapsed = timedelta_val
        new_w = old_w * (0.5 ** (max(elapsed, 0) / DECAY_HALFLIFE))
        new_w = round(new_w, 4)
        if abs(new_w - old_w) > 0.0001:
            entry["weight"] = new_w
            decayed_count += 1

    print(f"Decaimento aplicado a {decayed_count}/{len(behaviors)} comportamentos")
    print(f"(meia-vida = {DECAY_HALFLIFE} dias)")
    save_data(data)


def cmd_extinguish(args):
    """Executa protocolo de extinção: operante.py extinguish [threshold]"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    threshold = float(args[0]) if args else EXTINCTION_THRESHOLD
    extinguished_list = ep.evaluate(threshold)
    save_data(data)

    if extinguished_list:
        print(f"\n🪦 {len(extinguished_list)} comportamento(s) extinto(s) (threshold={threshold}):\n")
        for h, e in extinguished_list:
            print(f"  ✗ [{h}] {e['action']}")
            print(f"    peso: {e.get('weight', 0):+.4f}")
            print(f"    motivo: {e.get('extinction_reason', 'N/A')}")
            print()
    else:
        print(f"\n✅ Nenhum comportamento extinto (threshold={threshold}).")

    active = ep.get_active()
    print(f"📊 {len(active)} comportamentos ativos restantes.")


def cmd_dashboard(args):
    """Renderiza o dashboard: operante.py dashboard"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    # Atualiza análises automaticamente
    pa.analyze()
    rs.find_patterns()
    ep.evaluate()
    save_data(data)

    dash.render()


def cmd_full_cycle(args):
    """Executa ciclo completo de condicionamento: operante.py cycle"""
    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    print("\n🔄 Ciclo de Condicionamento Operante\n")

    # 1. Decaimento
    print("  1. Aplicando decaimento temporal...")
    decayed = 0
    for h, entry in tracker.all_behaviors().items():
        old_w = entry.get("weight", 0)
        elapsed = _days_since(entry.get("last_updated", entry.get("first_seen")))
        new_w = old_w * (0.5 ** (max(elapsed, 0) / DECAY_HALFLIFE))
        new_w = round(new_w, 4)
        if abs(new_w - old_w) > 0.0001:
            entry["weight"] = new_w
            decayed += 1
    print(f"     {decayed} comportamentos atualizados")

    # 2. Extinção
    print("  2. Avaliando extinção...")
    ep.evaluate()
    ext = ep.get_extinguished()
    print(f"     {len(ext)} extintos")

    # 3. Análise de punição
    print("  3. Analisando punições...")
    new_rules = pa.analyze()
    print(f"     {len(new_rules)} novas regras de evitação")

    # 4. Busca de recompensas
    print("  4. Identificando reforços...")
    patterns = rs.find_patterns()
    print(f"     {len(patterns)} padrões reforçados")

    save_data(data)
    print("\n✅ Ciclo completo!\n")

    # Mostra dashboard resumido
    dash.render()


def cmd_import_lessons(args):
    """Importa lições de lessons.jsonl para o tracker."""
    if not LESSONS_FILE.exists():
        print(f"Arquivo não encontrado: {LESSONS_FILE}")
        sys.exit(1)

    data = load_data()
    tracker, rl, pa, rs, ep, dash = build_systems(data)

    imported = 0
    with open(LESSONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lesson = json.loads(line)
                action = lesson.get("event", "unknown")
                fix = lesson.get("fix", "")
                summary = lesson.get("summary", "")
                outcome = "success" if "fix" in lesson else "failure"
                tracker.record(
                    action=f"lesson:{action}",
                    outcome=outcome,
                    context=summary[:100],
                    strategy="lesson_imported"
                )
                imported += 1
            except json.JSONDecodeError:
                continue

    save_data(data)
    print(f"✅ {imported} lições importadas de {LESSONS_FILE}")


# ═══════════════════════════════════════════════════════════════
#  ENTRADA
# ═══════════════════════════════════════════════════════════════

def print_help():
    print(__doc__)
    print("\nComandos disponíveis:\n")
    print("  track <action> <outcome> [metric] [ctx=...] [strat=...]")
    print("                          Registra um comportamento")
    print("  report [n]             Mostra os últimos n registros")
    print("  suggest <action> [ctx] Sugere melhor estratégia")
    print("  avoid [action]          Lista regras de evitação")
    print("  decay [days]           Aplica decaimento temporal")
    print("  extinguish [threshold] Executa protocolo de extinção")
    print("  cycle                  Executa ciclo completo")
    print("  dashboard              Mostra painel de visualização")
    print("  import-lessons         Importa de lessons.jsonl")
    print("  help                   Esta mensagem")
    print()
    print("Exemplos:")
    print('  python operante.py track "run_tests" success')
    print('  python operante.py track "api_call" timeout ctx="prod" strat="retry"')
    print('  python operante.py suggest "db_query" "production"')
    print('  python operante.py dashboard')
    print('  python operante.py extinguish 0.05')
    print()

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    COMMANDS = {
        "track": cmd_track,
        "report": cmd_report,
        "suggest": cmd_suggest,
        "avoid": cmd_avoid,
        "decay": cmd_decay,
        "extinguish": cmd_extinguish,
        "cycle": cmd_full_cycle,
        "dashboard": cmd_dashboard,
        "import-lessons": cmd_import_lessons,
        "help": lambda a: print_help(),
    }

    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"Comando desconhecido: {cmd}")
        print(f"Use 'help' para ver comandos disponíveis.")
        sys.exit(1)

    fn(args)


if __name__ == "__main__":
    main()
