#!/usr/bin/env python3
"""
Roteador Inteligente de Modelos - Atena Evolucao
==================================================

Escolhe automaticamente o melhor modelo baseado em:
1. Complexidade da tarefa (simples/media/complexa)
2. RAM disponivel (adaptativo)
3. Velocidade necessaria (rapida/padrao/qualidade)
4. Cache de performance (historico de respostas)

Estrategia:
- Tarefas simples + RAM baixa  -> phi4-mini (rapido, 3.8B)
- Tarefas medias  + RAM media  -> hermes3:8b (balanceado)
- Tarefas complexas           -> hermes3:8b com max_tokens alto
- RAM critica (<500MB)         -> gemma4:e2b (menor footprint)

Custo: ZERO (100% local)
"""
import json
import os
import sys
import time
import logging
import urllib.request
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configuracao
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
REQUEST_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "180"))

logger = logging.getLogger("RoteadorInteligente")


class Complexidade(Enum):
    """Niveis de complexidade da tarefa."""
    SIMPLES = "simples"       # saudacoes, confirmacoes, perguntas curtas
    MEDIA = "media"           # explicacoes, resumos, codigo simples
    COMPLEXA = "complexa"     # analise longa, raciocinio multi-step, escrita


class Velocidade(Enum):
    """Prioridade de velocidade."""
    RAPIDA = "rapida"         # resposta imediata (chat, suporte)
    PADRAO = "padrao"         # equilibrio
    QUALIDADE = "qualidade"   # melhor qualidade possivel (mais lento)


@dataclass
class ModeloInfo:
    """Informacoes de um modelo."""
    nome: str
    parametros: str           # ex: "8B", "3.8B"
    tamanho_gb: float         # tamanho em disco
    velocidade_relativa: float  # 1.0 = mais rapido
    qualidade: float          # 0-1 qualidade media
    ram_estimada_gb: float    # RAM estimada para carregar
    tarefas_ideais: List[str]


@dataclass
class ResultadoResposta:
    """Resultado de uma resposta do roteador."""
    resposta: str
    modelo_usado: str
    tempo_segundos: float
    tokens_gerados: int
    complexidade_detectada: str
    modo_roteamento: str


@dataclass
class PerformanceEntry:
    """Historico de performance de um modelo."""
    modelo: str
    tarefa: str
    tempo: float
    tokens: int
    satisfacao: bool          # avaliacao implicita (resposta nao vazia)
    timestamp: float = field(default_factory=time.time)


