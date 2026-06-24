#!/usr/bin/env python3
"""
AgenteLocal - Camada Agentica Local para o Atena Evolucao
=========================================================

Agente de IA local que funciona SEM custos de API.
Usa o Ollama como backend com o endpoint /api/generate.

Caracteristicas:
- 100% local (sem API externa)
- Identidade Koldi integrada
- 6 modos operacionais
- System prompt hierarquico
- Custo ZERO

Uso:
    from core.agente_local import AgenteLocal
    agente = AgenteLocal()
    resposta = agente.pergunte("Qual e o seu nome?")
"""
import json
import os
import sys
import time
import logging
import urllib.request
from typing import Optional, Dict, Any, List
from pathlib import Path

# Adicionar path do identity engine
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.identity import get_identity, ModoOperacional
from safety import security_manager as _sm_mod
def _get_sm():
    import importlib
    importlib.reload(_sm_mod)
    return _sm_mod.get_security_manager()

# Configuracao
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("ATENA_MODEL", "hermes3:8b")
REQUEST_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "180"))

logger = logging.getLogger("AgenteLocal")


class OllamaClient:
    """Cliente Ollama otimizado para /api/generate."""
    
    def __init__(self, base_url: str = OLLAMA_URL, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def health_check(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except:
            return False
    
    def generate(self, prompt: str, model: str = DEFAULT_MODEL,
                 max_tokens: int = 512, temperature: float = 0.7,
                 system: str = "") -> Optional[str]:
        """Gera resposta via /api/generate (formato Ollama classico)."""
        url = f"{self.base_url}/api/generate"
        
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json"
        })
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generate falhou: {e}")
            return None
    
    def get_models(self) -> List[str]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", data.get("models", []))
                return [m["name"] for m in models]
        except:
            return []


