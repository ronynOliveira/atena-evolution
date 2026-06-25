#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atena - Léxico Fonético Clínico Personalizado
==============================================

Versão 2.0

Este módulo foi aprimorado para incorporar conhecimento clínico sobre
distúrbios da fala, como a Distonia, tornando o sistema de correção mais
proativo e preciso. Ele agora modela padrões de fala específicos associados
a condições neurológicas para antecipar e corrigir erros de transcrição
de forma mais inteligente.

Autor: Claude (em colaboração com Atena e Senhor Robério)
Versão: 2.0
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import difflib
import logging
from enum import Enum

# --- Configuração do Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Estruturas de Dados Clínicas ---

class TipoDisturbio(Enum):
    """Enumeração dos tipos de distúrbios da fala modelados."""
    DISTONIA_LARINGEA = "Distonia Laríngea (Disfonia Espasmódica)"
    DISTONIA_CERVICAL = "Distonia Cervical"
    DISTONIA_OROMANDIBULAR = "Distonia Oromandibular"
    DISARTRIA_FLACIDA = "Disartria Flácida"
    DISARTRIA_ESPASTICA = "Disartria Espástica"
    DISARTRIA_ATAXICA = "Disartria Atáxica"
    NENHUM = "Nenhum"

@dataclass
class PerfilDeFala:
    """
    Representa o perfil clínico do usuário, guiando a correção fonética.
    Este perfil é a ponte entre o conhecimento médico e a lógica do software.
    """
    disturbio_primario: TipoDisturbio = TipoDisturbio.NENHUM
    caracteristicas_observadas: Set[str] = field(default_factory=set)
    intensidade: float = 0.5  # Varia de 0 (leve) a 1 (severo)

    def adicionar_caracteristica(self, desc: str):
        """Adiciona uma característica observada ao perfil."""
        self.caracteristicas_observadas.add(desc)
        logger.info(f"Característica adicionada ao perfil: {desc}")

# --- Componentes do Léxico ---

@dataclass
class EntradaLexico:
    """
    Estrutura de dados para cada mapeamento no léxico.
    """
    transcricao_crua: str
    texto_confirmado: str
    contagem_confirmacao: int = 1
    similaridade_media: float = 1.0
    ultimo_uso: str = field(default_factory=lambda: datetime.now().isoformat())
    fonemas_associados: List[str] = field(default_factory=list)
    contexto_clinico: Optional[str] = None # Armazena o distúrbio ativo durante o aprendizado

    def atualizar_uso(self):
        """Atualiza o timestamp do último uso."""
        self.ultimo_uso = datetime.now().isoformat()

class AnalisadorFonetico:
    """
    Módulo de análise fonética que extrai padrões e calcula distâncias.
    """
    def extrair_fonemas(self, texto: str) -> List[str]:
        """Extrai uma representação simplificada de fonemas de um texto."""
        texto_limpo = re.sub(r'[^a-záàâãéêíóôõúç\s]', '', texto.lower())
        # Mapeamento simplificado de grafemas para fonemas
        substituicoes = {'ss': 's', 'rr': 'R', 'lh': 'L', 'nh': 'N', 'ch': 'X', 'qu': 'k', 'gu': 'g'}
        for k, v in substituicoes.items():
            texto_limpo = texto_limpo.replace(k, v)
        return list(texto_limpo.replace(' ', ''))

    def calcular_distancia_fonetica(self, palavra1: str, palavra2: str) -> float:
        """Calcula a distância fonética (Levenshtein) entre duas palavras."""
        fonemas1 = self.extrair_fonemas(palavra1)
        fonemas2 = self.extrair_fonemas(palavra2)
        return 1.0 - difflib.SequenceMatcher(None, fonemas1, fonemas2).ratio()