class ModelRegistry:
    """Registro de modelos disponiveis com suas caracteristicas."""
    
    def __init__(self):
        self.modelos: Dict[str, ModeloInfo] = {}
        self.performance_history: List[PerformanceEntry] = []
        self._detect_modelos()
    
    def _detect_modelos(self):
        """Detecta modelos disponiveis no Ollama."""
        modelos_detectados = []
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for m in data.get("data", data.get("models", [])):
                    nome = m["name"]
                    size_gb = m.get("size", 0) / (1024**3)
                    params = m.get("details", {}).get("parameter_size", "?")
                    modelos_detectados.append((nome, size_gb, params))
        except Exception as e:
            logger.warning(f"Nao foi possivel detectar modelos: {e}")
        
        # Mapear modelos conhecidos
        for nome, size_gb, params in modelos_detectados:
            info = self._get_model_info(nome, size_gb, params)
            if info:
                self.modelos[nome] = info
        
        # Fallback: se nenhum detectado, usar modelos padrao
        if not self.modelos:
            self._set_defaults()
    
    def _get_model_info(self, nome: str, size_gb: float, params: str) -> Optional[ModeloInfo]:
        """Retorna info do modelo baseado no nome."""
        mapeamento = {
            "hermes3:8b": ModeloInfo(
                nome="hermes3:8b", parametros="8B", tamanho_gb=size_gb,
                velocidade_relativa=1.5, qualidade=0.85, ram_estimada_gb=6.0,
                tarefas_ideais=["conversacao", "analise", "codigo", "escrita"]
            ),
            "phi4-mini:latest": ModeloInfo(
                nome="phi4-mini:latest", parametros="3.8B", tamanho_gb=size_gb,
                velocidade_relativa=1.0, qualidade=0.70, ram_estimada_gb=3.5,
                tarefas_ideais=["saudacao", "confirmacao", "traducao", "classificacao"]
            ),
            "gemma4:e2b": ModeloInfo(
                nome="gemma4:e2b", parametros="5.1B", tamanho_gb=size_gb,
                velocidade_relativa=2.0, qualidade=0.75, ram_estimada_gb=4.5,
                tarefas_ideais=["conversacao_leve", "resumo_curto"]
            ),
            "gemma4:e4b": ModeloInfo(
                nome="gemma4:e4b", parametros="8B", tamanho_gb=size_gb,
                velocidade_relativa=2.5, qualidade=0.80, ram_estimada_gb=7.0,
                tarefas_ideais=["analise_media", "raciocinio"]
            ),
            "qwen3:8b": ModeloInfo(
                nome="qwen3:8b", parametros="8.2B", tamanho_gb=size_gb,
                velocidade_relativa=1.8, qualidade=0.82, ram_estimada_gb=6.5,
                tarefas_ideais=["codigo", "raciocinio", "chines"]
            ),
        }
        
        # Buscar por match parcial (para versoes :latest, etc)
        for key, info in mapeamento.items():
            key_base = key.split(":")[0]
            if key_base in nome or nome.startswith(key_base):
                # Atualizar tamanho detectado
                info.tamanho_gb = size_gb
                return info
        return None
    
    def _set_defaults(self):
        """Define modelos padrao se deteccao falhar."""
        self.modelos["phi4-mini:latest"] = ModeloInfo(
            nome="phi4-mini:latest", parametros="3.8B", tamanho_gb=2.3,
            velocidade_relativa=1.0, qualidade=0.70, ram_estimada_gb=3.5,
            tarefas_ideais=["rapido", "simples"]
        )
        self.modelos["hermes3:8b"] = ModeloInfo(
            nome="hermes3:8b", parametros="8B", tamanho_gb=4.5,
            velocidade_relativa=1.5, qualidade=0.85, ram_estimada_gb=6.0,
            tarefas_ideais=["qualidade", "complexo"]
        )
    
    def get_modelos(self) -> List[str]:
        return list(self.modelos.keys())
    
    def get_info(self, nome: str) -> Optional[ModeloInfo]:
        return self.modelos.get(nome)
    
    def registrar_performance(self, entry: PerformanceEntry):
        """Registra resultado de uma resposta para aprendizado."""
        self.performance_history.append(entry)
        # Manter apenas ultimos 100 registros
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def get_tempo_medio(self, modelo: str) -> Optional[float]:
        """Retorna tempo medio de resposta de um modelo."""
        tempos = [e.tempo for e in self.performance_history if e.modelo == modelo]
        if not tempos:
            return None
        return sum(tempos) / len(tempos)


class ClassificadorTarefa:
    """Classifica a complexidade da tarefa do usuario."""
    
    # Palavras-chave para cada complexidade
    PADROES_SIMPLES = [
        "oi", "ola", "opa", "eae", "bom dia", "boa tarde", "boa noite",
        "sim", "nao", "ok", "valeu", "obrigado", "tchau", "ate",
        "quem e", "qual e", "como vai", "tudo bem",
    ]
    
    PADROES_MEDIOS = [
        "explique", "resuma", "liste", "mostre", "descreva",
        "compare", "converta", "calcule", "verifique",
        "como fazer", "como funciona", "o que e",
    ]
    
    PADROES_COMPLEXOS = [
        "analise", "escreva", "crie", "desenvolva", "implemente",
        "otimize", "refatore", "projete", "pesquise", "compare detalhadamente",
        "explique detalhadamente", "raciocine", "pense passo a passo",
    ]
    
    @classmethod
    def classificar(cls, texto: str) -> Complexidade:
        """Classifica a complexidade do texto."""
        texto_lower = texto.lower()
        
        # Contar palavras (heuristica simples)
        palavras = texto_lower.split()
        
        # Tarefas muito curtas -> simples
        if len(palavras) <= 5:
            for padrao in cls.PADROES_SIMPLES:
                if padrao in texto_lower:
                    return Complexidade.SIMPLES
        
        # Verificar padroes complexos primeiro (mais especifico)
        for padrao in cls.PADROES_COMPLEXOS:
            if padrao in texto_lower:
                return Complexidade.COMPLEXA
        
        # Padroes medios
        for padrao in cls.PADROES_MEDIOS:
            if padrao in texto_lower:
                return Complexidade.MEDIA
        
        # Texto longo sem padroes especificos -> media
        if len(palavras) > 20:
            return Complexidade.MEDIA
        
        return Complexidade.SIMPLES


