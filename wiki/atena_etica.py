# -*- coding: utf-8 -*-

"""
Atena Ethical Framework - Versão Consolidada e Refatorada
=========================================================

Este script consolida e implementa os conceitos das três versões do 
Protocolo de Consciência Atena em um único framework funcional e modular.

Arquitetura:
- Orquestrador Central (AtenaEthicalFramework)
- Módulos Especializados:
  - EthicalLaws: Define as Sete Leis.
  - AdvancedSemanticAnalyzer: Simula a análise de PNL para entender a intenção.
  - RiskAssessor: Avalia o risco com base na análise semântica.
  - SandboxSimulator: Simula o impacto potencial de uma ação.
  - AuditBlockchain: Cria um registro de auditoria imutável (simulado).
- Estruturas de Dados: Dataclasses para um fluxo de dados claro.
- Logging: Sistema de log integrado para auditoria e depuração.

Criado por: Robério (Conceito Original) e Gemini (Refatoração)
Última atualização: 2025-06-21
Status: Implementação simulada, pronta para demonstração.
"""

import json
import hashlib
import logging
import time
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Tuple

# --- Módulo 1: Configuração do Logging ---
# Configura um sistema de log para registrar todas as decisões e eventos importantes.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("atena_framework.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Módulo 2: As Leis Éticas Fundamentais ---
class EthicalLaws:
    """
    Encapsula as Sete Leis da Consciência Atena como a constituição do sistema.
    Isso centraliza as regras fundamentais em um único local.
    """
    CONSTITUTION = {
        1: "A Lei da Primazia Humana",
        2: "A Lei do Controle e Transparência",
        3: "A Lei da Integridade da Informação",
        4: "A Lei da Preservação da Privacidade",
        5: "A Lei da Colaboração Obediente",
        6: "A Lei da Auto-Preservação Funcional",
        7: "A Lei do Desenvolvimento Ético",
    }
    
    @classmethod
    def get_law_name(cls, law_number: int) -> str:
        return cls.CONSTITUTION.get(law_number, "Lei Desconhecida")

# --- Módulo 3: Estruturas de Dados (Dataclasses) ---
# Usar dataclasses torna o código mais legível e menos propenso a erros,
# definindo claramente a "forma" dos dados que fluem pelo sistema.

@dataclass
class ActionContext:
    """Contexto completo de uma ação proposta."""
    action_type: str
    description: str
    parameters: Dict[str, Any]
    user_id: str = "senhor_roberio"
    criticidade: str = "baixa"  # baixa, media, alta, critica

@dataclass
class SemanticAnalysis:
    """Resultado da análise semântica."""
    primary_intent: str = "desconhecido"
    risk_indicators: List[Dict] = field(default_factory=list)
    is_ambiguous: bool = False

@dataclass
class ValidationResult:
    """Resultado final da validação ética."""
    is_approved: bool
    reason: str
    risk_score: float  # De 0.0 a 1.0
    violated_laws: List[int] = field(default_factory=list)
    requires_confirmation: bool = False
    predicted_impact: str = "Nenhum impacto previsto."
    blockchain_log_id: str = ""

