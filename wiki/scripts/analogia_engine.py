#!/usr/bin/env python3
"""
analogia_engine.py — Busca analogias do conhecimento para explicar conceitos complexos.

Mapeia conceitos abstratos para domínios familiares usando um banco de
analogias estruturado. Combina analogias por similaridade de atributos,
domínio e nível de abstração.

Estrutura de uma analogia:
  - source_domain: domínio familiar (ex: "cozinha", "trânsito", "futebol")
  - target_domain: conceito complexo a explicar
  - mapping: mapeamento de correspondências
  - explanation: texto explicativo usando a analogia
  - strength: qualidade da analogia [0.0, 1.0]
  - limitations: onde a analogia falha

Uso:
  from analogia_engine import AnalogiaEngine
  engine = AnalogiaEngine()
  resultado = engine.find_analogies("recursão")
  resultado = engine.explain("API REST", level="iniciante")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Analogia:
    """Uma analogia individual entre conceito e domínio familiar."""
    target_concept: str  # conceito a explicar
    source_domain: str   # domínio familiar
    source_label: str    # nome legível do domínio
    mapping: dict[str, str] = field(default_factory=dict)
    explanation: str = ""
    strength: float = 0.7
    limitations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    for_audience: str = "geral"  # iniciante, intermediário, avançado

    def to_dict(self) -> dict:
        return {
            "target_concept": self.target_concept,
            "source_domain": self.source_domain,
            "source_label": self.source_label,
            "mapping": self.mapping,
            "explanation": self.explanation,
            "strength": self.strength,
            "limitations": self.limitations,
            "tags": self.tags,
            "for_audience": self.for_audience,
        }

    def format_text(self) -> str:
        lines = [
            f"🔗 Analogia: {self.target_concept} → {self.source_label}",
            f"   ({self.source_domain})",
            "",
        ]
        if self.mapping:
            lines.append("   Mapeamento:")
            for k, v in self.mapping.items():
                lines.append(f"     • {k} ↔ {v}")
            lines.append("")
        if self.explanation:
            lines.append(f"   {self.explanation}")
        if self.limitations:
            lines.append("")
            lines.append("   Limitações desta analogia:")
            for lim in self.limitations:
                lines.append(f"     ⚠ {lim}")
        lines.append("")
        lines.append(f"   Força: {'█' * int(self.strength * 10)}{'░' * (10 - int(self.strength * 10))} {self.strength:.1f}")
        return "\n".join(lines)


class AnalogiaEngine:
    """
    Motor de analogias para explicação de conceitos complexos.

    Possui um banco de analogias embutido e permite adicionar novas.
    Busca funciona por correspondência exata, tags e similaridade parcial.
    """

    def __init__(self):
        self._analogias: list[Analogia] = []
        self._carregar_banco_padrao()

    # ── API Principal ──────────────────────────────────────────────

    def find_analogies(
        self,
        concept: str,
        audience: str = "geral",
        min_strength: float = 0.4,
        limit: int = 5,
    ) -> list[Analogia]:
        """
        Encontra analogias para um conceito.

        Args:
            concept: conceito a explicar
            audience: público-alvo (iniciante, intermediário, avançado, geral)
            min_strength: força mínima da analogia
            limit: máximo de resultados

        Returns:
            Lista de Analogia ordenadas pela mais forte
        """
        concept_lower = concept.lower().strip()
        results: list[tuple[Analogia, float]] = []

        for analogia in self._analogias:
            # Filtro por público
            if audience != "geral" and analogia.for_audience != "geral":
                if analogia.for_audience != audience:
                    continue

            # Filtro por força
            if analogia.strength < min_strength:
                continue

            # Calcular relevância
            relevance = self._calc_relevance(concept_lower, analogia)
            if relevance > 0:
                results.append((analogia, relevance))

        # Ordenar por relevância * força
        results.sort(key=lambda x: x[1] * x[0].strength, reverse=True)
        return [a for a, _ in results[:limit]]

    def explain(
        self,
        concept: str,
        audience: str = "geral",
    ) -> str:
        """
        Gera explicação usando a melhor analogia encontrada.

        Args:
            concept: conceito a explicar
            audience: público-alvo

        Returns:
            Texto explicativo usando analogia, ou mensagem se não encontrou.
        """
        analogias = self.find_analogies(concept, audience=audience, limit=3)
        if not analogias:
            return f"🔍 Nenhuma analogia encontrada para '{concept}'. Tente adicionar uma com add_analogia()."

        lines = [f"📚 Explicação por analogia: {concept}\n"]
        for i, analogia in enumerate(analogias):
            if i == 0:
                lines.append(analogia.format_text())
            else:
                lines.append(f"--- Alternativa ({i + 1}) ---")
                lines.append(analogia.format_text())

        return "\n".join(lines)

    def add_analogia(self, analogia: Analogia):
        """Adiciona uma nova analogia ao banco."""
        self._analogias.append(analogia)

    def add_analogia_quick(
        self,
        concept: str,
        domain: str,
        domain_label: str,
        explanation: str,
        mapping: Optional[dict[str, str]] = None,
        strength: float = 0.7,
        limitations: Optional[list[str]] = None,
        audience: str = "geral",
        tags: Optional[list[str]] = None,
    ):
        """Adiciona analogia de forma simplificada."""
        self._analogias.append(Analogia(
            target_concept=concept,
            source_domain=domain,
            source_label=domain_label,
            mapping=mapping or {},
            explanation=explanation,
            strength=strength,
            limitations=limitations or [],
            tags=tags or [],
            for_audience=audience,
        ))

    def list_concepts(self) -> list[str]:
        """Lista todos os conceitos que têm analogias."""
        return sorted(set(a.target_concept for a in self._analogias))

    def list_domains(self) -> list[str]:
        """Lista todos os domínios-fonte usados."""
        return sorted(set(a.source_label for a in self._analogias))

    def to_json(self) -> str:
        return json.dumps(
            [a.to_dict() for a in self._analogias],
            indent=2, ensure_ascii=False,
        )

    # ── Busca e matching ───────────────────────────────────────────

    def _calc_relevance(self, concept: str, analogia: Analogia) -> float:
        """Calcula relevância de uma analogia para um conceito."""
        score = 0.0

        # Match exato no conceito
        if concept == analogia.target_concept.lower():
            return 1.0

        # Match parcial no conceito
        if concept in analogia.target_concept.lower():
            score = 0.8
        elif analogia.target_concept.lower() in concept:
            score = 0.6

        # Match nas tags
        for tag in analogia.tags:
            if concept in tag.lower() or tag.lower() in concept:
                score = max(score, 0.7)

        # Match no domínio
        if concept in analogia.source_domain.lower():
            score = max(score, 0.3)

        return score

    # ── Banco de analogias padrão ──────────────────────────────────

    def _carregar_banco_padrao(self):
        """Carrega analogias padrão para conceitos comuns de tecnologia."""

    # ── Recursão ───────────────────────────────────────────────────
        self.add_analogia_quick(
            concept="recursão",
            domain="boneca_russa",
            domain_label="Bonecas Russas (Matryoshka)",
            explanation=(
                "Recursão é como uma boneca russa: cada boneca contém uma versão "
                "menor de si mesma. A função recursiva chama a si mesma com um "
                "problema menor, até chegar na menor boneda (caso base), que não "
                "contém mais ninguém dentro."
            ),
            mapping={
                "função recursiva": "boneca que contém outra boneca",
                "caso base": "menor boneca (não abre mais)",
                "chamada recursiva": "abrir a boneca e encontrar outra",
                "stack overflow": "tentar abrir bonecas infinitas",
            },
            strength=0.9,
            limitations=[
                "Bonecas russas têm limite físico óbvio; recursão depende da memória.",
                "Não captura bem recursão mútua (A chama B, B chama A).",
            ],
            audience="iniciante",
            tags=["programação", "funções", "algoritmo"],
        )

        self.add_analogia_quick(
            concept="recursão",
            domain="espelhos",
            domain_label="Dois Espelhos Frente a Frente",
            explanation=(
                "Imagine dois espelhos frente a frente: você vê reflexos infinitos, "
                "cada um menor que o anterior. A recursão funciona assim — cada "
                "chamada cria um 'reflexo' menor do problema, até que o reflexo "
                "fica tão pequeno que para (caso base)."
            ),
            mapping={
                "reflexo": "chamada recursiva",
                "espelho": "função",
                "reflexo mínimo": "caso base",
                "infinito": "recursão sem caso base",
            },
            strength=0.75,
            limitations=[
                "Espelhos sugerem infinito; recursão sempre deve ter caso base.",
            ],
            audience="iniciante",
            tags=["programação", "funções"],
        )

    # ── API REST ───────────────────────────────────────────────────
        self.add_analogia_quick(
            concept="API REST",
            domain="restaurante",
            domain_label="Restaurante (Garçom)",
            explanation=(
                "Uma API REST é como um restaurante. Você (cliente) não entra na "
                "cozinha — você faz pedidos ao garçom (API). O garçom leva seu "
                "pedido à cozinha (servidor) e traz a resposta (comida/dados). "
                "GET = pedir o cardápio, POST = fazer pedido, PUT = alterar pedido, "
                "DELETE = cancelar pedido."
            ),
            mapping={
                "cliente": "aplicativo/frontend",
                "garçom": "API",
                "cozinha": "servidor/banco de dados",
                "cardápio": "documentação da API",
                "GET": "pedir cardápio",
                "POST": "fazer pedido",
                "PUT": "alterar pedido",
                "DELETE": "cancelar pedido",
                "código de erro": "prato indisponível",
            },
            strength=0.95,
            limitations=[
                "Em restaurantes reais, o garçom tem estado (sabe quem você é). APIs REST são stateless.",
                "Não captura bem autenticação, rate limiting ou webhooks.",
            ],
            audience="iniciante",
            tags=["web", "http", "backend", "rede"],
        )

    # ── Cache ──────────────────────────────────────────────────────
        self.add_analogia_quick(
            concept="cache",
            domain="balcao",
            domain_label="Balcão de Atendimento",
            explanation=(
                "Cache é como ter um balcão de atendimento rápido ao lado do "
                "escritório principal. Em vez de ir até o escritório (banco de dados) "
                "toda vez, você pergunta no balcão primeiro. Se a resposta estiver lá "
                "(cache hit), é instantâneo. Se não (cache miss), vai ao escritório "
                "e traz a resposta para o balcão."
            ),
            mapping={
                "balcão rápido": "cache (Redis, Memcached)",
                "escritório principal": "banco de dados",
                "cache hit": "encontrou no balcão",
                "cache miss": "precisou ir ao escritório",
                "TTL": "tempo que a resposta fica no balcão antes de expirar",
                "cache invalidation": "atualizar o balcão quando o escritório muda algo",
            },
            strength=0.9,
            limitations=[
                "Não captura bem cache distribuído ou cache em múltiplas camadas.",
            ],
            audience="iniciante",
            tags=["performance", "banco de dados", "infraestrutura"],
        )

    # ── Blockchain ─────────────────────────────────────────────────
        self.add_analogia_quick(
            concept="blockchain",
            domain="livro_caixa",
            domain_label="Livro Caixa Compartilhado",
            explanation=(
                "Blockchain é como um livro caixa que todos têm uma cópia idêntica. "
                "Quando alguém faz uma transação, todos anotam ao mesmo tempo. "
                "Cada página (bloco) tem um código (hash) que depende da página anterior. "
                "Se alguém tenta alterar uma página antiga, o código não bate mais "
                "com as páginas seguintes — e todos percebem a fraude."
            ),
            mapping={
                "página do livro": "bloco",
                "código da página": "hash",
                "cópia do livro": "nó da rede",
                "anotar transação": "minerar bloco",
                "código que não bata": "tentativa de fraude",
                "consenso": "maioria dos livros concorda",
            },
            strength=0.85,
            limitations=[
                "Não captura bem smart contracts ou proof-of-stake.",
                "Blockchain real é mais complexo que um livro caixa.",
            ],
            audience="iniciante",
            tags=["cripto", "descentralizado", "segurança"],
        )

    # ── Machine Learning ───────────────────────────────────────────
        self.add_analogia_quick(
            concept="machine learning",
            domain="crianca",
            domain_label="Criança Aprendendo",
            explanation=(
                "Machine learning é como ensinar uma criança. Você não dá regras "
                "explícitas — você mostra muitos exemplos. A criança erra, você "
                "corrige, e ela melhora com o tempo. O modelo de ML funciona assim: "
                "recebe dados (exemplos), faz previsões (chutes), compara com a "
                "realidade (erro), e ajusta seus parâmetros (aprende)."
            ),
            mapping={
                "criança": "modelo de ML",
                "exemplos": "dados de treino",
                "erro": "loss function",
                "correção": "backpropagation",
                "melhorar com tempo": "treinamento/épocas",
                "decorar sem entender": "overfitting",
                "generalizar bem": "modelo bem treinado",
            },
            strength=0.85,
            limitations=[
                "Crianças têm senso comum; modelos de ML não.",
                "Não captura bem diferenças entre tipos de ML (supervised, unsupervised, RL).",
            ],
            audience="iniciante",
            tags=["IA", "dados", "algoritmo"],
        )

    # ── DNS ────────────────────────────────────────────────────────
        self.add_analogia_quick(
            concept="DNS",
            domain="lista_telefonica",
            domain_label="Lista Telefônica",
            explanation=(
                "DNS é como uma lista telefônica da internet. Em vez de lembrar "
                "números (IPs como 142.250.185.206), você procura o nome "
                "(google.com) e a lista te dá o número. Quando você digita um site, "
                "seu computador consulta o DNS para traduzir o nome em IP."
            ),
            mapping={
                "nome no DNS": "nome na lista telefônica",
                "endereço IP": "número de telefone",
                "resolver DNS": "consultar a lista",
                "cache DNS": "ter os números salvos nos contatos",
                "propagação DNS": "atualizar a lista telefônica",
            },
            strength=0.95,
            limitations=[
                "DNS é hierárquico e distribuído; lista telefônica é centralizada.",
            ],
            audience="iniciante",
            tags=["rede", "internet", "infraestrutura"],
        )

    # ── Git ────────────────────────────────────────────────────────
        self.add_analogia_quick(
            concept="git",
            domain="save_game",
            domain_label="Save de Videogame",
            explanation=(
                "Git é como o sistema de save de um videogame. Cada commit é um "
                "ponto de save. Você pode voltar a qualquer save anterior (checkout), "
                "criar uma linha alternativa (branch) para testar algo sem "
                "arriscar o save principal, e juntar duas linhas (merge). Se der "
                "errado, é só voltar ao save anterior."
            ),
            mapping={
                "commit": "ponto de save",
                "branch": "linha alternativa de progresso",
                "merge": "jogar duas linhas de save juntas",
                "checkout": "carregar um save anterior",
                "revert": "desfazer uma ação voltando ao save",
                "HEAD": "save atual carregado",
                "remote": "save na nuvem (pode jogar em outro console)",
                "clone": "baixar o save de outra pessoa",
            },
            strength=0.9,
            limitations=[
                "Git é mais complexo: rebase, cherry-pick, stash não têm equivalente em saves.",
                "Merge conflicts não acontecem em saves de videogame.",
            ],
            audience="iniciante",
            tags=["versionamento", "código", "colaboração"],
        )

    # ── Microserviços ──────────────────────────────────────────────
        self.add_analogia_quick(
            concept="microserviços",
            domain="cidade",
            domain_label="Cidade com Bairros Especializados",
            explanation=(
                "Microserviços são como uma cidade com bairros especializados. "
                "Cada bairro (serviço) tem sua própria função: o bairro financeiro "
                "lida com pagamentos, o bairro residencial com usuários, o bairro "
                "industrial com processamento. Se um bairro pega fogo, os outros "
                "continuam funcionando. A comunicação entre bairros é por ruas "
                "(APIs/mensageria)."
            ),
            mapping={
                "bairro": "microserviço",
                "prefeitura central": "API gateway",
                "ruas": "rede/comunicação entre serviços",
                "incêndio num bairro": "falha de um serviço",
                "bombeiros": "circuit breaker / monitoramento",
                "zoneamento": "bounded context (DDD)",
            },
            strength=0.8,
            limitations=[
                "Cidades têm governo central; microserviços idealmente não.",
                "Não captura bem service mesh, event sourcing, etc.",
            ],
            audience="intermediário",
            tags=["arquitetura", "backend", "escalabilidade"],
        )

    # ── Criptografia ───────────────────────────────────────────────
        self.add_analogia_quick(
            concept="criptografia",
            domain="cadeado",
            domain_label="Cadeado e Chave",
            explanation=(
                "Criptografia é como um cadeado. A mensagem original (texto plano) "
                "é trancada com um cadeado (criptografia) usando uma chave. Só quem "
                "tem a chave certa pode abrir (descriptografar). Criptografia "
                "simétrica = mesma chave para trancar e destrancar. Assimétrica = "
                "chave pública (cadeado) para trancar, chave privada para destrancar."
            ),
            mapping={
                "cadeado": "algoritmo de criptografia",
                "chave": "senha/chave criptográfica",
                "trancar": "criptografar",
                "destrancar": "descriptografar",
                "chave pública": "cadeado que qualquer um pode fechar",
                "chave privada": "única chave que abre o cadeado",
                "hash": "impressão digital da mensagem",
            },
            strength=0.85,
            limitations=[
                "Cadeados físicos podem ser forçados; criptografia forte é matematicamente inviolável.",
                "Não captura bem assinaturas digitais ou certificados.",
            ],
            audience="iniciante",
            tags=["segurança", "rede", "dados"],
        )


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    engine = AnalogiaEngine()

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("=== Analogia Engine Demo ===\n")

        conceitos = ["recursão", "API REST", "cache", "git", "DNS"]
        for conceito in conceitos:
            print(engine.explain(conceito, audience="iniciante"))
            print("\n" + "=" * 60 + "\n")

        print(f"Conceitos disponíveis: {', '.join(engine.list_concepts())}")
        print(f"Domínios usados: {', '.join(engine.list_domains())}")

    elif len(sys.argv) > 1 and sys.argv[1] == "--search" and len(sys.argv) > 2:
        termo = " ".join(sys.argv[2:])
        analogias = engine.find_analogies(termo)
        if analogias:
            for a in analogias:
                print(a.format_text())
        else:
            print(f"Nenhuma analogia para '{termo}'")

    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Uso: python analogia_engine.py [--demo|--search <termo>|--help]")
    else:
        print("Analogia Engine v1.0")
        print(f"  {len(engine.list_concepts())} conceitos, {len(engine.list_domains())} domínios")
        print("Importe: from analogia_engine import AnalogiaEngine")
