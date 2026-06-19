"""
consolidation.py — A parte "cara" do sistema, e por isso ela roda OFFLINE.

Esta é a separação central do LightMem (2026): processamento online
(escrever uma memória, recuperar memórias) é barato — sem chamada de
LLM. Processamento offline (agrupar memórias relacionadas e gerar um
fato consolidado) usa o modelo pequeno, mas raramente — uma vez por
cluster, não uma vez por turno.

Fluxo:
  1. extract_entities(): heurística leve (regex), sem custo de inferência.
  2. cluster_by_overlap(): agrupa memórias episódicas não-promovidas que
     compartilham entidades — union-find com índice invertido, custo O(n·e)
     onde e = entidades médias por memória (muito melhor que O(n²) quando
     entidades são esparsas).
  3. consolidate_cluster(): UMA chamada ao modelo local por cluster,
     gerando um fato sintetizado (estilo A-MEM: nota com contexto,
     não cópia literal das memórias-fonte).
"""

import json
import re
from collections import defaultdict


# Palavras de baixo valor semântico — filtradas da extração de entidades.
STOPWORDS_PT = {
    "Eu", "Você", "Voce", "Que", "Isso", "Isto", "Aquele", "Aquela",
    "Hoje", "Ontem", "Amanha", "Amanhã", "Sim", "Nao", "Não",
}


def _suppress_sentence_initial_capitals(text: str) -> str:
    """
    Capitalização no início de frase é gramática, não sinal de nome
    próprio ("Hoje fui ao médico" != entidade "Hoje"). Sem isso, um
    teste de escala (500 notas sintéticas) mostrou clusters falsos:
    toda frase começando com a mesma palavra ("Nota...") virava uma
    entidade compartilhada e fundia memórias completamente não
    relacionadas num único cluster gigante.

    Correção: minúsculo a primeira letra de cada sentença antes de
    rodar o regex de nomes próprios. Custo: perdemos nomes próprios
    que aparecem literalmente no início de uma frase — aceitável,
    porque na escrita natural a maioria das menções a entidades
    (Atena, TTP, nomes de pessoas) ocorre no meio da frase.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    fixed = []
    for s in sentences:
        if s:
            s = s[0].lower() + s[1:]
        fixed.append(s)
    return " ".join(fixed)


def extract_entities(text: str) -> list[str]:
    """
    Extração heurística e barata: substantivos próprios (sequências de
    palavras capitalizadas, fora do início de frase) + termos técnicos
    comuns no seu domínio.

    Propositalmente simples. Não usa NER nem chama o LLM — isso é o
    que mantém o caminho de escrita (remember()) rápido em CPU.
    Se quiser mais precisão depois, dá pra trocar por spaCy pt_core_news_sm
    ou por uma chamada ocasional ao próprio atena-glm5, mas comece simples.
    """
    safe_text = _suppress_sentence_initial_capitals(text)
    candidates = re.findall(r"\b[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*\b", safe_text)
    entities: set[str] = set()
    for c in candidates:
        c = c.strip()
        if c and c not in STOPWORDS_PT and len(c) > 2:
            entities.add(c)

    # Termos técnicos/domínio em minúsculas que valem a pena capturar
    # mesmo sem capitalização (ajuste essa lista ao seu vocabulário real).
    domain_terms = [
        "distonia", "TTP", "Tempo Puxado", "Atena", "Cidade Anômala",
        "artefato cognitivo", "RAG", "Ollama",
    ]
    lowered = text.lower()
    for term in domain_terms:
        if term.lower() in lowered:
            entities.add(term)

    return sorted(entities)


def cluster_by_overlap(
    rows: list,
    min_shared_entities: int = 1,
    min_cluster_size: int = 2,
) -> list[list]:
    """
    Union-find com índice invertido: duas memórias entram no mesmo cluster
    se compartilham pelo menos `min_shared_entities` entidades.

    Otimização: em vez de O(n²) par a par, construímos um índice invertido
    (entidade → lista de ids) e só comparamos memórias que compartilham
    pelo menos uma entidade. Para volumes pessoais (centenas a poucos
    milhares) isso é significativamente mais rápido.

    Retorna apenas clusters com tamanho >= min_cluster_size
    (clusters de 1 não valem consolidação — não há o que sintetizar).
    """
    if not rows:
        return []

    # Índice invertido: entidade -> set de ids que a contêm
    entity_to_ids: dict[str, set[int]] = defaultdict(set)
    entity_sets: dict[int, set[str]] = {}

    for row in rows:
        ents = set(json.loads(row["entities"]))
        entity_sets[row["id"]] = ents
        for e in ents:
            entity_to_ids[e].add(row["id"])

    # Union-find
    parent: dict[int, int] = {row["id"]: row["id"] for row in rows}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    # Fase 1: encontra pares candidatos via índice invertido
    # (pares que compartilham pelo menos 1 entidade)
    candidate_pairs: set[tuple[int, int]] = set()
    for ent, id_set in entity_to_ids.items():
        if len(id_set) < 2:
            continue
        id_list = sorted(id_set)
        for i in range(len(id_list)):
            for j in range(i + 1, len(id_list)):
                candidate_pairs.add((id_list[i], id_list[j]))

    # Fase 2: para min_shared_entities > 1, filtra pares que não atingem
    # o limiar mínimo de entidades compartilhadas
    if min_shared_entities <= 1:
        for a, b in candidate_pairs:
            union(a, b)
    else:
        for a, b in candidate_pairs:
            shared = entity_sets[a] & entity_sets[b]
            if len(shared) >= min_shared_entities:
                union(a, b)

    groups: dict[int, list] = defaultdict(list)
    row_by_id: dict[int, dict] = {row["id"]: row for row in rows}
    for id_ in parent:
        groups[find(id_)].append(row_by_id[id_])

    return [g for g in groups.values() if len(g) >= min_cluster_size]


CONSOLIDATION_SYSTEM_PROMPT = """Você é o módulo de consolidação de memória da Atena.
Sua tarefa: ler várias memórias episódicas relacionadas sobre o mesmo
tópico/entidade e sintetizar UM fato consolidado, denso e sem perda
de informação essencial. Não invente nada que não esteja nas memórias.
Responda APENAS com o fato consolidado, uma ou duas frases, sem preâmbulo."""


def consolidate_cluster(cluster: list, bridge) -> str:
    """
    Uma única chamada ao modelo local por cluster. `bridge` é uma
    instância de AtenaBridge (bridge.py) — injeção de dependência para
    facilitar testes sem Ollama real.
    """
    memories_text = "\n".join(f"- {row['content']}" for row in cluster)
    prompt = f"Memórias relacionadas:\n{memories_text}\n\nFato consolidado:"
    return bridge.ask(prompt, system=CONSOLIDATION_SYSTEM_PROMPT, temperature=0.2)