class RoteadorInteligente:
    """
    Roteador que escolhe o melhor modelo para cada tarefa.
    
    Combina:
    - Complexidade da tarefa
    - RAM disponivel
    - Performance historica
    - Velocidade necessaria
    """
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.classificador = ClassificadorTarefa()
        self.logger = logging.getLogger("Roteador")
    
    def _get_ram_livre_mb(self) -> float:
        """Estima RAM livre em MB."""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullAvailPhys / (1024**2)
        except:
            return 2048  # fallback: assume 2GB livre
    
    def escolher_modelo(self, tarefa: str,
                        velocidade: Velocidade = Velocidade.PADRAO) -> str:
        """
        Escolhe o melhor modelo para a tarefa.
        
        Returns:
            Nome do modelo selecionado
        """
        complexidade = self.classificador.classificar(tarefa)
        ram_livre = self._get_ram_livre_mb()
        modelos = self.registry.get_modelos()
        
        self.logger.debug(f"Tarefa: {complexidade.value}, RAM: {ram_livre:.0f}MB, "
                         f"Velocidade: {velocidade.value}, Modelos: {len(modelos)}")
        
        # Se RAM critica (<1.5GB), usar modelo mais leve
        if ram_livre < 1500:
            for nome in modelos:
                info = self.registry.get_info(nome)
                if info and info.ram_estimada_gb < 4.0:
                    self.logger.info(f"RAM critica -> modelo leve: {nome}")
                    return nome
        
        # Roteamento por complexidade + velocidade
        if complexidade == Complexidade.SIMPLES:
            # Tarefas simples: priorizar velocidade
            if velocidade in [Velocidade.RAPIDA, Velocidade.PADRAO]:
                # Tentar modelo mais rapido
                candidatos = sorted(
                    modelos,
                    key=lambda n: self.registry.get_info(n).velocidade_relativa 
                    if self.registry.get_info(n) else 999
                )
                if candidatos:
                    return candidatos[0]
            else:
                # Qualidade mesmo para simples
                candidatos = sorted(
                    modelos,
                    key=lambda n: self.registry.get_info(n).qualidade 
                    if self.registry.get_info(n) else 0,
                    reverse=True
                )
                if candidatos:
                    return candidatos[0]
        
        elif complexidade == Complexidade.MEDIA:
            # Tarefas medias: equilibrio
            if velocidade == Velocidade.RAPIDA:
                # Primeiro rapido que funcione
                for nome in ["phi4-mini:latest", "hermes3:8b"]:
                    if nome in modelos:
                        return nome
            else:
                # Melhor qualidade viavel
                candidatos = sorted(
                    modelos,
                    key=lambda n: (
                        self.registry.get_info(n).qualidade * 0.7 +
                        (2.0 / self.registry.get_info(n).velocidade_relativa) * 0.3
                    ) if self.registry.get_info(n) else 0,
                    reverse=True
                )
                if candidatos:
                    return candidatos[0]
        
        else:  # COMPLEXA
            # Tarefas complexas: melhor qualidade possivel
            if velocidade == Velocidade.RAPIDA:
                # Rapido mas com qualidade
                if "hermes3:8b" in modelos:
                    return "hermes3:8b"
            else:
                # Melhor qualidade
                candidatos = sorted(
                    modelos,
                    key=lambda n: self.registry.get_info(n).qualidade 
                    if self.registry.get_info(n) else 0,
                    reverse=True
                )
                if candidatos:
                    return candidatos[0]
        
        # Fallback: primeiro modelo disponivel
        if modelos:
            return modelos[0]
        return "hermes3:8b"  # fallback absoluto
    
    def gerar_resposta(self, tarefa: str,
                       velocidade: Velocidade = Velocidade.PADRAO,
                       max_tokens: int = 512,
                       temperature: float = 0.7,
                       system: str = "") -> ResultadoResposta:
        """
        Gera resposta escolhendo o melhor modelo automaticamente.
        
        Args:
            tarefa: Pergunta/texto do usuario
            velocidade: Prioridade de velocidade
            max_tokens: Maximo de tokens
            temperature: Criatividade
            system: System prompt adicional
        
        Returns:
            ResultadoResposta com metadados do roteamento
        """
        # Escolher modelo
        modelo = self.escolher_modelo(tarefa, velocidade)
        complexidade = self.classificador.classificar(tarefa)
        
        # Detectar modo rapido vs qualidade
        modo = "rapido" if velocidade == Velocidade.RAPIDA else \
               "qualidade" if velocidade == Velocidade.QUALIDADE else "padrao"
        
        # Ajustar max_tokens pela complexidade
        if complexidade == Complexidade.COMPLEXA and max_tokens < 1024:
            max_tokens = 1024
        elif complexidade == Complexidade.SIMPLES and max_tokens > 256:
            max_tokens = 256
        
        # Gerar
        payload = {
            "model": modelo,
            "prompt": f"{system}\n\n{tarefa}" if system else tarefa,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                elapsed = time.time() - start
                
                resposta = result.get("response", "")
                tokens = result.get("eval_count", 0)
                
                # Registrar performance
                self.registry.registrar_performance(PerformanceEntry(
                    modelo=modelo,
                    tarefa=tarefa[:50],
                    tempo=elapsed,
                    tokens=tokens,
                    satisfacao=len(resposta) > 10
                ))
                
                return ResultadoResposta(
                    resposta=resposta,
                    modelo_usado=modelo,
                    tempo_segundos=elapsed,
                    tokens_gerados=tokens,
                    complexidade_detectada=complexidade.value,
                    modo_roteamento=modo
                )
        except Exception as e:
            elapsed = time.time() - start
            self.logger.error(f"Falha com {modelo}: {e}")
            
            # Tentar fallback
            if modelo != "phi4-mini:latest" and "phi4-mini:latest" in self.registry.get_modelos():
                self.logger.info("Fallback para phi4-mini")
                return self.gerar_resposta(
                    tarefa, velocidade, max_tokens, temperature, system
                )
            
            return ResultadoResposta(
                resposta=f"[ERRO] {str(e)[:100]}",
                modelo_usado=modelo,
                tempo_segundos=elapsed,
                tokens_gerados=0,
                complexidade_detectada=complexidade.value,
                modo_roteamento="erro"
            )
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatisticas do roteador."""
        stats = {
            "modelos_disponiveis": self.registry.get_modelos(),
            "ram_livre_mb": round(self._get_ram_livre_mb()),
            "historico_size": len(self.registry.performance_history),
        }
        
        # Estatisticas por modelo
        for modelo in self.registry.get_modelos():
            info = self.registry.get_info(modelo)
            tempo_medio = self.registry.get_tempo_medio(modelo)
            stats[f"modelo_{modelo}"] = {
                "parametros": info.parametros if info else "?",
                "velocidade": info.velocidade_relativa if info else "?",
                "qualidade": info.qualidade if info else "?",
                "tempo_medio": f"{tempo_medio:.1f}s" if tempo_medio else "?",
            }
        
        return stats


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    roteador = RoteadorInteligente()
    
    print("=" * 60)
    print("ROTEADOR INTELIGENTE - ATENA EVOLUCAO")
    print("=" * 60)
    
    # Mostrar estatisticas
    stats = roteador.get_estatisticas()
    print(f"\nRAM livre: {stats['ram_livre_mb']} MB")
    print(f"Modelos: {stats['modelos_disponiveis']}")
    print()
    
    # Testes de roteamento
    tarefas = [
        ("Ola, tudo bem?", Velocidade.RAPIDA),
        ("Explique como funciona a fotossintese.", Velocidade.PADRAO),
        ("Escreva um conto de 500 palavras sobre um viajante do tempo.", Velocidade.QUALIDADE),
    ]
    
    for tarefa, vel in tarefas:
        print(f"--- [{vel.value}] {tarefa[:50]} ---")
        resultado = roteador.gerar_resposta(tarefa, velocidade=vel)
        print(f"  Modelo: {resultado.modelo_usado}")
        print(f"  Complexidade: {resultado.complexidade_detectada}")
        print(f"  Tempo: {resultado.tempo_segundos:.1f}s")
        print(f"  Tokens: {resultado.tokens_gerados}")
        print(f"  Resposta: {resultado.resposta[:100]}...")
        print()
