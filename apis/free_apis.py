#!/usr/bin/env python3
"""
free_apis.py — Integração com APIs Gratuitas para Atena Evolução

APIs integradas:
- OpenWeather (clima)
- Wikipedia (conhecimento)
- DuckDuckGo (busca)
- arXiv (pesquisa acadêmica)
- GitHub (código)
- Dictionary (dicionário)
- Quotable (citações)
"""

import urllib.request
import urllib.parse
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AtenaFreeAPIs")


class FreeAPIManager:
    """Gerenciador de APIs gratuitas."""
    
    def __init__(self):
        self.apis = {
            "openweather": {
                "base_url": "https://api.openweathermap.org/data/2.5",
                "auth": "appid",
                "free": True,
            },
            "wikipedia": {
                "base_url": "https://en.wikipedia.org/w/api.php",
                "auth": "none",
                "free": True,
            },
            "duckduckgo": {
                "base_url": "https://api.duckduckgo.com",
                "auth": "none",
                "free": True,
            },
            "arxiv": {
                "base_url": "https://export.arxiv.org/api/query",
                "auth": "none",
                "free": True,
            },
            "github": {
                "base_url": "https://api.github.com",
                "auth": "optional",
                "free": True,
            },
            "dictionary": {
                "base_url": "https://api.dictionaryapi.dev/api/v2/entries/en",
                "auth": "none",
                "free": True,
            },
            "quotable": {
                "base_url": "https://api.quotable.io",
                "auth": "none",
                "free": True,
            },
        }
    
    async def search_wikipedia(self, query: str, lang: str = "pt") -> Dict:
        """Busca na Wikipedia."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5,
            "lang": lang
        }
        url = f"https://{lang}.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Erro Wikipedia: {e}")
            return {"error": str(e)}
    
    async def search_arxiv(self, query: str, max_results: int = 5) -> Dict:
        """Busca papers no arXiv."""
        params = {
            "search_query": f"all:{query}",
            "max_results": max_results,
            "sortBy": "relevance"
        }
        url = f"https://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&max_results={max_results}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode('utf-8')
                # Parse XML to dict (simplified)
                import re
                titles = re.findall(r'<title>(.*?)</title>', content)
                summaries = re.findall(r'<summary>(.*?)</summary>', content, re.DOTALL)
                return {
                    "titles": titles[:max_results],
                    "summaries": [s.strip()[:200] for s in summaries[:max_results]]
                }
        except Exception as e:
            logger.error(f"Erro arXiv: {e}")
            return {"error": str(e)}
    
    async def search_duckduckgo(self, query: str) -> Dict:
        """Busca no DuckDuckGo."""
        params = {"q": query, "format": "json", "no_html": "1"}
        url = f"https://api.duckduckgo.com/?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Erro DuckDuckGo: {e}")
            return {"error": str(e)}
    
    async def get_weather(self, city: str, api_key: str = "") -> Dict:
        """Obtém clima atual."""
        if not api_key:
            # Usar wttr.in como fallback (sem API key)
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"Erro wttr.in: {e}")
                return {"error": str(e)}
        
        params = {"q": city, "appid": api_key, "units": "metric", "lang": "pt"}
        url = f"https://api.openweathermap.org/data/2.5/weather?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Erro OpenWeather: {e}")
            return {"error": str(e)}
    
    async def get_quote(self) -> Dict:
        """Obtém citação aleatória."""
        try:
            req = urllib.request.Request(
                "https://api.quotable.io/random",
                headers={'User-Agent': 'AtenaEvolution/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Erro Quotable: {e}")
            return {"error": str(e)}
    
    async def get_definition(self, word: str) -> Dict:
        """Obtém definição de palavra."""
        try:
            req = urllib.request.Request(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}",
                headers={'User-Agent': 'AtenaEvolution/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Erro Dictionary: {e}")
            return {"error": str(e)}
    
    async def get_weather_data(self, city: str, api_key: str = "") -> Dict:
        """
        Obtém dados climáticos de uma cidade.
        
        Usa wttr.in como fallback (sem API key).
        Usa OpenWeather se API key fornecida.
        
        Args:
            city: Nome da cidade
            api_key: API key do OpenWeather (opcional)
            
        Returns:
            Dict com dados climáticos
        """
        # Tentar wttr.in primeiro (gratuito, sem key)
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
                # Formatar resposta para compatibilidade
                current = data.get("current_condition", [{}])[0]
                return {
                    "name": city,
                    "main": {
                        "temp": float(current.get("temp_C", 0)),
                        "humidity": float(current.get("humidity", 0)),
                        "pressure": float(current.get("pressure", 0)),
                    },
                    "weather": [{
                        "description": current.get("weatherDesc", [{}])[0].get("value", ""),
                        "main": current.get("weatherDesc", [{}])[0].get("value", ""),
                    }],
                    "wind": {
                        "speed": float(current.get("windspeedKmph", 0)),
                    },
                    "source": "wttr.in",
                }
        except Exception as e:
            logger.warning(f"wttr.in falhou: {e}")
        
        # Fallback: OpenWeather (requer API key)
        if api_key:
            try:
                params = {"q": city, "appid": api_key, "units": "metric", "lang": "pt"}
                url = f"https://api.openweathermap.org/data/2.5/weather?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'AtenaEvolution/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"OpenWeather falhou: {e}")
        
        return {"error": "Não foi possível obter dados climáticos"}