class AgenteLocal:
    """
    Agente IA local com identidade Koldi.
    
    Funciona 100% local sem custos de API.
    Usa Ollama como backend com o modelo hermes3:8b.
    """
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.ollama = OllamaClient()
        self.identity = get_identity()
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.logger = logging.getLogger("AgenteLocal")
        
        # System base
        self.base_system = (
            "Voce e Koldi (Batedor da Nuvem), um assistente tecnico proativo.\n"
            "Responda sempre em portugues do Brasil.\n"
            "Seja direto, preciso e respeitoso.\n"
            "O usuario e o Senhor Roberio, 34 anos, escritor em Diadema/SP.\n"
        )
    
    def _build_system_prompt(self) -> str:
        """Constroi system prompt com identidade e modo atual."""
        identity_block = self.identity.build_identity_block()
        values_block = self.identity.build_values_block()
        context_block = self.identity.build_context_block()
        security_block = self.identity.build_security_block()
        tom_text = self.identity.get_tom()
        tom = {"estilo": tom_text, "verbose": "medio", "uso_metaforas": "liricos" in tom_text or "metaforico" in tom_text}
        
        return (
            f"SISTEMA DE IDENTIDADE KOLDI\n"
            f"==================================================\n"
            f"{identity_block}\n"
            f"[MODO ATUAL]\n"
            f"Modo: {self.identity.modo.value}\n"
            f"Estilo: {tom['estilo']}\n"
            f"Verbose: {tom['verbose']}\n"
            f"\n{values_block}\n"
            f"{security_block}\n"
            f"{context_block}\n"
            f"==================================================\n"
        )
    
    def _detect_and_set_mode(self, pergunta: str):
        """Detecta modo baseado na pergunta e seta no identity engine."""
        modo = self.identity.detectar_modo(pergunta)
        self.identity.set_modo(modo)
    
    def pergunte(self, pergunta: str, max_tokens: int = 512,
                 temperature: float = 0.7) -> str:
        """
        Faz uma pergunta ao agente local.
        
        Args:
            pergunta: Pergunta do usuario
            max_tokens: Maximo de tokens na resposta
            temperature: Criatividade (0.0 a 1.0)
        
        Returns:
            Resposta do agente
        """
        # Detectar modo
        self._detect_and_set_mode(pergunta)
        
        # Verificar acao permitida
        permitida, motivo = self.identity.verificar_acao_permitida(pergunta)
        if not permitida:
            return f"[BLOQUEADO] {motivo}"
        
        # Verificar seguranca do input
        sm = _get_sm()
        input_check = sm.check_input(pergunta)
        if isinstance(input_check, dict) and input_check.get("safe") is False:
            return "[INPUT INVALIDO] " + str(input_check.get("issues", []))
        
        # Construir system prompt
        system = self._build_system_prompt()
        
        # Adicionar historico recente (ultimas 3 mensagens)
        historico = ""
        for msg in self.conversation_history[-3:]:
            if msg["role"] == "user":
                historico += f"\nUsuario: {msg['content']}\n"
            else:
                historico += f"\nKoldi: {msg['content']}\n"
        
        prompt = f"{historico}Usuario: {pergunta}\nKoldi:"
        
        # Gerar resposta
        start = time.time()
        resposta = self.ollama.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system
        )
        elapsed = time.time() - start
        
        if resposta is None:
            return "[ERRO] Ollama nao respondeu"
        
        # Verificar consistencia (retorna tuple)
        try:
            consistencia = self.identity.verificar_consistencia(resposta)
            if isinstance(consistencia, tuple):
                if not consistencia[0]:
                    self.logger.warning(f"Inconsistencia: {consistencia[1]}")
            elif isinstance(consistencia, dict) and not consistencia.get("consistente", True):
                self.logger.warning(f"Inconsistencia: {consistencia.get('problemas', [])}")
        except (TypeError, AttributeError):
            pass
        
        # Salvar no historico
        self.conversation_history.append({"role": "user", "content": pergunta})
        self.conversation_history.append({"role": "assistant", "content": resposta})
        
        self.logger.info(f"Resposta gerada em {elapsed:.1f}s (modo: {self.identity.modo.value})")
        
        return resposta
    
    def chat(self):
        """Modo interativo no terminal."""
        print("=" * 60)
        print("ATENA EVOLUAO - Agente Local (modo interativo)")
        print(f"Modelo: {self.model}")
        print("Custo: ZERO (100% local)")
        print("Digite 'sair' para encerrar")
        print("=" * 60)
        print()
        
        while True:
            try:
                pergunta = input("Voce: ").strip()
                if pergunta.lower() in ["sair", "exit", "q"]:
                    print("Koldi: Ate logo, Senhor Roberio!")
                    break
                if not pergunta:
                    continue
                
                resposta = self.pergunte(pergunta)
                print(f"\nKoldi: {resposta}\n")
            except KeyboardInterrupt:
                print("\nKoldi: Ate logo!")
                break
    
    def pergunte_com_contexto(self, pergunta: str, contexto: str,
                               max_tokens: int = 512) -> str:
        """Pergunta com contexto adicional (documentos, etc)."""
        prompt_com_contexto = f"CONTEXT:\n{contexto}\n\nPERGUNTA: {pergunta}"
        return self.pergunte(prompt_com_contexto, max_tokens=max_tokens)
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informacoes do agente."""
        return {
            "modelo": self.model,
            "modo_atual": self.identity.modo.value,
            "tom": self.identity.get_tom(),
            "modelos_disponiveis": self.ollama.get_models(),
            "ollama_online": self.ollama.health_check(),
            "historico_size": len(self.conversation_history),
        }
    
    def limpar_historico(self):
        """Limpa historico de conversa."""
        self.conversation_history.clear()


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agente Local Atena Evolucao")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama")
    parser.add_argument("--chat", action="store_true", help="Modo interativo")
    parser.add_argument("--pergunta", "-p", type=str, help="Pergunta unica")
    args = parser.parse_args()
    
    agente = AgenteLocal(model=args.model)
    
    if args.chat:
        agente.chat()
    elif args.pergunta:
        print(agente.pergunte(args.pergunta))
    else:
        # Demo
        print("=== DEMO: Agente Local ===")
        print(f"Info: {agente.get_info()}")
        print()
        print("Pergunta: Qual e o seu nome e sua funcao?")
        resposta = agente.pergunte("Qual e o seu nome e sua funcao?")
        print(f"Resposta: {resposta}")
