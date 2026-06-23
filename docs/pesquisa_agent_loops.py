#!/usr/bin/env python3
"""Pesquisa sobre Agent Loops - arXiv API + Wikipedia"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re

def search_arxiv(query, max_results=5):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query.replace(' ', '+')}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entries = root.findall('a:entry', ns)
    results = []
    for e in entries:
        title = e.find('a:title', ns).text.strip().replace('\n', ' ')
        published = e.find('a:published', ns).text[:10]
        link = e.find('a:id', ns).text
        summary = e.find('a:summary', ns).text.strip().replace('\n', ' ')[:300]
        results.append({'title': title, 'published': published, 'link': link, 'summary': summary})
    return results

def search_wikipedia(title):
    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={title.replace(' ', '_')}&prop=text&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    text = data.get('parse', {}).get('text', {}).get('*', '')
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:3000]

# Pesquisa 1: Agent Loops
print("=" * 60)
print("PESQUISA 1: Agent Loops / Autonomous Agents (arXiv)")
print("=" * 60)
try:
    results = search_arxiv("agent loop autonomous AI", 5)
    for r in results:
        print(f"\n  [{r['published']}] {r['title']}")
        print(f"  Link: {r['link']}")
        print(f"  {r['summary']}...")
except Exception as e:
    print(f"  Erro: {e}")

# Pesquisa 2: ReAct
print("\n" + "=" * 60)
print("PESQUISA 2: ReAct Framework (arXiv)")
print("=" * 60)
try:
    results = search_arxiv("ReAct reasoning acting language models", 5)
    for r in results:
        print(f"\n  [{r['published']}] {r['title']}")
        print(f"  Link: {r['link']}")
        print(f"  {r['summary']}...")
except Exception as e:
    print(f"  Erro: {e}")

# Pesquisa 3: Multi-Agent
print("\n" + "=" * 60)
print("PESQUISA 3: Multi-Agent Orchestration (arXiv)")
print("=" * 60)
try:
    results = search_arxiv("multi-agent orchestration loop", 5)
    for r in results:
        print(f"\n  [{r['published']}] {r['title']}")
        print(f"  Link: {r['link']}")
        print(f"  {r['summary']}...")
except Exception as e:
    print(f"  Erro: {e}")

# Pesquisa 4: Wikipedia AI Agent
print("\n" + "=" * 60)
print("PESQUISA 4: Wikipedia - AI Agent")
print("=" * 60)
try:
    text = search_wikipedia("AI agent")
    print(text)
except Exception as e:
    print(f"  Erro: {e}")

# Pesquisa 5: Wikipedia ReAct
print("\n" + "=" * 60)
print("PESQUISA 5: Wikipedia - ReAct")
print("=" * 60)
try:
    text = search_wikipedia("ReAct (reasoning and acting in language models)")
    print(text)
except Exception as e:
    print(f"  Erro: {e}")

print("\n" + "=" * 60)
print("PESQUISA CONCLUÍDA - Salvando resultados")
print("=" * 60)

# Salvar resultados em arquivo
output = {
    'pesquisa': 'Agent Loops',
    'data': '2026-06-23',
    'fontes': ['arXiv API', 'Wikipedia API'],
    'resultados': []
}
try:
    output['resultados'].append({'query': 'agent loop autonomous AI', 'results': search_arxiv("agent loop autonomous AI", 5)})
    output['resultados'].append({'query': 'ReAct reasoning acting', 'results': search_arxiv("ReAct reasoning acting language models", 5)})
except:
    pass

with open("C:/Users/dell-/AppData/Local/hermes/atena_evolution/docs/pesquisa-agent-loops-2026-06-23.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print("Salvo em docs/pesquisa-agent-loops-2026-06-23.json")