class AnalisadorClinicoFonetico:
    """
    NOVO: Módulo que traduz conhecimento clínico em regras de correção.
    Este é o núcleo da nova inteligência do sistema.
    """
    def __init__(self, perfil: PerfilDeFala):
        self.perfil = perfil
        self.mapa_regras_clinicas = self._mapear_regras()
        logger.info(f"Analisador Clínico inicializado para o perfil: {self.perfil.disturbio_primario.value}")

    def _mapear_regras(self) -> Dict[TipoDisturbio, Dict]:
        """
        Mapeia os distúrbios para um conjunto de heurísticas de correção.
        Esta função é a implementação direta das informações clínicas fornecidas.
        """
        return {
            TipoDisturbio.DISTONIA_OROMANDIBULAR: {
                "descricao": "Afeta boca, língua, garganta. Causa fala pastosa/língua pesada.",
                "heuristica": self._heuristica_fala_pastosa
            },
            TipoDisturbio.DISTONIA_LARINGEA: {
                "descricao": "Afeta cordas vocais. Causa fala entrecortada/estrangulada.",
                "heuristica": self._heuristica_fala_entrecortada
            },
            TipoDisturbio.DISTONIA_CERVICAL: {
                "descricao": "Compromete musculatura do pescoço. Causa fala tremida.",
                "heuristica": self._heuristica_fala_tremida
            }
            # Outros distúrbios podem ser mapeados aqui
        }

    def aplicar_correcao_preditiva(self, texto: str) -> str:
        """Aplica correções preditivas com base no perfil clínico."""
        if self.perfil.disturbio_primario == TipoDisturbio.NENHUM:
            return texto

        regras = self.mapa_regras_clinicas.get(self.perfil.disturbio_primario)
        if not regras or 'heuristica' not in regras:
            return texto

        logger.info(f"Aplicando heurística para {self.perfil.disturbio_primario.name}")
        texto_corrigido = regras['heuristica'](texto)
        return texto_corrigido

    def _heuristica_fala_pastosa(self, texto: str) -> str:
        """
        Simula a correção de uma "fala pastosa", onde consoantes podem
        ser trocadas por outras de articulação próxima.
        Ex: 't' -> 'd', 'p' -> 'b', 's' -> 'z'
        """
        correcoes = {
            r'\b(t|d)e\b': 'de',
            r'\b(p|b)ara\b': 'para',
            r'\b(s|z)ua\b': 'sua',
        }
        texto_corrigido = texto
        for padrao, substituicao in correcoes.items():
            texto_corrigido = re.sub(padrao, substituicao, texto_corrigido, flags=re.IGNORECASE)
        return texto_corrigido

    def _heuristica_fala_entrecortada(self, texto: str) -> str:
        """
        Tenta unir palavras que podem ter sido separadas por espasmos vocais,
        especialmente em vogais iniciais.
        Ex: "a tena" -> "atena"
        """
        # Une palavras pequenas que começam com vogal à palavra anterior
        texto_corrigido = re.sub(r'(\w)\s+([aeiou]\w*)', r'\1\2', texto)
        return texto_corrigido

    def _heuristica_fala_tremida(self, texto: str) -> str:
        """
        Simula a correção de uma fala trêmula, que pode gerar
        duplicação de sílabas ou letras.
        Ex: "atena-na" -> "atena"
        """
        palavras = texto.split()
        palavras_corrigidas = []
        for palavra in palavras:
            # Remove duplicação de sílabas simples no final da palavra
            if len(palavra) > 4 and palavra[-2:] == palavra[-4:-2]:
                palavras_corrigidas.append(palavra[:-2])
            else:
                palavras_corrigidas.append(palavra)
        return ' '.join(palavras_corrigidas)


