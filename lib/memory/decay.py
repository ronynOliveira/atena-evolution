"""
decay.py — Esquecimento natural via curva de Ebbinghaus.

Fórmula direta do MemoryBank (Zhong et al., 2024), validada também
em FadeMem (2026) e em implementações de produção como YourMemory:

    R = e^(-t / S)

onde:
    R = retenção atual (0 a 1) — quão "viva" a memória está
    t = dias desde o último acesso (não desde a criação!)
    S = força da memória, aumenta a cada recall

Esse design tem uma propriedade importante para o seu caso filosófico:
não existe um "apagar" binário. Existe um gradiente contínuo entre
presença e ausência — que é, aliás, bem mais próximo do seu vocabulário
de Memória vs. Esquecimento do que um DELETE FROM seria.
"""

import math


def retention(days_since_access: float, strength: float) -> float:
    """R = e^(-t/S). Retorna valor entre 0 e 1."""
    s = max(strength, 0.01)  # evita divisão por zero
    t = max(days_since_access, 0.0)
    return math.exp(-t / s)


def reinforce(strength: float, boost: float = 1.0) -> float:
    """
    Cada recall aumenta S — memórias usadas resistem mais ao esquecimento.
    Isso é o equivalente computacional do "efeito de espaçamento":
    relembrar é mais barato que reaprender, e fortalece a retenção futura.
    """
    return strength + boost


def importance_adjusted_strength(base_strength: float, importance: float) -> float:
    """
    Memórias mais importantes (heurística: contém dados pessoais
    estáveis, decisões, fatos sobre você) decaem mais devagar.
    importance vai de 0 a 1.
    """
    return base_strength * (1.0 + importance)


def should_archive(retention_score: float, threshold: float = 0.05) -> bool:
    """
    Abaixo do threshold, a memória episódica é arquivada (não destruída —
    fica fora do índice de busca ativo, mas pode ser reativada se um
    processo de consolidação posterior a referenciar).
    """
    return retention_score < threshold
