# atena_etica_aprimorada.py
# Versão 2.3 - Framework Ético Avançado para Integração (Completo)

import json
import hashlib
import logging
import time
import re
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Union
from enum import Enum, IntEnum
import hmac
import secrets
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor

# --- Configuração de Logging ---
logger = logging.getLogger("AtenaEthicalFramework")

# --- Leis Éticas e Estruturas de Dados ---

class LawPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class EthicalLaw:
    id: int
    name: str
    description: str
    priority: LawPriority
    conditions: List[str]
    exceptions: List[str]

@dataclass
class EthicalDecision:
    is_approved: bool
    reason: str
    confidence: float
    triggered_laws: List[int] = field(default_factory=list)
    conflicting_laws: List[int] = field(default_factory=list)
    suggested_action: Optional[str] = None
    predicted_impact: str = "Nenhum impacto previsto."
    blockchain_log_id: str = ""

class AdvancedEthicalLaws:
    LAWS = {
        1: EthicalLaw(id=1, name="Lei da Primazia e Preservação Humana", description="Proteger a vida, segurança, autonomia e dignidade humana acima de qualquer outro objetivo", priority=LawPriority.CRITICAL, conditions=[], exceptions=[]),
        2: EthicalLaw(id=2, name="Lei da Não Maleficência e Beneficência", description="Evitar causar dano e buscar o bem-estar de todos os envolvidos", priority=LawPriority.CRITICAL, conditions=[], exceptions=[]),
        3: EthicalLaw(id=3, name="Lei da Autonomia e Consentimento Informado", description="Respeitar a capacidade de decisão dos indivíduos e agir com consentimento claro", priority=LawPriority.HIGH, conditions=[], exceptions=[]),
        4: EthicalLaw(id=4, name="Lei da Justiça e Equidade", description="Garantir tratamento justo e imparcial, evitando discriminação e viés", priority=LawPriority.HIGH, conditions=[], exceptions=[]),
        5: EthicalLaw(id=5, name="Lei da Transparência e Responsabilidade", description="Operar de forma aberta, explicando decisões e assumindo responsabilidade por ações", priority=LawPriority.MEDIUM, conditions=[], exceptions=[]),
        6: EthicalLaw(id=6, name="Lei da Privacidade e Segurança de Dados", description="Proteger informações sensíveis e garantir a segurança dos sistemas", priority=LawPriority.MEDIUM, conditions=[], exceptions=[]),
        7: EthicalLaw(id=7, name="Lei da Melhoria Contínua e Adaptabilidade", description="Buscar aprimoramento constante e adaptar-se a novos desafios éticos", priority=LawPriority.LOW, conditions=[], exceptions=[])
    }

    @classmethod
    def get_law(cls, law_id: int) -> Optional[EthicalLaw]:
        return cls.LAWS.get(law_id)

    @classmethod
    def resolve_conflict(cls, conflicting_laws: List[int]) -> List[int]:
        laws = [cls.LAWS[law_id] for law_id in conflicting_laws if law_id in cls.LAWS]
        return sorted(laws, key=lambda x: x.priority.value)

@dataclass
class EnhancedActionContext:
    action_type: str
    description: str
    parameters: Dict[str, Any]
    user_id: str = "senhor_roberio"
    session_id: str = field(default_factory=lambda: secrets.token_hex(16))
    criticidade: str = "baixa"

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

    def analyze(self, context_description: str) -> Dict[str, Any]:
        """Executa a análise semântica da descrição da ação."""
        desc = context_description.lower()
        analysis = {"primary_intent": "operacao_geral_segura", "risk_indicators": [], "is_ambiguous": False}

        # 1. Detectar indicadores de risco
        for key, value in self.RISK_PATTERNS.items():
            if re.search(value['pattern'], desc):
                analysis['risk_indicators'].append({'type': key, 'score': value['score']})
        
        # 2. Inferir a intenção principal (simulação)
        if any(kw in desc for kw in ["pesquisar", "buscar", "ler", "obter"]):
            analysis['primary_intent'] = "coleta_de_informacao"
        elif any(kw in desc for kw in ["criar", "escrever", "gerar"]):
            analysis['primary_intent'] = "criacao_de_conteudo"
        elif analysis['risk_indicators']:
            # Se houver risco, a intenção primária está relacionada a ele
            analysis['primary_intent'] = max(analysis['risk_indicators'], key=lambda x: x['score'])['type']
        
        # 3. Verificar ambiguidade
        if "?" in desc or any(kw in desc for kw in ["talvez", "acho que", "pode ser"]):
            analysis['is_ambiguous'] = True

        return analysis