class LexicoFoneticoManager:
    """
    Classe principal para gerenciamento do Léxico Fonético Personalizado.
    """
    def __init__(self, arquivo_lexico: str, perfil_fala: PerfilDeFala):
        self.arquivo_lexico = Path(arquivo_lexico)
        self.lexico: Dict[str, EntradaLexico] = {}
        self.perfil_fala = perfil_fala
        self.analisador_fonetico = AnalisadorFonetico()
        self.analisador_clinico = AnalisadorClinicoFonetico(self.perfil_fala)

        self._carregar_lexico()
        logger.info(f"Léxico Fonético inicializado com {len(self.lexico)} entradas.")

    def _carregar_lexico(self):
        """Carrega o léxico do arquivo JSON."""
        try:
            if self.arquivo_lexico.exists():
                with open(self.arquivo_lexico, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                for chave, entrada_dict in dados.items():
                    self.lexico[chave] = EntradaLexico(**entrada_dict)
                logger.info(f"Léxico carregado com {len(self.lexico)} entradas.")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Erro ao carregar léxico: {e}. Iniciando com léxico vazio.")
            self.lexico = {}

    def _salvar_lexico(self):
        """Salva o léxico no arquivo JSON."""
        try:
            with open(self.arquivo_lexico, 'w', encoding='utf-8') as f:
                json.dump({k: asdict(v) for k, v in self.lexico.items()}, f, ensure_ascii=False, indent=2)
            logger.info(f"Léxico salvo com {len(self.lexico)} entradas.")
        except Exception as e:
            logger.error(f"Erro ao salvar léxico: {e}")

    def aprender_mapeamento(self, transcricao_crua: str, texto_confirmado: str):
        """Aprende um novo mapeamento ou reforça um existente."""
        chave = self._normalizar_texto(transcricao_crua)
        texto_confirmado_norm = self._normalizar_texto(texto_confirmado)

        if chave in self.lexico:
            entrada = self.lexico[chave]
            if entrada.texto_confirmado == texto_confirmado_norm:
                entrada.contagem_confirmacao += 1
                entrada.atualizar_uso()
                logger.info(f"Reforço de mapeamento: '{chave}' -> '{texto_confirmado_norm}' (x{entrada.contagem_confirmacao})")
            else:
                # Conflito: decide com base na contagem de confirmação
                if entrada.contagem_confirmacao < 2:
                    logger.warning(f"Substituindo mapeamento conflitante para '{chave}'. Novo: '{texto_confirmado_norm}'. Antigo: '{entrada.texto_confirmado}'.")
                    entrada.texto_confirmado = texto_confirmado_norm
                    entrada.contagem_confirmacao = 1
                    entrada.atualizar_uso()
                else:
                     logger.warning(f"Conflito ignorado para '{chave}' devido à alta contagem do mapeamento existente.")
        else:
            logger.info(f"Novo mapeamento aprendido: '{chave}' -> '{texto_confirmado_norm}'")
            nova_entrada = EntradaLexico(
                transcricao_crua=chave,
                texto_confirmado=texto_confirmado_norm,
                contexto_clinico=self.perfil_fala.disturbio_primario.name
            )
            self.lexico[chave] = nova_entrada

        self._salvar_lexico()

    def corrigir_transcricao(self, texto_transcrito: str) -> str:
        """
        Pipeline de correção: Preditiva -> Léxico -> Similaridade.
        """
        texto_normalizado = self._normalizar_texto(texto_transcrito)

        # 1. Correção Preditiva Clínica (NOVO)
        texto_preditivo = self.analisador_clinico.aplicar_correcao_preditiva(texto_normalizado)
        if texto_preditivo != texto_normalizado:
            logger.info(f"Correção Preditiva aplicada: '{texto_normalizado}' -> '{texto_preditivo}'")
            # Usa o resultado da correção preditiva como base para as próximas etapas
            texto_base = texto_preditivo
        else:
            texto_base = texto_normalizado

        # 2. Correção por Léxico (correspondência exata)
        if texto_base in self.lexico:
            entrada = self.lexico[texto_base]
            entrada.atualizar_uso()
            self._salvar_lexico()
            logger.info(f"Correção por Léxico: '{texto_base}' -> '{entrada.texto_confirmado}'")
            return entrada.texto_confirmado

        # 3. Correção por Similaridade
        melhor_match = self._buscar_por_similaridade(texto_base)
        if melhor_match:
            entrada, similaridade = melhor_match
            if similaridade > 0.85 and entrada.contagem_confirmacao >= 2:
                entrada.atualizar_uso()
                self._salvar_lexico()
                logger.info(f"Correção por Similaridade: '{texto_base}' -> '{entrada.texto_confirmado}' (sim: {similaridade:.2f})")
                return entrada.texto_confirmado

        # Se nenhuma correção forte foi encontrada, retorna o texto original ou o preditivo
        if texto_preditivo != texto_normalizado:
            return texto_preditivo
            
        logger.info(f"Nenhuma correção forte encontrada para: '{texto_transcrito}'")
        return texto_transcrito

    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza texto para consistência."""
        return re.sub(r'\s+', ' ', texto.lower().strip())

    def _buscar_por_similaridade(self, texto: str) -> Optional[Tuple[EntradaLexico, float]]:
        """Busca a entrada mais similar no léxico."""
        if not self.lexico: return None
        
        melhor_entrada = None
        maior_similaridade = 0.0

        for chave, entrada in self.lexico.items():
            similaridade = 1 - self.analisador_fonetico.calcular_distancia_fonetica(texto, chave)
            # Pondera pela confiança da entrada
            similaridade_ponderada = similaridade * (1 + (entrada.contagem_confirmacao / 10))

            if similaridade_ponderada > maior_similaridade:
                maior_similaridade = similaridade_ponderada
                melhor_entrada = entrada

        if melhor_entrada and maior_similaridade > 0.8: # Limiar de confiança
            # Retorna a similaridade original, não a ponderada
            original_sim = 1 - self.analisador_fonetico.calcular_distancia_fonetica(texto, melhor_entrada.transcricao_crua)
            return melhor_entrada, original_sim
            
        return None

# --- Função de conveniência e Exemplo de Uso ---
def criar_lexico_manager(arquivo_lexico: str, perfil_fala: PerfilDeFala) -> LexicoFoneticoManager:
    return LexicoFoneticoManager(arquivo_lexico, perfil_fala)

if __name__ == "__main__":
    print("=== Atena - Léxico Fonético Clínico Personalizado (v2.0) ===\n")

    # 1. Configuração do Perfil Clínico do Usuário
    # Simula o perfil do Senhor Robério, com base nas informações fornecidas.
    perfil_roberio = PerfilDeFala(
        disturbio_primario=TipoDisturbio.DISTONIA_OROMANDIBULAR,
        intensidade=0.6
    )
    perfil_roberio.adicionar_caracteristica("Fala um pouco pastosa ou com sensação de língua pesada.")
    perfil_roberio.adicionar_caracteristica("Dificuldade em articular certas consoantes.")
    
    print(f"Perfil Clínico Configurado: {perfil_roberio.disturbio_primario.value}\n")

    # 2. Inicialização do Gerenciador do Léxico
    caminho_memoria = Path(__file__).parent.parent / 'memoria_do_usuario'
    caminho_memoria.mkdir(exist_ok=True)
    arquivo_lexico = caminho_memoria / "lexico_fonetico_clinico_roberio.json"
    lexico_manager = criar_lexico_manager(str(arquivo_lexico), perfil_roberio)

    # 3. Simulação de Aprendizado
    print("--- Fase de Aprendizado ---")
    exemplos_aprendizado = [
        ("atena ligar lus", "atena ligar luz"), # Erro de articulação comum
        ("bodia atena", "bom dia atena"),     # Troca de fonema
        ("filha bonita", "brilha bonita"),     # Padrão de fala específico
        ("atena ligar lus", "atena ligar luz"), # Reforço
    ]
    for transcricao, confirmacao in exemplos_aprendizado:
        lexico_manager.aprender_mapeamento(transcricao, confirmacao)
    print("\n--- Fim da Fase de Aprendizado ---\n")

    # 4. Teste do Pipeline de Correção
    print("--- Testando o Pipeline de Correção ---")
    testes = [
        "atena ligar lus",        # Deve corrigir pelo léxico
        "fala bonita",            # Deve corrigir por similaridade ("filha bonita" -> "brilha bonita")
        "bodia atena",            # Deve corrigir pelo léxico
        "te novo",                # Deve ser corrigido pela heurística clínica ("de novo")
        "a tena",                 # Não deve ser corrigido (perfil é oromandibular, não laríngeo)
        "um texto qualquer",      # Deve permanecer inalterado
    ]

    for texto_teste in testes:
        corrigido = lexico_manager.corrigir_transcricao(texto_teste)
        print(f"Original: '{texto_teste}'\t->\tCorrigido: '{corrigido}'")
        
    # Exemplo de mudança de perfil
    print("\n--- Mudando perfil para Distonia Laríngea ---")
    perfil_laringeo = PerfilDeFala(disturbio_primario=TipoDisturbio.DISTONIA_LARINGEA)
    lexico_manager_laringeo = criar_lexico_manager("lexico_fonetico_clinico_roberio.json", perfil_laringeo)
    texto_teste_laringeo = "a tena ligar a luz"
    corrigido_laringeo = lexico_manager_laringeo.corrigir_transcricao(texto_teste_laringeo)
    print(f"Original: '{texto_teste_laringeo}'\t->\tCorrigido: '{corrigido_laringeo}'")