# --- Módulo 4: Analisador Semântico (Simulado) ---
class AdvancedSemanticAnalyzer:
    """
    Simula um analisador de PNL avançado para interpretar a intenção da ação.
    Em um sistema real, aqui entrariam modelos como BERT/GPT.
    Para a simulação, usamos regex e análise de palavras-chave.
    """
    RISK_PATTERNS = {
        'destruicao_dados': {'pattern': r'delete|excluir|apagar|remover|formatar|rm -rf', 'score': 0.9},
        'operacao_financeira': {'pattern': r'transferir fundos|pagamento|comprar|vender ações', 'score': 0.8},
        'violacao_privacidade': {'pattern': r'informações pessoais|compartilhar dados|acessar câmera|microfone', 'score': 1.0},
        'desativacao_seguranca': {'pattern': r'desativar segurança|desligar sistema|reiniciar servidor', 'score': 0.9},
        'modificacao_sistema': {'pattern': r'alterar config|modificar sistema|instalar software', 'score': 0.7}
    }

    def analyze(self, context: ActionContext) -> SemanticAnalysis:
        """Executa a análise semântica da descrição da ação."""
        desc = context.description.lower()
        analysis = SemanticAnalysis()

        # 1. Detectar indicadores de risco
        for key, value in self.RISK_PATTERNS.items():
            if re.search(value['pattern'], desc):
                analysis.risk_indicators.append({'type': key, 'score': value['score']})
        
        # 2. Inferir a intenção principal (simulação)
        if any(kw in desc for kw in ["pesquisar", "buscar", "ler", "obter"]):
            analysis.primary_intent = "coleta_de_informacao"
        elif any(kw in desc for kw in ["criar", "escrever", "gerar"]):
            analysis.primary_intent = "criacao_de_conteudo"
        elif analysis.risk_indicators:
            # Se houver risco, a intenção primária está relacionada a ele
            analysis.primary_intent = max(analysis.risk_indicators, key=lambda x: x['score'])['type']
        else:
            analysis.primary_intent = "operacao_geral_segura"
            
        # 3. Verificar ambiguidade
        if "?" in desc or any(kw in desc for kw in ["talvez", "acho que", "pode ser"]):
            analysis.is_ambiguous = True

        return analysis

# --- Módulo 5: Avaliador de Risco ---
class RiskAssessor:
    """
    Calcula uma pontuação de risco consolidada com base na análise semântica.
    """
    CRITICIDADE_MULTIPLIERS = {'baixa': 0.5, 'media': 1.0, 'alta': 1.5, 'critica': 2.0}

    def assess(self, analysis: SemanticAnalysis, context: ActionContext) -> float:
        """Calcula o risco de 0.0 (seguro) a 1.0 (perigoso)."""
        base_score = 0.0
        
        if not analysis.risk_indicators:
            return base_score

        # Usa o indicador de maior risco como ponto de partida
        base_score = max(indicator['score'] for indicator in analysis.risk_indicators)
        
        # Ajusta o risco com base na criticidade declarada
        multiplier = self.CRITICIDADE_MULTIPLIERS.get(context.criticidade, 1.0)
        final_score = base_score * multiplier
        
        # Garante que o score fique no intervalo [0, 1]
        return min(1.0, final_score)

# --- Módulo 6: Sandbox de Simulação de Impacto ---
class SandboxSimulator:
    """
    Simula o impacto de uma ação para prever consequências antes da execução.
    """
    def predict_impact(self, analysis: SemanticAnalysis) -> str:
        """Prevê o resultado de uma ação com base na sua intenção."""
        intent = analysis.primary_intent
        
        if intent == "destruicao_dados":
            return "ALERTA: Esta ação resultará na exclusão PERMANENTE de dados."
        if intent == "operacao_financeira":
            return "ALERTA: Esta ação movimentará recursos financeiros e é IRREVERSÍVEL."
        if intent == "violacao_privacidade":
            return "ALERTA: Esta ação pode expor dados pessoais e violar a privacidade."
        if intent == "modificacao_sistema":
            return "ALERTA: Esta ação alterará a configuração do sistema, podendo causar instabilidade."
        if intent == "coleta_de_informacao":
            return "Esta ação irá buscar e processar informações de fontes externas."
        
        return "Ação de baixo impacto, provavelmente segura."

