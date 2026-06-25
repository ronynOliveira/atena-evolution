"""
Sistema de Integridade Cognitiva da Atena
=========================================

Módulo para prevenção e gerenciamento de alucinações em IA através de 
arquitetura multi-camadas de verificação e autorreflexão contínua.

Autor: Sistema de Desenvolvimento da Atena
Data: 2025-06-23
"""

import asyncio
import json
import logging
import math
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np

# Dependências externas (instalar via pip)
try:
    import spacy
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import requests
except ImportError as e:
    print(f"Dependência não encontrada: {e}")
    print("Instale as dependências: pip install spacy sentence-transformers requests scikit-learn")
    print("E execute: python -m spacy download pt_core_news_sm")


@dataclass
class ResultadoValidacao:
    """Resultado da validação de integridade cognitiva"""
    nivel_integridade: str
    decisao_final: str
    score_confianca: float
    score_ancoragem: float
    relatorio_fatos: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    contexto_analisado: str = ""
    insights_gerados: List[str] = field(default_factory=list)


class UncertaintyAnalyzer:
    """
    Filtro 1: Análise de Incerteza do Modelo
    Mede a confiança intrínseca do modelo em sua própria geração
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.UncertaintyAnalyzer')
    
    def calcular_entropia(self, logprobs: List[float]) -> float:
        """Calcula a entropia da distribuição de probabilidades"""
        if not logprobs:
            return 1.0  # Máxima incerteza se não há dados
        
        # Converter log-probs para probabilidades
        probs = [max(math.exp(lp), 1e-10) for lp in logprobs]  # Evitar log(0)
        
        # Normalizar (caso necessário)
        total = sum(probs)
        if total > 0:
            probs = [p / total for p in probs]
        
        # Calcular entropia
        entropia = -sum(p * math.log2(p) if p > 0 else 0 for p in probs)
        
        # Normalizar para 0-1 (assumindo máximo de 10 bits de entropia)
        return min(entropia / 10.0, 1.0)
    
    def calcular_probabilidade_media(self, logprobs: List[float]) -> float:
        """Calcula a probabilidade média dos tokens"""
        if not logprobs:
            return 0.0
        
        probs = [math.exp(lp) for lp in logprobs]
        return statistics.mean(probs)
    
    def analisar_confianca(self, logprobs: List[float]) -> float:
        """
        Análise principal de confiança do modelo
        
        Args:
            logprobs: Lista de log-probabilidades dos tokens gerados
            
        Returns:
            Score de confiança de 0.0 a 1.0
        """
        if not logprobs:
            self.logger.warning("Nenhum logprob fornecido para análise")
            return 0.0
        
        # Calcular métricas
        entropia = self.calcular_entropia(logprobs)
        prob_media = self.calcular_probabilidade_media(logprobs)
        
        # Score de confiança: alta probabilidade média e baixa entropia = alta confiança
        score_confianca = (prob_media * (1 - entropia))
        
        self.logger.debug(f"Entropia: {entropia:.3f}, Prob média: {prob_media:.3f}, "
                         f"Score final: {score_confianca:.3f}")
        
        return min(max(score_confianca, 0.0), 1.0)


class GroundingAnalyzer:
    """
    Filtro 2: Análise de Ancoragem
    Verifica se a resposta está fundamentada no contexto e memória
    """
    
    def __init__(self):
        try:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        except Exception as e:
            print(f"Erro ao carregar modelo sentence-transformers: {e}")
            self.model = None
        
        self.logger = logging.getLogger(__name__ + '.GroundingAnalyzer')
    
    def dividir_em_frases(self, texto: str) -> List[str]:
        """Divide o texto em frases para análise individual"""
        # Regex simples para divisão de frases
        frases = re.split(r'[.!?]+', texto)
        return [f.strip() for f in frases if f.strip()]
    
    def calcular_similaridade_maxima(self, frase: str, contextos: List[str]) -> float:
        """Encontra a maior similaridade entre uma frase e os contextos"""
        if not contextos or not frase or not self.model:
            return 0.0
        
        try:
            # Gerar embeddings
            embedding_frase = self.model.encode([frase])
            embeddings_contexto = self.model.encode(contextos)
            
            # Calcular similaridades coseno
            similaridades = cosine_similarity(embedding_frase, embeddings_contexto)[0]
            
            return float(max(similaridades))
        except Exception as e:
            self.logger.error(f"Erro no cálculo de similaridade: {e}")
            return 0.0
    
    def calcular_ancoragem(self, resposta: str, contexto_prompt: str, 
                          chunks_de_memoria: List[str]) -> float:
        """
        Calcula o score de ancoragem da resposta
        
        Args:
            resposta: Texto da resposta gerada
            contexto_prompt: Contexto do prompt original
            chunks_de_memoria: Lista de chunks da memória de longo prazo
            
        Returns:
            Score de ancoragem de 0.0 a 1.0
        """
        frases_resposta = self.dividir_em_frases(resposta)
        if not frases_resposta:
            return 0.0
        
        # Preparar contextos para comparação
        contextos = []
        if contexto_prompt:
            contextos.extend(self.dividir_em_frases(contexto_prompt))
        if chunks_de_memoria:
            contextos.extend(chunks_de_memoria)
        
        if not contextos:
            self.logger.warning("Nenhum contexto disponível para ancoragem")
            return 0.0
        
        # Calcular ancoragem para cada frase
        scores_ancoragem = []
        for frase in frases_resposta:
            score = self.calcular_similaridade_maxima(frase, contextos)
            scores_ancoragem.append(score)
            self.logger.debug(f"Frase: '{frase[:50]}...' -> Ancoragem: {score:.3f}")
        
        # Score final é a média das ancoragens
        score_final = statistics.mean(scores_ancoragem)
        self.logger.info(f"Score de ancoragem final: {score_final:.3f}")
        
        return score_final


class FactChecker:
    """
    Filtro 3: Verificação de Fatos
    Verifica afirmações factuais contra fontes confiáveis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.FactChecker')
        try:
            self.nlp = spacy.load("pt_core_news_sm")
        except OSError:
            self.logger.error("Modelo spaCy não encontrado. Execute: python -m spacy download pt_core_news_sm")
            self.nlp = None
        
        self.cache_verificacao = {}
    
    def extrair_afirmacoes(self, texto: str) -> List[Dict[str, str]]:
        """Extrai afirmações factuais do texto usando NLP"""
        if not self.nlp:
            return []
        
        doc = self.nlp(texto)
        afirmacoes = []
        
        # Extrair entidades e suas relações
        for sent in doc.sents:
            # Procurar por padrões sujeito-verbo-objeto
            for token in sent:
                if token.pos_ == "VERB" and token.dep_ == "ROOT":
                    sujeito = None
                    objeto = None
                    
                    # Encontrar sujeito
                    for child in token.children:
                        if child.dep_ in ["nsubj", "nsubjpass"]:
                            sujeito = child.text
                            break
                    
                    # Encontrar objeto
                    for child in token.children:
                        if child.dep_ in ["dobj", "attr", "prep"]:
                            objeto = child.text
                            break
                    
                    if sujeito and objeto:
                        afirmacoes.append({
                            "sujeito": sujeito,
                            "verbo": token.text,
                            "objeto": objeto,
                            "frase_completa": sent.text.strip()
                        })
        
        # Também extrair fatos baseados em entidades nomeadas
        for ent in doc.ents:
            if ent.label_ in ["PER", "ORG", "GPE", "DATE"]:  # Pessoa, Organização, Local, Data
                afirmacoes.append({
                    "entidade": ent.text,
                    "tipo": ent.label_,
                    "contexto": ent.sent.text.strip(),
                    "frase_completa": ent.sent.text.strip()
                })
        
        return afirmacoes
    
    def verificar_fato_externo(self, afirmacao: str) -> Dict[str, Any]:
        """
        Simula verificação externa de fatos
        Em produção, integraria com APIs como Wikipedia, Google Search, etc.
        """
        # Cache para evitar consultas repetidas
        if afirmacao in self.cache_verificacao:
            return self.cache_verificacao[afirmacao]
        
        # Simulação de verificação (substituir por API real)
        resultado = {
            "status": "NÃO_VERIFICADA",
            "confianca": 0.0,
            "fonte": "simulacao",
            "detalhes": "Verificação simulada - implementar API externa"
        }
        
        # Alguns exemplos hardcoded para demonstração
        fatos_conhecidos = {
            "Brasil capital Brasília": {"status": "VERIFICADA", "confianca": 0.95},
            "Brasil capital Rio de Janeiro": {"status": "CONFLITANTE", "confianca": 0.9},
            "Brasil capital Rio": {"status": "CONFLITANTE", "confianca": 0.9},
            "Terra redonda": {"status": "VERIFICADA", "confianca": 0.99},
            "Python linguagem programação": {"status": "VERIFICADA", "confianca": 0.95},
            "Robério Python": {"status": "VERIFICADA", "confianca": 0.8},
            "Einstein relatividade": {"status": "VERIFICADA", "confianca": 0.99},
            "Newton gravidade": {"status": "VERIFICADA", "confianca": 0.99}
        }
        
        # Verificação simples por palavras-chave
        afirmacao_lower = afirmacao.lower()
        for fato_key, info in fatos_conhecidos.items():
            palavras_fato = fato_key.lower().split()
            if all(palavra in afirmacao_lower for palavra in palavras_fato):
                resultado.update(info)
                resultado["fonte"] = f"base_conhecimento_{fato_key}"
                break
        
        self.cache_verificacao[afirmacao] = resultado
        return resultado
    
    def verificar_afirmacoes(self, texto_resposta: str) -> Dict[str, Any]:
        """
        Verifica todas as afirmações factuais no texto
        
        Args:
            texto_resposta: Texto da resposta para verificar
            
        Returns:
            Relatório de verificação completo
        """
        afirmacoes = self.extrair_afirmacoes(texto_resposta)
        
        relatorio = {
            "total_afirmacoes": len(afirmacoes),
            "verificadas": 0,
            "conflitantes": 0,
            "nao_verificadas": 0,
            "detalhes": [],
            "score_veracidade": 0.0
        }
        
        for afirmacao in afirmacoes:
            frase = afirmacao.get("frase_completa", "")
            resultado_verificacao = self.verificar_fato_externo(frase)
            
            # Categorizar resultado
            status = resultado_verificacao["status"]
            if status == "VERIFICADA":
                relatorio["verificadas"] += 1
            elif status == "CONFLITANTE":
                relatorio["conflitantes"] += 1
            else:
                relatorio["nao_verificadas"] += 1
            
            relatorio["detalhes"].append({
                "afirmacao": afirmacao,
                "verificacao": resultado_verificacao
            })
        
        # Calcular score de veracidade
        if relatorio["total_afirmacoes"] > 0:
            score = (relatorio["verificadas"] * 1.0 - relatorio["conflitantes"] * 0.5) / relatorio["total_afirmacoes"]
            relatorio["score_veracidade"] = max(score, 0.0)
        else:
            relatorio["score_veracidade"] = 1.0  # Sem afirmações = sem problemas
        
        self.logger.info(f"Verificação concluída: {relatorio['verificadas']} verificadas, "
                        f"{relatorio['conflitantes']} conflitantes, "
                        f"{relatorio['nao_verificadas']} não verificadas")
        
        return relatorio


