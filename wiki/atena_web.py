"""
Atena Web Search Engine
======================
Motor de busca web robusto com múltiplas estratégias de fallback.
Autor: Sistema Atena
Versão: 1.0
"""

import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from atena_config import AtenaConfig
from typing import List, Dict, Optional, Any, Union
import json
import time
import random
from urllib.parse import quote_plus, urljoin, urlparse
from dataclasses import dataclass, asdict
import logging
from datetime import datetime, timedelta
import hashlib
import sqlite3
import os
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Estrutura padronizada para resultados de busca"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: datetime
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class AtenaWebSearchEngine:
    """
    Motor de busca web multicamadas com estratégias de fallback
    """
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.cache_db = self._init_cache_db()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]

    def _init_cache_db(self) -> sqlite3.Connection:
        """Inicializa banco de dados de cache local"""
        cache_dir = "data/cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        db_path = os.path.join(cache_dir, "search_cache.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                results TEXT,
                timestamp DATETIME,
                source TEXT
            )
        """)
        conn.commit()
        return conn
    
    def _get_cache_key(self, query: str, source: str = "all") -> str:
        """Gera chave de cache para a consulta"""
        return hashlib.md5(f"{query}:{source}".encode()).hexdigest()
    
    def _get_cached_results(self, query: str, source: str = "all") -> Optional[List[SearchResult]]:
        """Recupera resultados do cache se não estiverem expirados"""
        cache_key = self._get_cache_key(query, source)
        ttl = timedelta(hours=self.config.cache_ttl_hours)
        
        cursor = self.cache_db.execute(
            "SELECT results, timestamp FROM search_cache WHERE query_hash = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        
        if row:
            results_json, timestamp_str = row
            timestamp = datetime.fromisoformat(timestamp_str)
            
            if datetime.now() - timestamp < ttl:
                logger.info(f"Cache hit para query: {query}")
                results_data = json.loads(results_json)
                return [SearchResult(**result) for result in results_data]
        
        return None
    
    def _cache_results(self, query: str, results: List[SearchResult], source: str = "all"):
        """Armazena resultados no cache"""
        cache_key = self._get_cache_key(query, source)
        results_json = json.dumps([asdict(result) for result in results], default=str)
        
        self.cache_db.execute("""
            INSERT OR REPLACE INTO search_cache 
            (query_hash, query, results, timestamp, source)
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, query, results_json, datetime.now().isoformat(), source))
        self.cache_db.commit()
    
    async def search(self, query: str, max_results: int = 20) -> List[SearchResult]:
        """
        Busca principal com estratégias de fallback
        """
        logger.info(f"Iniciando busca para: '{query}'")
        
        # 1. Verificar cache primeiro
        cached_results = self._get_cached_results(query)
        if cached_results:
            return cached_results[:max_results]
        
        all_results = []
        
        # 2. Buscar em fontes habilitadas por ordem de prioridade
        search_engines = sorted(
            self.config.search_engines.items(),
            key=lambda x: x[1].get("priority", 999)
        )
        
        for engine_name, engine_config in search_engines:
            if not engine_config.get("enabled", False):
                continue
                
            try:
                logger.info(f"Buscando em: {engine_name}")
                results = await self._search_engine(engine_name, query, max_results)
                
                if results:
                    all_results.extend(results)
                    logger.info(f"Encontrados {len(results)} resultados em {engine_name}")
                    
                    # Se já temos resultados suficientes, parar
                    if len(all_results) >= max_results:
                        break
                        
            except Exception as e:
                logger.error(f"Erro ao buscar em {engine_name}: {e}")
                continue
        
        # 3. Deduplicar e ranquear resultados
        final_results = self._deduplicate_and_rank(all_results)[:max_results]
        
        # 4. Cache dos resultados
        if final_results:
            self._cache_results(query, final_results)
        
        logger.info(f"Busca concluída: {len(final_results)} resultados únicos")
        return final_results
    
    async def _search_engine(self, engine_name: str, query: str, max_results: int) -> List[SearchResult]:
        """Dispatch para diferentes motores de busca"""
        search_methods = {
            "duckduckgo": self._search_duckduckgo,
            "google_scrape": self._search_google_scrape,
            "bing_api": self._search_bing_api,
            "startpage": self._search_startpage
        }
        
        method = search_methods.get(engine_name)
        if method:
            return await method(query, max_results)
        else:
            logger.warning(f"Motor de busca desconhecido: {engine_name}")
            return []
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        """Busca no DuckDuckGo via scraping"""
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_duckduckgo_results(html, query)
                    else:
                        logger.error(f"DuckDuckGo retornou status {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Erro ao buscar no DuckDuckGo: {e}")
            return []
    
    def _parse_duckduckgo_results(self, html: str, query: str) -> List[SearchResult]:
        """Parse dos resultados do DuckDuckGo"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # DuckDuckGo usa divs com classe específica para resultados
        result_divs = soup.find_all('div', class_='result')
        
        for div in result_divs:
            try:
                # Link e título
                title_link = div.find('a', class_='result__a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                url = title_link.get('href', '')
                
                # Snippet
                snippet_div = div.find('div', class_='result__snippet')
                snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                
                if title and url:
                    result = SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="duckduckgo",
                        timestamp=datetime.now(),
                        relevance_score=self._calculate_relevance(title, snippet, query)
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.debug(f"Erro ao processar resultado DDG: {e}")
                continue
        
        return results
    
    async def _search_google_scrape(self, query: str, max_results: int) -> List[SearchResult]:
        """Busca no Google via scraping (com cuidado para evitar bloqueios)"""
        url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(max_results, 50)}"
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
        
        try:
            # Delay aleatório para evitar detecção
            await asyncio.sleep(random.uniform(1, 3))
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_google_results(html, query)
                    else:
                        logger.warning(f"Google retornou status {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Erro ao buscar no Google: {e}")
            return []
    
    def _parse_google_results(self, html: str, query: str) -> List[SearchResult]:
        """Parse dos resultados do Google"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Google muda frequentemente, múltiplos seletores
        selectors = [
            'div.g',  # Seletor principal
            'div[data-ved]',  # Alternativo
            '.rc'  # Mais antigo
        ]
        
        result_divs = []
        for selector in selectors:
            result_divs = soup.select(selector)
            if result_divs:
                break
        
        for div in result_divs[:max_results]:
            try:
                # Título e link
                title_link = div.find('h3')
                if not title_link:
                    continue
                
                parent_link = title_link.find_parent('a')
                if not parent_link:
                    continue
                
                title = title_link.get_text(strip=True)
                url = parent_link.get('href', '')
                
                # Snippet
                snippet_spans = div.find_all('span', string=True)
                snippet = ' '.join([span.get_text(strip=True) for span in snippet_spans[-2:]])
                
                if title and url and url.startswith('http'):
                    result = SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="google",
                        timestamp=datetime.now(),
                        relevance_score=self._calculate_relevance(title, snippet, query)
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.debug(f"Erro ao processar resultado Google: {e}")
                continue
        
        return results
    
    async def _search_bing_api(self, query: str, max_results: int) -> List[SearchResult]:
        """Busca via Bing Search API (requer chave)"""
        api_key = self.config.search_engines["bing_api"].get("api_key")
        if not api_key:
            logger.warning("Bing API key não configurada")
            return []
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": min(max_results, 50),
            "mkt": "pt-BR",
            "responseFilter": "Webpages"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_bing_api_results(data, query)
                    else:
                        logger.error(f"Bing API retornou status {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Erro na Bing API: {e}")
            return []
    
    def _parse_bing_api_results(self, data: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse dos resultados da Bing API"""
        results = []
        
        web_pages = data.get("webPages", {}).get("value", [])
        
        for page in web_pages:
            result = SearchResult(
                title=page.get("name", ""),
                url=page.get("url", ""),
                snippet=page.get("snippet", ""),
                source="bing_api",
                timestamp=datetime.now(),
                relevance_score=self._calculate_relevance(
                    page.get("name", ""), 
                    page.get("snippet", ""), 
                    query
                )
            )
            results.append(result)
        
        return results
    
    async def _search_startpage(self, query: str, max_results: int) -> List[SearchResult]:
        """Busca no Startpage (proxy do Google)"""
        url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_startpage_results(html, query)
                    else:
                        logger.warning(f"Startpage retornou status {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Erro ao buscar no Startpage: {e}")
            return []
    
    def _parse_startpage_results(self, html: str, query: str) -> List[SearchResult]:
        """Parse dos resultados do Startpage"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Startpage usa divs com classe específica
        result_divs = soup.find_all('div', class_='w-gl__result')
        
        for div in result_divs:
            try:
                # Título e link
                title_link = div.find('a', class_='w-gl__result-title')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                url = title_link.get('href', '')
                
                # Snippet
                snippet_div = div.find('div', class_='w-gl__description')
                snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                
                if title and url:
                    result = SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="startpage",
                        timestamp=datetime.now(),
                        relevance_score=self._calculate_relevance(title, snippet, query)
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.debug(f"Erro ao processar resultado Startpage: {e}")
                continue
        
        return results
    
    def _calculate_relevance(self, title: str, snippet: str, query: str) -> float:
        """Calcula score de relevância simples"""
        query_words = query.lower().split()
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        
        score = 0.0
        
        # Palavras no título valem mais
        for word in query_words:
            if word in title_lower:
                score += 2.0
            if word in snippet_lower:
                score += 1.0
        
        # Normalizar pelo número de palavras
        if query_words:
            score = score / len(query_words)
        
        return score
    
    def _deduplicate_and_rank(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicatas e ordena por relevância"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        # Ordenar por relevância
        return sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)
    
    async def get_page_content(self, url: str) -> Optional[str]:
        """Extrai conteúdo de uma página web"""
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove scripts e styles
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Extrai texto principal
                        return soup.get_text(separator=' ', strip=True)
                    else:
                        logger.warning(f"Erro ao acessar {url}: status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Erro ao extrair conteúdo de {url}: {e}")
            return None
    
    def clear_cache(self):
        """Limpa o cache de buscas"""
        self.cache_db.execute("DELETE FROM search_cache")
        self.cache_db.commit()
        logger.info("Cache de buscas limpo")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        cursor = self.cache_db.execute("SELECT COUNT(*) as total FROM search_cache")
        total = cursor.fetchone()[0]
        
        cursor = self.cache_db.execute("""
            SELECT COUNT(*) as recent 
            FROM search_cache 
            WHERE datetime(timestamp) > datetime('now', '-24 hours')
        """)
        recent = cursor.fetchone()[0]
        
        return {
            "total_cached_queries": total,
            "recent_queries_24h": recent,
            "cache_ttl_hours": self.config.cache_ttl_hours
        }

# Exemplo de uso
async def main():
    """Exemplo de uso do motor de busca"""
    from app.atena_config import AtenaConfig
    config = AtenaConfig()
    search_engine = AtenaWebSearchEngine(config)
    
    # Busca simples
    results = await search_engine.search("Python web scraping tutorial", max_results=10)
    
    print(f"Encontrados {len(results)} resultados:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   URL: {result.url}")
        print(f"   Fonte: {result.source}")
        print(f"   Relevância: {result.relevance_score:.2f}")
        print(f"   Snippet: {result.snippet[:100]}...")
    
    # Estatísticas do cache
    stats = search_engine.get_cache_stats()
    print(f"\nEstatísticas do cache: {stats}")

if __name__ == "__main__":
    asyncio.run(main())