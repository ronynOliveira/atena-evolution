#!/usr/bin/env python3
"""Pesquisa refinada - artigos específicos sobre agent loops"""
import urllib.request
import xml.etree.ElementTree as ET
import json

def get_paper(arxiv_id):
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entries = root.findall('a:entry', ns)
    if entries:
        e = entries[0]
        return {
            'title': e.find('a:title', ns).text.strip().replace('\n', ' '),
            'published': e.find('a:published', ns).text[:10],
            'summary': e.find('a:summary', ns).text.strip().replace('\n', ' ')[:500],
            'authors': [a.find('a:name', ns).text for a in e.findall('a:author', ns)]
        }
    return None

# Papers conhecidos e relevantes sobre agent loops
papers = [
    ("2205.00445", "ReAct: Synergizing Reasoning and Acting in Language Models"),
    ("2201.11903", "Chain-of-Thought Prompting Elicits Reasoning"),
    ("2203.11436", "Self-Refine: Iterative Refinement with Self-Feedback"),
    ("2210.03629", "Reflexion: Language Agents with Verbal Reinforcement Learning"),
    ("2205.07867", "Large Language Models are Zero-Shot Reasoners"),
    ("2308.11432", "AutoGPT: An Autonomous GPT-4 Experiment"),
    ("2309.07864", "Generative Agents: Interactive Simulacra of Human Behavior"),
    ("2308.00352", "Toolformer: Language Models Can Teach Themselves to Use Tools"),
]

print("=" * 60)
print("PESQUISA REFINADA: Artigos sobre Agent Loops")
print("=" * 60)

for arxiv_id, expected_title in papers:
    try:
        paper = get_paper(arxiv_id)
        if paper:
            print(f"\n  [{paper['published']}] {paper['title']}")
            print(f"  Authors: {', '.join(paper['authors'][:3])}")
            print(f"  {paper['summary'][:300]}...")
    except Exception as e:
        print(f"\n  [{arxiv_id}] Erro: {e}")

print("\n" + "=" * 60)
print("PESQUISA REFINADA CONCLUÍDA")
print("=" * 60)