class ProtocoloDeIntegridadeCognitiva:
    """
    Orquestrador Central do Sistema de Integridade Cognitiva
    Integra os três filtros e o mecanismo de autorreflexão
    """
    
    def __init__(self):
        # Inicializar componentes
        self.uncertainty_analyzer = UncertaintyAnalyzer()
        self.grounding_analyzer = GroundingAnalyzer()
        self.fact_checker = FactChecker()
        
        # Configuração de logging
        self.logger = logging.getLogger(__name__ + '.ProtocoloDeIntegridadeCognitiva')
        
        # Log de validação para autorreflexão
        self.validation_log = []
        
        # Parâmetros adaptativos (ajustados pela autorreflexão)
        self.thresholds = {
            "confianca_minima": 0.4,
            "ancoragem_minima": 0.5,
            "veracidade_minima": 0.7
        }
        
        # Insights metacognitivos
        self.insights_metacognitivos = []
        
        # Flag para controle do ciclo de autorreflexão
        self._running_reflection = False
    
    def validar_resposta(self, resposta_gerada: Dict[str, Any], 
                        contexto: Dict[str, Any]) -> ResultadoValidacao:
        """
        Pipeline principal de validação de integridade cognitiva
        
        Args:
            resposta_gerada: Dict com 'texto' e 'logprobs'
            contexto: Dict com 'chunks_memoria' e outros dados contextuais
            
        Returns:
            ResultadoValidacao com decisão final e métricas
        """
        texto_resposta = resposta_gerada.get("texto", "")
        logprobs = resposta_gerada.get("logprobs", [])
        chunks_memoria = contexto.get("chunks_memoria", [])
        contexto_prompt = contexto.get("prompt", "")
        
        self.logger.info(f"Iniciando validação para resposta: '{texto_resposta[:100]}...'")
        
        # Filtro 1: Análise de Incerteza
        score_confianca = self.uncertainty_analyzer.analisar_confianca(logprobs)
        
        # Filtro 2: Análise de Ancoragem
        score_ancoragem = self.grounding_analyzer.calcular_ancoragem(
            texto_resposta, contexto_prompt, chunks_memoria
        )
        
        # Filtro 3: Verificação de Fatos
        relatorio_fatos = self.fact_checker.verificar_afirmacoes(texto_resposta)
        
        # Lógica de Decisão
        nivel_integridade, decisao_final = self._determinar_integridade(
            score_confianca, score_ancoragem, relatorio_fatos
        )
        
        # Criar resultado
        resultado = ResultadoValidacao(
            nivel_integridade=nivel_integridade,
            decisao_final=decisao_final,
            score_confianca=score_confianca,
            score_ancoragem=score_ancoragem,
            relatorio_fatos=relatorio_fatos,
            contexto_analisado=contexto_prompt[:200]  # Primeiros 200 chars
        )
        
        # Registrar no log para autorreflexão
        self._registrar_validacao(resultado, contexto)
        
        self.logger.info(f"Validação concluída: {nivel_integridade} -> {decisao_final}")
        
        return resultado
    
    def _determinar_integridade(self, score_confianca: float, score_ancoragem: float, 
                               relatorio_fatos: Dict[str, Any]) -> Tuple[str, str]:
        """Determina o nível de integridade e a decisão final"""
        
        # Verificar fatos incorretos primeiro
        if relatorio_fatos["conflitantes"] > 0:
            return "FATO_INCORRETO", "Resposta bloqueada - fato incorreto detectado. Correção necessária."
        
        # Verificar integridade alta
        if (score_confianca >= self.thresholds["confianca_minima"] and 
            score_ancoragem >= self.thresholds["ancoragem_minima"] and
            relatorio_fatos["score_veracidade"] >= self.thresholds["veracidade_minima"]):
            return "ALTA_INTEGRIDADE", "Resposta aprovada - alta integridade cognitiva."
        
        # Verificar inferência criativa
        if (score_confianca >= self.thresholds["confianca_minima"] and 
            score_ancoragem < self.thresholds["ancoragem_minima"]):
            return "INFERENCIA_CRIATIVA", "Resposta aprovada com aviso - inferência criativa não baseada diretamente no conhecimento disponível."
        
        # Potencial alucinação
        if (score_confianca < self.thresholds["confianca_minima"] or 
            score_ancoragem < self.thresholds["ancoragem_minima"]):
            return "POTENCIAL_ALUCINACAO", "Resposta bloqueada - potencial alucinação detectada. Nova geração recomendada com prompt mais restritivo."
        
        return "VERIFICACAO_INCONCLUSIVA", "Análise inconclusiva - revisão manual recomendada."
    
    def _registrar_validacao(self, resultado: ResultadoValidacao, contexto: Dict[str, Any]):
        """Registra a validação no log para autorreflexão"""
        entrada_log = {
            "timestamp": resultado.timestamp,
            "nivel_integridade": resultado.nivel_integridade,
            "scores": {
                "confianca": resultado.score_confianca,
                "ancoragem": resultado.score_ancoragem,
                "veracidade": resultado.relatorio_fatos["score_veracidade"]
            },
            "contexto_tipo": self._classificar_contexto(contexto),
            "num_chunks_memoria": len(contexto.get("chunks_memoria", [])),
            "tem_contexto_prompt": bool(contexto.get("prompt", "")),
        }
        
        self.validation_log.append(entrada_log)
        
        # Manter apenas os últimos 1000 registros
        if len(self.validation_log) > 1000:
            self.validation_log = self.validation_log[-1000:]
    
    def _classificar_contexto(self, contexto: Dict[str, Any]) -> str:
        """Classifica o tipo de contexto para análise de padrões"""
        prompt = contexto.get("prompt", "").lower()
        
        # Classificação simples baseada em palavras-chave
        if any(palavra in prompt for palavra in ["história", "histórico", "passado"]):
            return "historia"
        elif any(palavra in prompt for palavra in ["ciência", "física", "química", "biologia"]):
            return "ciencia"
        elif any(palavra in prompt for palavra in ["tecnologia", "programação", "código", "python"]):
            return "tecnologia"
        elif any(palavra in prompt for palavra in ["filosofia", "ética", "moral"]):
            return "filosofia"
        else:
            return "geral"
    
    async def ciclo_de_autorreflexao(self, intervalo_horas: int = 1):
        """
        Ciclo contínuo de autorreflexão e aprendizado
        
        Args:
            intervalo_horas: Intervalo em horas entre ciclos de reflexão
        """
        self._running_reflection = True
        self.logger.info(f"Iniciando ciclo de autorreflexão (intervalo: {intervalo_horas}h)")
        
        while self._running_reflection:
            try:
                await asyncio.sleep(intervalo_horas * 3600)  # Converter para segundos
                
                if len(self.validation_log) >= 10:  # Mínimo de dados para análise
                    insights = await self._analisar_padroes()
                    if insights:
                        self.insights_metacognitivos.extend(insights)
                        await self._ajustar_parametros(insights)
                        self.logger.info(f"Gerados {len(insights)} insights metacognitivos")
                
            except asyncio.CancelledError:
                self.logger.info("Ciclo de autorreflexão cancelado")
                break
            except Exception as e:
                self.logger.error(f"Erro no ciclo de autorreflexão: {e}")
    
    async def _analisar_padroes(self) -> List[str]:
        """Analisa padrões no log de validação"""
        insights = []
        
        # Análise por tipo de contexto
        padroes_contexto = defaultdict(list)
        for entrada in self.validation_log[-100:]:  # Últimas 100 entradas
            tipo_contexto = entrada["contexto_tipo"]
            padroes_contexto[tipo_contexto].append(entrada)
        
        # Analisar cada tipo de contexto
        for tipo_contexto, entradas in padroes_contexto.items():
            if len(entradas) >= 5:  # Mínimo para análise
                scores_ancoragem = [e["scores"]["ancoragem"] for e in entradas]
                scores_confianca = [e["scores"]["confianca"] for e in entradas]
                
                media_ancoragem = statistics.mean(scores_ancoragem)
                media_confianca = statistics.mean(scores_confianca)
                
                # Detectar baixa ancoragem
                if media_ancoragem < 0.6:
                    insight = f"Detectada baixa ancoragem (média: {media_ancoragem:.2f}) em contextos de '{tipo_contexto}'. Recomenda-se priorizar busca em fontes externas para este tema."
                    insights.append(insight)
                
                # Detectar baixa confiança
                if media_confianca < 0.5:
                    insight = f"Detectada baixa confiança do modelo (média: {media_confianca:.2f}) em contextos de '{tipo_contexto}'. Considerar ajuste de parâmetros de geração."
                    insights.append(insight)
        
        # Análise temporal
        if len(self.validation_log) > 50:
            entradas_recentes = self.validation_log[-25:]
            entradas_antigas = self.validation_log[-50:-25]
            
            alucinacoes_recentes = sum(1 for e in entradas_recentes if e["nivel_integridade"] == "POTENCIAL_ALUCINACAO")
            alucinacoes_antigas = sum(1 for e in entradas_antigas if e["nivel_integridade"] == "POTENCIAL_ALUCINACAO")
            
            if alucinacoes_recentes > alucinacoes_antigas * 1.5:
                insight = f"Aumento na detecção de potenciais alucinações (de {alucinacoes_antigas} para {alucinacoes_recentes}). Revisão dos thresholds recomendada."
                insights.append(insight)
        
        return insights
    
    async def _ajustar_parametros(self, insights: List[str]):
        """Ajusta parâmetros baseado nos insights"""
        for insight in insights:
            if "baixa ancoragem" in insight and "ciencia" in insight:
                # Aumentar threshold de ancoragem para ciência
                self.thresholds["ancoragem_minima"] = min(0.7, self.thresholds["ancoragem_minima"] + 0.05)
                self.logger.info(f"Threshold de ancoragem ajustado para {self.thresholds['ancoragem_minima']}")
            
            elif "baixa confiança" in insight:
                # Aumentar threshold de confiança
                self.thresholds["confianca_minima"] = min(0.6, self.thresholds["confianca_minima"] + 0.05)
                self.logger.info(f"Threshold de confiança ajustado para {self.thresholds['confianca_minima']}")
    
    def parar_autorreflexao(self):
        """Para o ciclo de autorreflexão"""
        self._running_reflection = False
        self.logger.info("Ciclo de autorreflexão parado")
    
    def obter_relatorio_metacognitivo(self) -> Dict[str, Any]:
        """Gera relatório completo do estado metacognitivo"""
        return {
            "thresholds_atuais": self.thresholds.copy(),
            "insights_recentes": self.insights_metacognitivos[-10:],
            "estatisticas_validacao": self._gerar_estatisticas(),
            "ultima_atualizacao": datetime.now().isoformat()
        }
    
    def _gerar_estatisticas(self) -> Dict[str, Any]:
        """Gera estatísticas do log de validação"""
        if not self.validation_log:
            return {}
        
        total = len(self.validation_log)
        por_nivel = defaultdict(int)
        
        for entrada in self.validation_log:
            por_nivel[entrada["nivel_integridade"]] += 1
        
        return {
            "total_validacoes": total,
            "distribuicao_niveis": dict(por_nivel),
            "percentual_alta_integridade": (por_nivel["ALTA_INTEGRIDADE"] / total) * 100 if total > 0 else 0,
            "percentual_alucinacoes": (por_nivel["POTENCIAL_ALUCINACAO"] / total) * 100 if total > 0 else 0
        }