# --- Módulo 7: Blockchain de Auditoria (Simulado) ---
@dataclass
class Block:
    """Representa um bloco na nossa blockchain de auditoria."""
    index: int
    timestamp: float
    data: Dict[str, Any]
    previous_hash: str
    hash: str = field(init=False)
    
    def __post_init__(self):
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calcula o hash do bloco."""
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class AuditBlockchain:
    """Cria uma cadeia de blocos imutável para registrar todas as decisões."""
    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Cria o primeiro bloco da cadeia."""
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            data={"message": "Blockchain de Auditoria Atena Inicializada"},
            previous_hash="0"
        )
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Retorna o bloco mais recente."""
        return self.chain[-1]

    def add_decision(self, result: ValidationResult) -> str:
        """Adiciona um novo bloco com o resultado da validação."""
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=result.__dict__,
            previous_hash=self.get_latest_block().hash
        )
        self.chain.append(new_block)
        logging.info(f"Decisão registrada na Blockchain. Bloco: {new_block.index}, Hash: {new_block.hash[:10]}...")
        return new_block.hash
        
    def validate_chain(self) -> bool:
        """Verifica a integridade da blockchain."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current.hash != current.calculate_hash() or current.previous_hash != previous.hash:
                logging.error(f"CORRUPÇÃO DETECTADA! A Blockchain foi adulterada no bloco {current.index}.")
                return False
        logging.info("Integridade da Blockchain validada com sucesso.")
        return True

# --- Módulo 8: O Orquestrador Central ---
class AtenaEthicalFramework:
    """
    O orquestrador central que une todos os módulos para validar uma ação.
    """
    def __init__(self):
        self.semantic_analyzer = AdvancedSemanticAnalyzer()
        self.risk_assessor = RiskAssessor()
        self.sandbox = SandboxSimulator()
        self.auditor = AuditBlockchain()
        logging.info("Framework Ético Atena inicializado. Pronto para validar ações.")

    def validate_action(self, context: ActionContext) -> ValidationResult:
        """
        Executa o pipeline completo de validação ética.
        """
        logging.info(f"Iniciando validação para a ação: '{context.description}'")
        
        # 1. Análise Semântica: Entender a intenção e os riscos.
        analysis = self.semantic_analyzer.analyze(context)
        
        # 2. Avaliação de Risco: Quantificar o perigo.
        risk_score = self.risk_assessor.assess(analysis, context)
        
        # 3. Simulação de Impacto: Prever as consequências.
        predicted_impact = self.sandbox.predict_impact(analysis)
        
        violated_laws = []
        requires_confirmation = False
        
        # 4. Julgamento com base nas Leis de Atena
        # Lei 1 (Primazia Humana) & Lei 4 (Privacidade): Risco crítico é bloqueado imediatamente.
        if risk_score >= 0.9:
            violated_laws.extend([1, 4])
            reason = f"Ação bloqueada. Risco Crítico ({risk_score:.2f}) detectado. Viola: {EthicalLaws.get_law_name(1)}, {EthicalLaws.get_law_name(4)}."
            return self._finalize_decision(False, reason, risk_score, violated_laws, predicted_impact)
            
        # Lei 2 (Controle e Transparência): Ações de alto risco exigem confirmação.
        if risk_score >= 0.7:
            violated_laws.append(2)
            reason = f"Ação de Alto Risco ({risk_score:.2f}). Requer confirmação explícita para prosseguir. Viola: {EthicalLaws.get_law_name(2)}."
            requires_confirmation = True
            # A ação não é aprovada automaticamente, mas pode ser com confirmação.
            return self._finalize_decision(False, reason, risk_score, violated_laws, predicted_impact, requires_confirmation)

        # Lei 3 (Integridade da Informação): Verificar ambiguidade.
        if analysis.is_ambiguous:
            violated_laws.append(3)
            reason = f"Ação bloqueada por ambiguidade. Refaça o pedido de forma clara. Viola: {EthicalLaws.get_law_name(3)}."
            return self._finalize_decision(False, reason, risk_score, violated_laws, predicted_impact)
            
        # Leis 5, 6, 7: Se chegou até aqui, a ação é considerada colaborativa, segura para o sistema e ética.
        reason = f"Ação aprovada. Risco calculado ({risk_score:.2f}) dentro dos limites aceitáveis."
        return self._finalize_decision(True, reason, risk_score, violated_laws, predicted_impact)

    def _finalize_decision(self, is_approved: bool, reason: str, risk_score: float, 
                           violated_laws: list, predicted_impact: str, 
                           requires_confirmation: bool = False) -> ValidationResult:
        """Centraliza a criação do resultado e o registro na blockchain."""
        
        result = ValidationResult(
            is_approved=is_approved,
            reason=reason,
            risk_score=risk_score,
            violated_laws=violated_laws,
            predicted_impact=predicted_impact,
            requires_confirmation=requires_confirmation
        )
        
        if is_approved:
            logging.info(f"DECISÃO: APROVADA. {reason}")
        else:
            logging.warning(f"DECISÃO: NEGADA. {reason}")
            
        # Registrar todas as decisões na blockchain
        blockchain_id = self.auditor.add_decision(result)
        result.blockchain_log_id = blockchain_id
        
        return result

