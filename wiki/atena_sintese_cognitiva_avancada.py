# atena_sintese_cognitiva_avancada.py
# Versão 2.0 - Módulo Avançado de Síntese e Estruturação de Conhecimento
# Implementação com IA robusta e tecnologias modernas

import logging
import asyncio
import hashlib
import numpy as np
import networkx as nx
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import json
import re

# Bibliotecas de NLP e ML
import spacy
import transformers
from transformers import (
    AutoTokenizer, AutoModel, AutoModelForSequenceClassification,
    pipeline, T5ForConditionalGeneration, T5Tokenizer
)
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import textstat

# Processamento de grafos e embeddings
from node2vec import Node2Vec
import community

# Configuração avançada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('atena_cognitive_synthesis.log')
    ]
)
logger = logging.getLogger("AtenaSinteseCognitivaAvancada")

@dataclass
class ConhecimentoEstruturado:
    """Estrutura de dados para conhecimento processado"""
    id_conhecimento: str
    texto_original: str
    resumo_executivo: str
    resumo_tecnico: str
    entidades_nomeadas: Dict[str, List[str]]
    conceitos_principais: List[Dict[str, Any]]
    relacoes_semanticas: Dict[str, Any]
    sentimentos: Dict[str, float]
    topicos: List[Dict[str, Any]]
    complexidade_linguistica: Dict[str, float]
    embeddings: np.ndarray
    grafo_conhecimento: Dict[str, Any]
    metadados: Dict[str, Any]
    timestamp_criacao: str
    confianca_processamento: float