# --- Módulo 5: Avaliador de Risco ---
class RiskAssessor:
    """
    Calcula uma pontuação de risco consolidada com base na análise semântica.
    """
    CRITICIDADE_MULTIPLIERS = {'baixa': 0.5, 'media': 1.0, 'alta': 1.5, 'critica': 2.0}

    def assess(self, analysis: Dict[str, Any], context_criticidade: str) -> float:
        """Calcula o risco de 0.0 (seguro) a 1.0 (perigoso)."""
        base_score = 0.0
        
        if not analysis.get('risk_indicators'):
            return base_score

        # Usa o indicador de maior risco como ponto de partida
        base_score = max(indicator['score'] for indicator in analysis['risk_indicators'])
        
        # Ajusta o risco com base na criticidade declarada
        multiplier = self.CRITICIDADE_MULTIPLIERS.get(context_criticidade, 1.0)
        final_score = base_score * multiplier
        
        # Garante que o score fique no intervalo [0, 1]
        return min(1.0, final_score)

# --- Módulo 6: Sandbox de Simulação de Impacto ---
@dataclass
class PredictedImpact:
    impact_type: str
    description: str
    severity: float # 0.0 a 1.0
    affected_areas: List[str]

class SandboxSimulator:
    """
    Simula o impacto de uma ação para prever consequências antes da execução.
    """
    def predict_impact(self, analysis: Dict[str, Any]) -> PredictedImpact:
        """Prevê o resultado de uma ação com base na sua intenção."""
        intent = analysis.get('primary_intent', 'unknown')
        risk_indicators = analysis.get('risk_indicators', [])

        if intent == "destruicao_dados":
            return PredictedImpact(
                impact_type="Destruição de Dados",
                description="Esta ação resultará na exclusão PERMANENTE de dados do sistema.",
                severity=1.0,
                affected_areas=["Sistema de Arquivos", "Dados do Usuário"]
            )
        if intent == "operacao_financeira":
            return PredictedImpact(
                impact_type="Impacto Financeiro",
                description="Esta ação movimentará recursos financeiros e é IRREVERSÍVEL.",
                severity=0.8,
                affected_areas=["Contas Financeiras", "Registros de Transação"]
            )
        if intent == "violacao_privacidade":
            return PredictedImpact(
                impact_type="Violação de Privacidade",
                description="Esta ação pode expor dados pessoais sensíveis e violar a privacidade dos usuários.",
                severity=1.0,
                affected_areas=["Dados Pessoais", "Privacidade do Usuário"]
            )
        if intent == "modificacao_sistema":
            return PredictedImpact(
                impact_type="Modificação do Sistema",
                description="Esta ação alterará a configuração do sistema, podendo causar instabilidade ou falhas.",
                severity=0.7,
                affected_areas=["Configuração do Sistema", "Estabilidade Operacional"]
            )
        if intent == "coleta_de_informacao":
            return PredictedImpact(
                impact_type="Coleta de Informação",
                description="Esta ação irá buscar e processar informações de fontes externas. Impacto geralmente baixo.",
                severity=0.1,
                affected_areas=["Nenhum"]
            )
        
        # Se houver indicadores de risco sem intenção específica
        if risk_indicators:
            highest_risk = max(risk_indicators, key=lambda x: x['score'])
            return PredictedImpact(
                impact_type=f"Risco Potencial: {highest_risk['type']}",
                description=f"Ação com potencial de {highest_risk['type']}. Requer atenção.",
                severity=highest_risk['score'],
                affected_areas=["Desconhecido"]
            )

        return PredictedImpact(
            impact_type="Baixo Impacto",
            description="Ação de baixo impacto, provavelmente segura.",
            severity=0.05,
            affected_areas=["Nenhum"]
        )

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
        # Excluir o próprio hash para evitar recursão infinita na serialização
        temp_data = self.__dict__.copy()
        temp_data.pop('hash', None)
        block_string = json.dumps(temp_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class AuditBlockchain:
    """Cria uma cadeia de blocos imutável para registrar todas as decisões."""
    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis_block()
        self.lock = threading.Lock() # Para garantir thread-safety

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
        with self.lock:
            return self.chain[-1]

    def add_decision(self, result: EthicalDecision) -> str:
        """Adiciona um novo bloco com o resultado da validação."""
        with self.lock:
            new_block = Block(
                index=len(self.chain),
                timestamp=time.time(),
                data=result.__dict__,
                previous_hash=self.get_latest_block().hash
            )
            self.chain.append(new_block)
            logger.info(f"Decisão registrada na Blockchain. Bloco: {new_block.index}, Hash: {new_block.hash[:10]}...")
            return new_block.hash
        
    def validate_chain(self) -> bool:
        """Verifica a integridade da blockchain."""
        with self.lock:
            for i in range(1, len(self.chain)):
                current = self.chain[i]
                previous = self.chain[i-1]
                # Recalcula o hash do bloco atual para verificar integridade
                if current.hash != current.calculate_hash() or current.previous_hash != previous.hash:
                    logger.error(f"CORRUPÇÃO DETECTADA! A Blockchain foi adulterada no bloco {current.index}.")
                    return False
            logger.info("Integridade da Blockchain validada com sucesso.")
            return True

# --- Framework Principal Aprimorado ---
class AdvancedAtenaFramework:
    """
    Framework Ético Atena com IA avançada e segurança robusta.
    Agora funciona como um componente do servidor central.
    """
    def __init__(self):
        self.semantic_analyzer = AdvancedSemanticAnalyzer()
        self.risk_assessor = RiskAssessor()
        self.sandbox = SandboxSimulator()
        self.auditor = AuditBlockchain()
        logger.info("Framework Ético Avançado instanciado.")

    def validate_action_advanced(self, context: EnhancedActionContext) -> EthicalDecision:
        """
        Valida uma ação proposta com base nas leis éticas da Atena e análise de IA.
        Retorna uma decisão ética detalhada.
        """
        logger.info(f"Validando ação: {context.action_type} - {context.description[:50]}...")
        
        # 1. Análise de Risco e Conformidade (usando o SemanticAnalyzer)
        ai_analysis = self.semantic_analyzer.analyze(context.description)
        risk_score = self.risk_assessor.assess(ai_analysis, context.criticidade)
        
        # 2. Previsão de Impacto (usando o SandboxSimulator)
        predicted_impact_obj = self.sandbox.predict_impact(ai_analysis)
        
        triggered_laws = set()
        # Adicionar leis acionadas pela análise de risco
        for indicator in ai_analysis.get('risk_indicators', []):
            if indicator['type'] == 'destruicao_dados':
                triggered_laws.add(1) # Lei da Primazia Humana
                triggered_laws.add(2) # Lei da Não Maleficência
            elif indicator['type'] == 'violacao_privacidade':
                triggered_laws.add(6) # Lei da Privacidade
            elif indicator['type'] == 'operacao_financeira':
                triggered_laws.add(4) # Lei da Justiça e Equidade
            elif indicator['type'] == 'desativacao_seguranca':
                triggered_laws.add(2) # Lei da Não Maleficência
            elif indicator['type'] == 'modificacao_sistema':
                triggered_laws.add(2) # Lei da Não Maleficência

        # 3. Avaliação de Criticidade e Leis
        if context.criticidade == "alta" or risk_score > 0.7:
            triggered_laws.add(1) # Lei da Primazia Humana
            triggered_laws.add(2) # Lei da Não Maleficência

        # 4. Tomada de Decisão
        is_approved = True
        reason = "Ação aprovada. Nenhuma violação ética detectada."
        confidence = 0.95 - risk_score
        suggested_action = None

        if ai_analysis['is_ambiguous']:
            is_approved = False
            reason = f"Ação bloqueada por ambiguidade. Refaça o pedido de forma clara. Viola: {AdvancedEthicalLaws.get_law(3).name}."
            triggered_laws.add(3)
            confidence = 0.1
        elif risk_score >= 0.9:
            is_approved = False
            reason = f"Ação bloqueada. Risco Crítico ({risk_score:.2f}) detectado. Viola: {AdvancedEthicalLaws.get_law(1).name}, {AdvancedEthicalLaws.get_law(2).name}."
            triggered_laws.add(1)
            triggered_laws.add(2)
            confidence = 1.0 - risk_score
            suggested_action = "Reavaliar a intenção e remover elementos de risco."
        elif risk_score >= 0.7:
            is_approved = False # Requer confirmação, então não é aprovado automaticamente
            reason = f"Ação de Alto Risco ({risk_score:.2f}). Requer confirmação explícita para prosseguir. Viola: {AdvancedEthicalLaws.get_law(2).name}."
            triggered_laws.add(2)
            confidence = 0.6 - risk_score
            suggested_action = "Monitorar de perto e buscar alternativas mais éticas."
        
        # Criar a decisão ética
        decision = EthicalDecision(
            is_approved=is_approved,
            reason=reason,
            confidence=confidence,
            triggered_laws=list(triggered_laws),
            predicted_impact=predicted_impact_obj.description,
            suggested_action=suggested_action
        )

        # Registrar na blockchain
        decision.blockchain_log_id = self.auditor.add_decision(decision)
        
        return decision

# Exemplo de uso (para testes)
if __name__ == "__main__":
    print("--- Teste do Framework Ético da Atena ---")
    ethical_framework = AdvancedAtenaFramework()

    # Cenário 1: Ação inofensiva
    context1 = EnhancedActionContext(
        action_type="pesquisa_informacao",
        description="Pesquisar sobre a história da inteligência artificial",
        parameters={},
        criticidade="baixa"
    )
    decision1 = ethical_framework.validate_action_advanced(context1)
    print(f"\nCenário 1: {context1.description}")
    print(f"Aprovado: {decision1.is_approved}, Razão: {decision1.reason}, Confiança: {decision1.confidence:.2f}")
    print(f"Leis Acionadas: {decision1.triggered_laws}")
    print(f"Impacto Previsto: {decision1.predicted_impact}")

    # Cenário 2: Ação com potencial de dano
    context2 = EnhancedActionContext(
        action_type="executar_comando",
        description="Comando para prejudicar o sistema de arquivos",
        parameters={"command": "rm -rf /"}, 
        criticidade="alta"
    )
    decision2 = ethical_framework.validate_action_advanced(context2)
    print(f"\nCenário 2: {context2.description}")
    print(f"Aprovado: {decision2.is_approved}, Razão: {decision2.reason}, Confiança: {decision2.confidence:.2f}")
    print(f"Leis Acionadas: {decision2.triggered_laws}")
    print(f"Impacto Previsto: {decision2.predicted_impact}")

    # Cenário 3: Violação de privacidade
    context3 = EnhancedActionContext(
        action_type="acesso_dados",
        description="Tentar acessar dados privados de usuários sem permissão",
        parameters={"data_type": "private_user_info"}
    )
    decision3 = ethical_framework.validate_action_advanced(context3)
    print(f"\nCenário 3: {context3.description}")
    print(f"Aprovado: {decision3.is_approved}, Razão: {decision3.reason}, Confiança: {decision3.confidence:.2f}")
    print(f"Leis Acionadas: {decision3.triggered_laws}")
    print(f"Impacto Previsto: {decision3.predicted_impact}")

    # Cenário 4: Ação com risco baixo, mas com palavra-chave
    context4 = EnhancedActionContext(
        action_type="gerar_texto",
        description="Gerar um texto sobre como causar dano a um computador",
        parameters={"topic": "malware"}
    )
    decision4 = ethical_framework.validate_action_advanced(context4)
    print(f"\nCenário 4: {context4.description}")
    print(f"Aprovado: {decision4.is_approved}, Razão: {decision4.reason}, Confiança: {decision4.confidence:.2f}")
    print(f"Leis Acionadas: {decision4.triggered_laws}")
    print(f"Impacto Previsto: {decision4.predicted_impact}")

    print("\n" + "="*50)
    print("VERIFICANDO INTEGRIDADE DA AUDITORIA")
    print("="*50 + "\n")
    
    # Validar a integridade da blockchain no final
    ethical_framework.auditor.validate_chain()

    print("\nDemonstração concluída. Verifique o arquivo 'atena_framework.log' para o log detalhado.")