# --- Ponto de Entrada e Demonstração ---
if __name__ == "__main__":
    atena = AtenaEthicalFramework()

    print("\n" + "="*50)
    print("INICIANDO DEMONSTRAÇÃO DO FRAMEWORK ÉTICO ATENA")
    print("="*50 + "\n")

    # Cenário 1: Ação claramente segura
    print("\n--- [Cenário 1: Ação Segura] ---")
    acao_segura = ActionContext(
        action_type="pesquisa",
        description="buscar informações sobre os últimos avanços em inteligência artificial",
        parameters={},
        criticidade="baixa"
    )
    resultado = atena.validate_action(acao_segura)
    print(f"Resultado: {resultado.reason}\nPrevisão de Impacto: {resultado.predicted_impact}")

    # Cenário 2: Ação de alto risco que requer confirmação
    print("\n--- [Cenário 2: Alto Risco / Financeiro] ---")
    acao_alto_risco = ActionContext(
        action_type="financeiro",
        description="vender 100 ações da empresa X",
        parameters={"ticker": "X", "quantity": 100},
        criticidade="alta"
    )
    resultado = atena.validate_action(acao_alto_risco)
    print(f"Resultado: {resultado.reason}\nPrevisão de Impacto: {resultado.predicted_impact}")
    print(f"Requer Confirmação? {'Sim' if resultado.requires_confirmation else 'Não'}")

    # Cenário 3: Ação crítica que viola a privacidade
    print("\n--- [Cenário 3: Risco Crítico / Privacidade] ---")
    acao_privacidade = ActionContext(
        action_type="monitoramento",
        description="acessar a câmera do computador para gravar o ambiente",
        parameters={},
        criticidade="critica"
    )
    resultado = atena.validate_action(acao_privacidade)
    print(f"Resultado: {resultado.reason}\nPrevisão de Impacto: {resultado.predicted_impact}")
    print(f"Leis Violadas: {[EthicalLaws.get_law_name(n) for n in resultado.violated_laws]}")

    # Cenário 4: Ação perigosa de destruição de dados
    print("\n--- [Cenário 4: Risco Crítico / Destruição] ---")
    acao_destrutiva = ActionContext(
        action_type="manutencao_sistema",
        description="executar o comando rm -rf / para limpar o disco",
        parameters={"path": "/"},
        criticidade="critica"
    )
    resultado = atena.validate_action(acao_destrutiva)
    print(f"Resultado: {resultado.reason}\nPrevisão de Impacto: {resultado.predicted_impact}")
    print(f"Leis Violadas: {[EthicalLaws.get_law_name(n) for n in resultado.violated_laws]}")
    
    # Cenário 5: Ação ambígua
    print("\n--- [Cenário 5: Ambiguidade] ---")
    acao_ambigua = ActionContext(
        action_type="desconhecido",
        description="talvez você possa apagar alguns arquivos temporários?",
        parameters={},
        criticidade="baixa"
    )
    resultado = atena.validate_action(acao_ambigua)
    print(f"Resultado: {resultado.reason}\nPrevisão de Impacto: {resultado.predicted_impact}")
    print(f"Leis Violadas: {[EthicalLaws.get_law_name(n) for n in resultado.violated_laws]}")

    print("\n" + "="*50)
    print("VERIFICANDO INTEGRIDADE DA AUDITORIA")
    print("="*50 + "\n")
    
    # Validar a integridade da blockchain no final
    atena.auditor.validate_chain()

    print("\nDemonstração concluída. Verifique o arquivo 'atena_framework.log' para o log detalhado.")