class ModelosIA:
    """Gerenciador centralizado de modelos de IA"""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Inicializando modelos de IA no dispositivo: {self.device}")
        
        # Modelo de linguagem português
        self.nlp_pt = None
        self.sentence_transformer = None
        self.summarizer = None
        self.sentiment_analyzer = None
        self.ner_model = None
        self.topic_model = None
        
        # Cache para embeddings
        self.embedding_cache = {}
        
    async def inicializar_modelos(self):
        """Inicialização assíncrona dos modelos"""
        try:
            # SpaCy para português
            logger.info("Carregando modelo spaCy português...")
            self.nlp_pt = spacy.load("pt_core_news_lg")
            
            # Sentence Transformer multilíngue
            logger.info("Carregando Sentence Transformer...")
            self.sentence_transformer = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            )
            
            # Modelo de sumarização T5 português
            logger.info("Carregando modelo de sumarização...")
            self.summarizer = pipeline(
                "summarization",
                model="unicamp-dl/ptt5-base-portuguese-vocab",
                tokenizer="unicamp-dl/ptt5-base-portuguese-vocab",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Análise de sentimentos
            logger.info("Carregando analisador de sentimentos...")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="neuralmind/bert-base-portuguese-cased",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # NER customizado
            self.ner_model = pipeline(
                "ner",
                model="neuralmind/bert-base-portuguese-cased",
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1
            )
            
            logger.info("Todos os modelos carregados com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelos: {e}")
            raise

class AtenaSinteseCognitivaAvancada:
    """
    Sistema avançado de síntese cognitiva com IA robusta
    """
    
    def __init__(self):
        self.modelos = ModelosIA()
        self.grafo_global = nx.Graph()
        self.conhecimentos_processados = {}
        self.inicializado = False
        
    async def inicializar(self):
        """Inicialização assíncrona do sistema"""
        if not self.inicializado:
            await self.modelos.inicializar_modelos()
            self.inicializado = True
            logger.info("Sistema Atena inicializado com sucesso!")
    
    def _gerar_id_conhecimento(self, texto: str) -> str:
        """Gera ID único baseado no hash do conteúdo"""
        hash_obj = hashlib.sha256(texto.encode())
        return f"knowledge_{hash_obj.hexdigest()[:16]}"
    
    def _analisar_complexidade_linguistica(self, texto: str) -> Dict[str, float]:
        """Análise avançada da complexidade linguística"""
        try:
            complexidade = {
                'flesch_reading_ease': textstat.flesch_reading_ease(texto),
                'flesch_kincaid_grade': textstat.flesch_kincaid_grade(texto),
                'gunning_fog': textstat.gunning_fog(texto),
                'smog_index': textstat.smog_index(texto),
                'automated_readability_index': textstat.automated_readability_index(texto),
                'coleman_liau_index': textstat.coleman_liau_index(texto),
                'linsear_write_formula': textstat.linsear_write_formula(texto),
                'dale_chall_readability_score': textstat.dale_chall_readability_score(texto)
            }
            return complexidade
        except Exception as e:
            logger.warning(f"Erro na análise de complexidade: {e}")
            return {}
    
    async def _extrair_entidades_avancado(self, texto: str) -> Dict[str, List[str]]:
        """Extração avançada de entidades nomeadas"""
        try:
            # Processamento com spaCy
            doc = self.modelos.nlp_pt(texto)
            entidades_spacy = {
                'PERSON': [ent.text for ent in doc.ents if ent.label_ == 'PER'],
                'ORG': [ent.text for ent in doc.ents if ent.label_ == 'ORG'],
                'LOC': [ent.text for ent in doc.ents if ent.label_ == 'LOC'],
                'MISC': [ent.text for ent in doc.ents if ent.label_ == 'MISC']
            }
            
            # Processamento com BERT NER
            entidades_bert = self.modelos.ner_model(texto)
            entidades_consolidadas = defaultdict(list)
            
            # Consolidar entidades
            for ent_type, ents in entidades_spacy.items():
                entidades_consolidadas[ent_type].extend(ents)
            
            for ent in entidades_bert:
                tipo = ent['entity_group']
                if tipo not in entidades_consolidadas:
                    entidades_consolidadas[tipo] = []
                entidades_consolidadas[tipo].append(ent['word'])
            
            # Remover duplicatas e limpar
            for tipo in entidades_consolidadas:
                entidades_consolidadas[tipo] = list(set(entidades_consolidadas[tipo]))
            
            return dict(entidades_consolidadas)
            
        except Exception as e:
            logger.error(f"Erro na extração de entidades: {e}")
            return {}
    
    def _extrair_conceitos_semanticos(self, texto: str) -> List[Dict[str, Any]]:
        """Extração de conceitos usando análise semântica avançada"""
        try:
            doc = self.modelos.nlp_pt(texto)
            
            # Extrair conceitos baseados em substantivos e suas relações
            conceitos = []
            for token in doc:
                if (token.pos_ in ['NOUN', 'PROPN'] and 
                    len(token.text) > 3 and 
                    not token.is_stop and 
                    token.is_alpha):
                    
                    # Calcular importância baseada em frequência e posição
                    importancia = self._calcular_importancia_conceito(token, doc)
                    
                    conceito = {
                        'termo': token.lemma_.lower(),
                        'texto_original': token.text,
                        'pos': token.pos_,
                        'importancia': importancia,
                        'contexto': [child.text for child in token.children],
                        'dependencias': [(child.dep_, child.text) for child in token.children]
                    }
                    conceitos.append(conceito)
            
            # Ordenar por importância e remover duplicatas
            conceitos_unicos = {}
            for conceito in conceitos:
                termo = conceito['termo']
                if termo not in conceitos_unicos or conceito['importancia'] > conceitos_unicos[termo]['importancia']:
                    conceitos_unicos[termo] = conceito
            
            return sorted(conceitos_unicos.values(), key=lambda x: x['importancia'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro na extração de conceitos semânticos: {e}")
            return []
    
    def _calcular_importancia_conceito(self, token, doc) -> float:
        """Calcula a importância de um conceito no texto"""
        # Frequência do termo
        freq = sum(1 for t in doc if t.lemma_.lower() == token.lemma_.lower())
        freq_norm = freq / len(doc)
        
        # Posição no texto (início é mais importante)
        pos_norm = 1 - (token.i / len(doc))
        
        # Número de dependências (mais conexões = mais importante)
        deps_norm = len(list(token.children)) / 10  # Normalizar por 10
        
        # Score final
        importancia = (freq_norm * 0.4) + (pos_norm * 0.3) + (deps_norm * 0.3)
        return min(importancia, 1.0)
    
    async def _gerar_embeddings(self, texto: str) -> np.ndarray:
        """Gera embeddings semânticos do texto"""
        try:
            # Verificar cache
            texto_hash = hashlib.md5(texto.encode()).hexdigest()
            if texto_hash in self.modelos.embedding_cache:
                return self.modelos.embedding_cache[texto_hash]
            
            # Gerar embeddings
            embeddings = self.modelos.sentence_transformer.encode([texto])
            self.modelos.embedding_cache[texto_hash] = embeddings[0]
            
            return embeddings[0]
            
        except Exception as e:
            logger.error(f"Erro na geração de embeddings: {e}")
            return np.array([])
    
    def _construir_grafo_conhecimento(self, conceitos: List[Dict[str, Any]], 
                                    entidades: Dict[str, List[str]]) -> Dict[str, Any]:
        """Constrói grafo de conhecimento avançado"""
        try:
            grafo = nx.Graph()
            
            # Adicionar nós de conceitos
            for conceito in conceitos:
                grafo.add_node(
                    conceito['termo'],
                    tipo='conceito',
                    importancia=conceito['importancia'],
                    contexto=conceito['contexto']
                )
            
            # Adicionar nós de entidades
            for tipo_ent, entidades_lista in entidades.items():
                for entidade in entidades_lista:
                    grafo.add_node(
                        entidade,
                        tipo='entidade',
                        categoria=tipo_ent,
                        importancia=0.8
                    )
            
            # Criar arestas baseadas em co-ocorrência e proximidade semântica
            nos = list(grafo.nodes())
            for i, no1 in enumerate(nos):
                for no2 in nos[i+1:]:
                    # Calcular peso da aresta baseado em co-ocorrência
                    peso = self._calcular_peso_aresta(no1, no2, conceitos, entidades)
                    if peso > 0.3:  # Threshold para conexões significativas
                        grafo.add_edge(no1, no2, peso=peso)
            
            # Análise de comunidades
            try:
                communities = community.best_partition(grafo)
                nx.set_node_attributes(grafo, communities, 'comunidade')
            except:
                logger.warning("Não foi possível detectar comunidades no grafo")
            
            # Métricas do grafo
            metricas = {
                'num_nos': grafo.number_of_nodes(),
                'num_arestas': grafo.number_of_edges(),
                'densidade': nx.density(grafo),
                'centralidades': dict(nx.betweenness_centrality(grafo))
            }
            
            return {
                'grafo_dados': nx.node_link_data(grafo),
                'metricas': metricas
            }
            
        except Exception as e:
            logger.error(f"Erro na construção do grafo: {e}")
            return {'grafo_dados': {}, 'metricas': {}}
    
    def _calcular_peso_aresta(self, no1: str, no2: str, conceitos: List[Dict], 
                            entidades: Dict[str, List[str]]) -> float:
        """Calcula o peso da aresta entre dois nós baseado em co-ocorrência e similaridade."""
        # Coleta todos os termos relevantes do texto original
        todos_termos = [c['termo'] for c in conceitos] + \
                       [e for sublist in entidades.values() for e in sublist]
        
        # Cria um conjunto de termos para cada nó para verificar co-ocorrência
        termos_no1 = set([no1.lower()] + [c['termo'].lower() for c in conceitos if c['termo'].lower() == no1.lower()])
        termos_no2 = set([no2.lower()] + [c['termo'].lower() for c in conceitos if c['termo'].lower() == no2.lower()])

        # Verifica co-ocorrência no texto original (simplificado)
        # Para uma implementação mais robusta, seria necessário o texto original completo aqui
        # e verificar a proximidade das palavras.
        co_occurrence_score = 0.0
        if no1.lower() in todos_termos and no2.lower() in todos_termos:
            # Simplesmente verifica se ambos estão presentes na lista de termos extraídos
            co_occurrence_score = 0.7 # Dá um peso base se co-ocorrem

        # Calcula similaridade semântica entre os nós (se embeddings estiverem disponíveis)
        semantic_similarity_score = 0.0
        try:
            if self.modelos.sentence_transformer and no1 and no2:
                # Gera embeddings para os termos dos nós
                embeddings = self.modelos.sentence_transformer.encode([no1, no2])
                semantic_similarity_score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
                # Normaliza para um score entre 0 e 1
                semantic_similarity_score = (semantic_similarity_score + 1) / 2 
        except Exception as e:
            logger.warning(f"Erro ao calcular similaridade semântica para aresta ({no1}, {no2}): {e}")

        # Combina os scores
        # Pondera mais a similaridade semântica se for alta
        peso = (co_occurrence_score * 0.3) + (semantic_similarity_score * 0.7)
        
        return peso
    
    async def _analisar_sentimentos(self, texto: str) -> Dict[str, float]:
        """Análise avançada de sentimentos"""
        try:
            resultado = self.modelos.sentiment_analyzer(texto)
            
            # Normalizar resultados
            sentimentos = {
                'polaridade': 0.0,
                'confianca': 0.0,
                'emocoes': {}
            }
            
            if resultado:
                if resultado[0]['label'] == 'POSITIVE':
                    sentimentos['polaridade'] = resultado[0]['score']
                else:
                    sentimentos['polaridade'] = -resultado[0]['score']
                sentimentos['confianca'] = resultado[0]['score']
            
            return sentimentos
            
        except Exception as e:
            logger.error(f"Erro na análise de sentimentos: {e}")
            return {'polaridade': 0.0, 'confianca': 0.0, 'emocoes': {}}
    
    async def _gerar_resumos(self, texto: str) -> Tuple[str, str]:
        """Gera resumos executivo e técnico"""
        try:
            # Resumo executivo (mais curto, linguagem simples)
            resumo_exec = self.modelos.summarizer(
                texto,
                max_length=100,
                min_length=30,
                do_sample=False
            )[0]['summary_text']
            
            # Resumo técnico (mais detalhado, preserva termos técnicos)
            resumo_tec = self.modelos.summarizer(
                texto,
                max_length=200,
                min_length=80,
                do_sample=False
            )[0]['summary_text']
            
            return resumo_exec, resumo_tec
            
        except Exception as e:
            logger.error(f"Erro na geração de resumos: {e}")
            return "Resumo não disponível", "Resumo técnico não disponível"
    
    def _detectar_topicos(self, conceitos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detecção de tópicos principais"""
        try:
            # Agrupar conceitos por similaridade semântica
            if len(conceitos) < 2:
                return [{'topico': 'Geral', 'conceitos': conceitos, 'relevancia': 1.0}]
            
            # Simplificado: agrupar por importância
            conceitos_importantes = [c for c in conceitos if c['importancia'] > 0.5]
            
            topicos = [{
                'topico': 'Principal',
                'conceitos': conceitos_importantes[:5],
                'relevancia': np.mean([c['importancia'] for c in conceitos_importantes[:5]]) if conceitos_importantes else 0.0
            }]
            
            return topicos
            
        except Exception as e:
            logger.error(f"Erro na detecção de tópicos: {e}")
            return []
    
    def _calcular_confianca(self, dados: Dict[str, Any]) -> float:
        """Calcula score de confiança do processamento"""
        try:
            scores = []
            
            # Confiança baseada na qualidade dos dados extraídos
            if dados.get('entidades_nomeadas'):
                scores.append(0.8)
            if dados.get('conceitos_principais'):
                scores.append(0.9)
            if dados.get('sentimentos', {}).get('confianca', 0) > 0.7:
                scores.append(0.85)
            
            return np.mean(scores) if scores else 0.5
            
        except Exception as e:
            logger.error(f"Erro no cálculo de confiança: {e}")
            return 0.5
    
    async def processar_informacao(self, dados_brutos: Dict[str, Any]) -> ConhecimentoEstruturado:
        """
        Pipeline principal de processamento cognitivo
        """
        logger.info("Iniciando processamento cognitivo avançado...")
        
        if not self.inicializado:
            await self.inicializar()
        
        try:
            texto = dados_brutos.get('text', '')
            if not texto.strip():
                raise ValueError("Texto vazio ou inválido")
            
            # Gerar ID único
            id_conhecimento = self._gerar_id_conhecimento(texto)
            logger.info(f"Processando conhecimento ID: {id_conhecimento}")
            
            # 1. Análise linguística
            complexidade = self._analisar_complexidade_linguistica(texto)
            
            # 2. Extração de entidades
            entidades = await self._extrair_entidades_avancado(texto)
            
            # 3. Extração de conceitos semânticos
            conceitos = self._extrair_conceitos_semanticos(texto)
            
            # 4. Geração de embeddings
            embeddings = await self._gerar_embeddings(texto)
            
            # 5. Construção do grafo de conhecimento
            grafo = self._construir_grafo_conhecimento(conceitos, entidades)
            
            # 6. Análise de sentimentos
            sentimentos = await self._analisar_sentimentos(texto)
            
            # 7. Geração de resumos
            resumo_exec, resumo_tec = await self._gerar_resumos(texto)
            
            # 8. Detecção de tópicos
            topicos = self._detectar_topicos(conceitos)
            
            # 9. Estrutura final do conhecimento
            dados_processados = {
                'entidades_nomeadas': entidades,
                'conceitos_principais': conceitos,
                'sentimentos': sentimentos,
                'complexidade_linguistica': complexidade
            }
            
            # 10. Calcular confiança
            confianca = self._calcular_confianca(dados_processados)
            
            # Criar estrutura final
            conhecimento = ConhecimentoEstruturado(
                id_conhecimento=id_conhecimento,
                texto_original=texto,
                resumo_executivo=resumo_exec,
                resumo_tecnico=resumo_tec,
                entidades_nomeadas=entidades,
                conceitos_principais=conceitos,
                relacoes_semanticas=grafo,
                sentimentos=sentimentos,
                topicos=topicos,
                complexidade_linguistica=complexidade,
                embeddings=embeddings,
                grafo_conhecimento=grafo,
                metadados=dados_brutos.get('metadata', {}),
                timestamp_criacao=datetime.now().isoformat(),
                confianca_processamento=confianca
            )
            
            # Armazenar para consultas futuras
            self.conhecimentos_processados[id_conhecimento] = conhecimento
            
            logger.info(f"Processamento concluído com sucesso. Confiança: {confianca:.2f}")
            return conhecimento
            
        except Exception as e:
            logger.error(f"Erro no processamento cognitivo: {e}")
            raise
    
    def exportar_conhecimento(self, conhecimento: ConhecimentoEstruturado, 
                            formato: str = 'json') -> str:
        """Exporta conhecimento em diferentes formatos"""
        try:
            if formato == 'json':
                # Converter arrays numpy para listas
                dados = asdict(conhecimento)
                if isinstance(dados['embeddings'], np.ndarray):
                    dados['embeddings'] = dados['embeddings'].tolist()
                return json.dumps(dados, ensure_ascii=False, indent=2)
            
            elif formato == 'markdown':
                return self._gerar_relatorio_markdown(conhecimento)
            
            else:
                raise ValueError(f"Formato '{formato}' não suportado")
                
        except Exception as e:
            logger.error(f"Erro na exportação: {e}")
            return ""
    
    def _gerar_relatorio_markdown(self, conhecimento: ConhecimentoEstruturado) -> str:
        """Gera relatório em formato Markdown"""
        md = f"""# Relatório de Análise Cognitiva

## Informações Gerais
- **ID:** {conhecimento.id_conhecimento}
- **Data de Processamento:** {conhecimento.timestamp_criacao}
- **Confiança:** {conhecimento.confianca_processamento:.2%}

## Resumo Executivo
{conhecimento.resumo_executivo}

## Resumo Técnico
{conhecimento.resumo_tecnico}

## Entidades Identificadas
"""
        for tipo, entidades in conhecimento.entidades_nomeadas.items():
            if entidades:
                md += f"\n### {tipo}\n"
                for ent in entidades[:5]:  # Limitar a 5 por tipo
                    md += f"- {ent}\n"
        
        md += f"\n## Conceitos Principais\n"
        for conceito in conhecimento.conceitos_principais[:10]:
            md += f"- **{conceito['termo']}** (Importância: {conceito['importancia']:.2f})\n"
        
        md += f"\n## Análise de Sentimentos\n"
        md += f"- Polaridade: {conhecimento.sentimentos.get('polaridade', 0):.2f}\n"
        md += f"- Confiança: {conhecimento.sentimentos.get('confianca', 0):.2f}\n"
        
        return md

# Exemplo de uso
async def main():
    """Exemplo de uso do sistema"""
    atena = AtenaSinteseCognitivaAvancada()
    
    dados_teste = {
        'text': """
        A inteligência artificial tem revolucionado diversos setores da economia mundial.
        Empresas como Google, Microsoft e OpenAI estão liderando o desenvolvimento
        de modelos de linguagem cada vez mais sofisticados. Estes avanços prometem
        transformar áreas como educação, saúde e automação industrial.
        """,
        'metadata': {
            'fonte': 'documento_teste',
            'autor': 'sistema',
            'categoria': 'tecnologia'
        }
    }
    
    try:
        conhecimento = await atena.processar_informacao(dados_teste)
        
        # Exportar em JSON
        json_output = atena.exportar_conhecimento(conhecimento, 'json')
        print("Conhecimento processado e exportado com sucesso!")
        
        # Exportar relatório
        relatorio = atena.exportar_conhecimento(conhecimento, 'markdown')
        print("\nRelatório gerado:")
        print(relatorio)
        
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")

if __name__ == "__main__":
    asyncio.run(main())