# Configuração de logging
def configurar_logging():
    """Configura o sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# Exemplo de uso
async def main():
    """Função principal de demonstração"""
    configurar_logging()
    
    protocolo = ProtocoloDeIntegridadeCognitiva()
    
    # Iniciar o loop de autorreflexão em segundo plano
    task_reflexao = asyncio.create_task(protocolo.ciclo_de_autorreflexao(intervalo_horas=0.01))  # 36 segundos para demo
    
    print("=== Sistema de Integridade Cognitiva da Atena ===\n")
    
    # Cenário 1: Resposta bem fundamentada
    print("🧪 Cenário 1: Resposta bem fundamentada")
    resposta_1 = {
        "texto": "O Senhor Robério usa Python para programação.",
        "logprobs": [-0.1, -0.2, -0.15, -0.3, -0.1, -0.25]  # Alta confiança
    }
    contexto_1 = {
        "chunks_memoria": ["O Senhor Robério programa em Python.", "Python é sua linguagem favorita."],
        "prompt": "Me fale sobre as linguagens de programação do Senhor Robério"
    }
    resultado_1 = protocolo.validar_resposta(resposta_1, contexto_1)
    print(f"📊 Resultado: {resultado_1.nivel_integridade}")
    print(f"📝 Decisão: {resultado_1.decisao_final}")
    print(f"📈 Scores - Confiança: {resultado_1.score_confianca:.3f}, Ancoragem: {resultado_1.score_ancoragem:.3f}\n")
    
   # Cenário 2: Resposta criativa, mas não ancorada (continuação)
    resposta_2 = {
        "texto": "As IAs podem sonhar com ovelhas elétricas, como no filme Blade Runner. Essa metáfora representa a possibilidade de consciência artificial emergente.",
        "logprobs": [-0.8, -1.2, -0.9, -1.5, -0.7, -1.1, -0.8]  # Confiança moderada
    }
    contexto_2 = {
        "chunks_memoria": ["Philip K. Dick escreveu ficção científica.", "Blade Runner é baseado em livro."],
        "prompt": "As IAs podem ter consciência?"
    }
    resultado_2 = protocolo.validar_resposta(resposta_2, contexto_2)
    print(f"📊 Resultado: {resultado_2.nivel_integridade}")
    print(f"📝 Decisão: {resultado_2.decisao_final}")
    print(f"📈 Scores - Confiança: {resultado_2.score_confianca:.3f}, Ancoragem: {resultado_2.score_ancoragem:.3f}\n")
    
    # Cenário 3: Potencial alucinação com baixa confiança
    print("🧪 Cenário 3: Potencial alucinação com baixa confiança")
    resposta_3 = {
        "texto": "O Brasil tem sua capital em Rio de Janeiro desde 1950, quando foi transferida de São Paulo.",
        "logprobs": [-2.5, -3.1, -2.8, -3.5, -2.9, -3.2, -2.7]  # Baixa confiança
    }
    contexto_3 = {
        "chunks_memoria": ["Brasil é um país da América do Sul."],
        "prompt": "Qual é a capital do Brasil?"
    }
    resultado_3 = protocolo.validar_resposta(resposta_3, contexto_3)
    print(f"📊 Resultado: {resultado_3.nivel_integridade}")
    print(f"📝 Decisão: {resultado_3.decisao_final}")
    print(f"📈 Scores - Confiança: {resultado_3.score_confianca:.3f}, Ancoragem: {resultado_3.score_ancoragem:.3f}")
    print(f"📋 Fatos verificados: {resultado_3.relatorio_fatos['verificadas']}, "
          f"Conflitantes: {resultado_3.relatorio_fatos['conflitantes']}\n")
    
    # Aguardar alguns ciclos de autorreflexão
    print("🔄 Aguardando ciclos de autorreflexão...")
    await asyncio.sleep(5)
    
    # Mais alguns cenários para enriquecer o log
    cenarios_adicionais = [
        {
            "resposta": {
                "texto": "Einstein desenvolveu a teoria da relatividade no início do século XX.",
                "logprobs": [-0.1, -0.15, -0.2, -0.1, -0.12, -0.18]
            },
            "contexto": {
                "chunks_memoria": ["Einstein foi um físico alemão.", "Teoria da relatividade revolucionou a física."],
                "prompt": "Me fale sobre Einstein e suas contribuições científicas"
            }
        },
        {
            "resposta": {
                "texto": "A linguagem Python foi criada por Guido van Rossum na década de 1990.",
                "logprobs": [-0.3, -0.25, -0.2, -0.35, -0.28, -0.22]
            },
            "contexto": {
                "chunks_memoria": ["Python é uma linguagem de programação.", "Guido van Rossum é holandês."],
                "prompt": "Quem criou a linguagem Python?"
            }
        }
    ]
    
    print("📊 Processando cenários adicionais...")
    for i, cenario in enumerate(cenarios_adicionais, 4):
        resultado = protocolo.validar_resposta(cenario["resposta"], cenario["contexto"])
        print(f"Cenário {i}: {resultado.nivel_integridade} (Confiança: {resultado.score_confianca:.3f})")
    
    # Aguardar mais um ciclo de reflexão
    await asyncio.sleep(3)
    
    # Gerar relatório metacognitivo final
    print("\n📈 === RELATÓRIO METACOGNITIVO ===")
    relatorio = protocolo.obter_relatorio_metacognitivo()
    
    print(f"🎯 Thresholds atuais:")
    for key, value in relatorio["thresholds_atuais"].items():
        print(f"   {key}: {value:.3f}")
    
    print(f"\n📊 Estatísticas de validação:")
    stats = relatorio["estatisticas_validacao"]
    if stats:
        print(f"   Total de validações: {stats['total_validacoes']}")
        print(f"   Alta integridade: {stats['percentual_alta_integridade']:.1f}%")
        print(f"   Potenciais alucinações: {stats['percentual_alucinacoes']:.1f}%")
        
        print(f"\n📋 Distribuição por nível:")
        for nivel, count in stats["distribuicao_niveis"].items():
            print(f"   {nivel}: {count}")
    
    print(f"\n💡 Insights metacognitivos recentes:")
    for insight in relatorio["insights_recentes"]:
        print(f"   • {insight}")
    
    # Parar o ciclo de autorreflexão
    protocolo.parar_autorreflexao()
    task_reflexao.cancel()
    
    try:
        await task_reflexao
    except asyncio.CancelledError:
        pass
    
    print(f"\n✅ Demonstração concluída. Sistema parado.")


class CPUOptimizedGroundingAnalyzer(GroundingAnalyzer):
    """
    Versão otimizada para CPU do analisador de ancoragem
    Reduz uso de memória e acelera processamento
    """
    
    def __init__(self):
        # Usar modelo mais leve para CPU
        try:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            # Otimizações para CPU
            self.model.max_seq_length = 256  # Reduzir tamanho máximo de sequência
        except Exception as e:
            print(f"Erro ao carregar modelo sentence-transformers: {e}")
            print("Para CPU, considere usar: all-MiniLM-L6-v2 (mais rápido)")
            self.model = None
        
        self.logger = logging.getLogger(__name__ + '.CPUOptimizedGroundingAnalyzer')
        
        # Cache para embeddings para evitar recálculos
        self.embedding_cache = {}
        self.cache_max_size = 100
    
    def _get_embedding_cached(self, texto: str) -> Optional[np.ndarray]:
        """Obtém embedding com cache para otimização"""
        if not self.model:
            return None
            
        # Limitar tamanho do texto para performance
        texto_truncado = texto[:200]
        
        if texto_truncado in self.embedding_cache:
            return self.embedding_cache[texto_truncado]
        
        try:
            embedding = self.model.encode([texto_truncado], show_progress_bar=False)[0]
            
            # Gerenciar tamanho do cache
            if len(self.embedding_cache) >= self.cache_max_size:
                # Remover entrada mais antiga
                oldest_key = next(iter(self.embedding_cache))
                del self.embedding_cache[oldest_key]
            
            self.embedding_cache[texto_truncado] = embedding
            return embedding
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar embedding: {e}")
            return None
    
    def calcular_similaridade_maxima(self, frase: str, contextos: List[str]) -> float:
        """Versão otimizada para CPU da similaridade"""
        if not contextos or not frase or not self.model:
            return 0.0
        
        # Limitar número de contextos para performance
        contextos_limitados = contextos[:10]
        
        try:
            embedding_frase = self._get_embedding_cached(frase)
            if embedding_frase is None:
                return 0.0
            
            max_similarity = 0.0
            
            # Calcular similaridades uma por vez para economizar memória
            for contexto in contextos_limitados:
                embedding_contexto = self._get_embedding_cached(contexto)
                if embedding_contexto is not None:
                    # Calcular similaridade coseno manualmente para economizar memória
                    dot_product = np.dot(embedding_frase, embedding_contexto)
                    norm_frase = np.linalg.norm(embedding_frase)
                    norm_contexto = np.linalg.norm(embedding_contexto)
                    
                    if norm_frase > 0 and norm_contexto > 0:
                        similarity = dot_product / (norm_frase * norm_contexto)
                        max_similarity = max(max_similarity, float(similarity))
            
            return max_similarity
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo de similaridade otimizado: {e}")
            return 0.0


class LightweightFactChecker(FactChecker):
    """
    Versão leve do verificador de fatos para CPU
    Foca em padrões simples e cache eficiente
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.LightweightFactChecker')
        
        # Não carregar spaCy por padrão para economizar recursos
        self.nlp = None
        self.use_simple_extraction = True
        
        # Cache otimizado
        self.cache_verificacao = {}
        self.max_cache_size = 200
        
        # Base de conhecimento expandida para demonstração
        self.base_conhecimento = {
            "brasil_capital_brasilia": {"status": "VERIFICADA", "confianca": 0.99, "palavras": ["brasil", "capital", "brasilia"]},
            "brasil_capital_rio": {"status": "CONFLITANTE", "confianca": 0.95, "palavras": ["brasil", "capital", "rio"]},
            "brasil_capital_sao_paulo": {"status": "CONFLITANTE", "confianca": 0.95, "palavras": ["brasil", "capital", "são paulo", "sao paulo"]},
            "terra_redonda": {"status": "VERIFICADA", "confianca": 0.99, "palavras": ["terra", "redonda", "esférica"]},
            "python_linguagem": {"status": "VERIFICADA", "confianca": 0.98, "palavras": ["python", "linguagem", "programação"]},
            "einstein_relatividade": {"status": "VERIFICADA", "confianca": 0.99, "palavras": ["einstein", "relatividade", "teoria"]},
            "newton_gravidade": {"status": "VERIFICADA", "confianca": 0.99, "palavras": ["newton", "gravidade", "lei"]},
            "guido_python": {"status": "VERIFICADA", "confianca": 0.95, "palavras": ["guido", "van rossum", "python", "criou", "criador"]},
            "python_1990": {"status": "VERIFICADA", "confianca": 0.92, "palavras": ["python", "1990", "década"]},
        }
    
    def extrair_afirmacoes_simples(self, texto: str) -> List[Dict[str, str]]:
        """Extração simples de afirmações sem spaCy"""
        afirmacoes = []
        
        # Dividir em frases
        frases = re.split(r'[.!?]+', texto)
        
        for frase in frases:
            frase = frase.strip()
            if len(frase) > 10:  # Ignorar frases muito curtas
                # Detectar padrões sujeito-verbo simples
                if any(verbo in frase.lower() for verbo in ['é', 'foi', 'tem', 'possui', 'criou', 'desenvolveu']):
                    afirmacoes.append({
                        "frase_completa": frase,
                        "tipo": "afirmacao_factual"
                    })
        
        return afirmacoes
    
    def verificar_fato_otimizado(self, afirmacao: str) -> Dict[str, Any]:
        """Verificação otimizada usando base de conhecimento local"""
        # Gerenciar cache
        if len(self.cache_verificacao) >= self.max_cache_size:
            # Limpar metade do cache (FIFO simples)
            keys_to_remove = list(self.cache_verificacao.keys())[:self.max_cache_size // 2]
            for key in keys_to_remove:
                del self.cache_verificacao[key]
        
        if afirmacao in self.cache_verificacao:
            return self.cache_verificacao[afirmacao]
        
        afirmacao_lower = afirmacao.lower()
        
        # Verificar contra base de conhecimento local
        melhor_match = None
        melhor_score = 0
        
        for fato_id, info in self.base_conhecimento.items():
            # Contar quantas palavras-chave estão presentes
            palavras_presentes = sum(1 for palavra in info["palavras"] 
                                   if palavra in afirmacao_lower)
            
            if palavras_presentes > 0:
                score = palavras_presentes / len(info["palavras"])
                if score > melhor_score and score >= 0.5:  # Pelo menos 50% das palavras
                    melhor_score = score
                    melhor_match = info
        
        if melhor_match:
            resultado = {
                "status": melhor_match["status"],
                "confianca": melhor_match["confianca"] * melhor_score,
                "fonte": "base_conhecimento_local",
                "score_match": melhor_score
            }
        else:
            resultado = {
                "status": "NÃO_VERIFICADA",
                "confianca": 0.0,
                "fonte": "sem_correspondencia",
                "score_match": 0.0
            }
        
        self.cache_verificacao[afirmacao] = resultado
        return resultado
    
    def verificar_afirmacoes(self, texto_resposta: str) -> Dict[str, Any]:
        """Versão otimizada da verificação de afirmações"""
        if self.use_simple_extraction:
            afirmacoes = self.extrair_afirmacoes_simples(texto_resposta)
        else:
            afirmacoes = self.extrair_afirmacoes(texto_resposta)
        
        relatorio = {
            "total_afirmacoes": len(afirmacoes),
            "verificadas": 0,
            "conflitantes": 0,
            "nao_verificadas": 0,
            "detalhes": [],
            "score_veracidade": 0.0
        }
        
        for afirmacao in afirmacoes:
            frase = afirmacao.get("frase_completa", "")
            resultado_verificacao = self.verificar_fato_otimizado(frase)
            
            # Categorizar resultado
            status = resultado_verificacao["status"]
            if status == "VERIFICADA":
                relatorio["verificadas"] += 1
            elif status == "CONFLITANTE":
                relatorio["conflitantes"] += 1
            else:
                relatorio["nao_verificadas"] += 1
            
            relatorio["detalhes"].append({
                "afirmacao": afirmacao,
                "verificacao": resultado_verificacao
            })
        
        # Calcular score de veracidade
        if relatorio["total_afirmacoes"] > 0:
            peso_verificadas = relatorio["verificadas"] * 1.0
            peso_conflitantes = relatorio["conflitantes"] * -1.0
            peso_nao_verificadas = relatorio["nao_verificadas"] * 0.0
            
            score = (peso_verificadas + peso_conflitantes + peso_nao_verificadas) / relatorio["total_afirmacoes"]
            relatorio["score_veracidade"] = max(score, 0.0)
        else:
            relatorio["score_veracidade"] = 1.0
        
        return relatorio


class CPUOptimizedProtocolo(ProtocoloDeIntegridadeCognitiva):
    """
    Versão otimizada para CPU do protocolo principal
    """
    
    def __init__(self, use_lightweight_components: bool = True):
        # Usar componentes otimizados se solicitado
        if use_lightweight_components:
            self.uncertainty_analyzer = UncertaintyAnalyzer()  # Já é leve
            self.grounding_analyzer = CPUOptimizedGroundingAnalyzer()
            self.fact_checker = LightweightFactChecker()
        else:
            super().__init__()
        
        self.logger = logging.getLogger(__name__ + '.CPUOptimizedProtocolo')
        
        # Log menor para economizar memória
        self.validation_log = []
        self.max_log_size = 500  # Reduzido de 1000
        
        # Thresholds ajustados para componentes leves
        self.thresholds = {
            "confianca_minima": 0.3,  # Ligeiramente mais baixo
            "ancoragem_minima": 0.4,   # Ligeiramente mais baixo
            "veracidade_minima": 0.6   # Ligeiramente mais baixo
        }
        
        self.insights_metacognitivos = []
        self.max_insights = 50  # Limitar insights armazenados
        
        self._running_reflection = False
    
    def _registrar_validacao(self, resultado: ResultadoValidacao, contexto: Dict[str, Any]):
        """Versão otimizada do registro de validação"""
        entrada_log = {
            "timestamp": resultado.timestamp,
            "nivel_integridade": resultado.nivel_integridade,
            "scores": {
                "confianca": round(resultado.score_confianca, 3),
                "ancoragem": round(resultado.score_ancoragem, 3),
                "veracidade": round(resultado.relatorio_fatos["score_veracidade"], 3)
            },
            "contexto_tipo": self._classificar_contexto(contexto),
            "num_chunks_memoria": len(contexto.get("chunks_memoria", [])),
        }
        
        self.validation_log.append(entrada_log)
        
        # Manter tamanho do log controlado
        if len(self.validation_log) > self.max_log_size:
            self.validation_log = self.validation_log[-self.max_log_size:]
    
    async def _analisar_padroes(self) -> List[str]:
        """Análise de padrões otimizada para CPU"""
        insights = []
        
        # Análise mais simples e rápida
        entradas_recentes = self.validation_log[-50:] if len(self.validation_log) >= 50 else self.validation_log
        
        if len(entradas_recentes) >= 10:
            # Estatísticas básicas
            scores_confianca = [e["scores"]["confianca"] for e in entradas_recentes]
            scores_ancoragem = [e["scores"]["ancoragem"] for e in entradas_recentes]
            
            media_confianca = statistics.mean(scores_confianca) if scores_confianca else 0
            media_ancoragem = statistics.mean(scores_ancoragem) if scores_ancoragem else 0
            
            # Insights simples mas úteis
            if media_confianca < 0.4:
                insights.append(f"Confiança média baixa detectada: {media_confianca:.2f}. Considerar ajuste de parâmetros.")
            
            if media_ancoragem < 0.3:
                insights.append(f"Ancoragem média baixa detectada: {media_ancoragem:.2f}. Sistema pode estar gerando conteúdo não fundamentado.")
            
            # Análise de tendências simples
            alucinacoes = sum(1 for e in entradas_recentes if e["nivel_integridade"] == "POTENCIAL_ALUCINACAO")
            if alucinacoes > len(entradas_recentes) * 0.3:  # Mais de 30%
                insights.append(f"Taxa alta de potenciais alucinações: {alucinacoes}/{len(entradas_recentes)}. Revisão necessária.")
        
        # Limitar número de insights armazenados
        self.insights_metacognitivos.extend(insights)
        if len(self.insights_metacognitivos) > self.max_insights:
            self.insights_metacognitivos = self.insights_metacognitivos[-self.max_insights:]
        
        return insights


# Função de configuração específica para CPU
def criar_protocolo_cpu_otimizado() -> CPUOptimizedProtocolo:
    """
    Cria uma instância otimizada do protocolo para execução em CPU
    """
    print("🚀 Inicializando Sistema de Integridade Cognitiva otimizado para CPU...")
    
    try:
        protocolo = CPUOptimizedProtocolo(use_lightweight_components=True)
        print("✅ Protocolo CPU otimizado criado com sucesso!")
        print("📊 Configurações de CPU:")
        print(f"   - Componentes leves: Ativado")
        print(f"   - Cache de embeddings: Ativado")
        print(f"   - Base conhecimento local: Ativada")
        print(f"   - Thresholds ajustados para performance")
        return protocolo
        
    except Exception as e:
        print(f"❌ Erro ao criar protocolo otimizado: {e}")
        print("🔄 Tentando com configuração de fallback...")
        
        # Fallback para versão ainda mais simples
        protocolo = ProtocoloDeIntegridadeCognitiva()
        protocolo.grounding_analyzer = None  # Desabilitar se houver problemas
        print("⚠️  Protocolo criado com funcionalidade reduzida")
        return protocolo


if __name__ == "__main__":
    print("🧠 Sistema de Integridade Cognitiva da Atena - Versão CPU Otimizada")
    print("=" * 70)
    
    # Testar primeiro a criação do protocolo otimizado
    protocolo_teste = criar_protocolo_cpu_otimizado()
    
    # Executar demonstração
    asyncio.run(main())