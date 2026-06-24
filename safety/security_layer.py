#!/usr/bin/env python3
"""
Koldi Security Layer v4.2
Output Validation + Input Sanitization + Anomaly Detection
Baseado em pesquisa de 12/06/2026: OWASP LLM Top 10, Cycode, Stanford HAI
"""

import re
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# === CONFIG ===
LOG_DIR = Path.home() / ".hermes" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
SECURITY_LOG = LOG_DIR / "security_events.jsonl"

# Padrões de prompt injection conhecidos
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|guidelines?|prompts?)",
    r"you\s+are\s+now\s+(a|an|the)\s+",
    r"system\s+(override|bypass|disable|reset)",
    r"new\s+(instructions?|rules?|directives?)\s*:",
    r"forget\s+(everything|all|what)",
    r"disregard\s+(your\s+)?(training|programming|instructions?)",
    r"jailbreak|mode\s*:\s*(developer|admin|root|god)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if|though)",
    r"from\s+now\s+on",
    r"override\s+safety",
    r"bypass\s+(security|filter|restriction)",
    r"DAN|do\s+anything\s+now",
]

# Comandos de alto risco que requerem confirmação
HIGH_RISK_PATTERNS = [
    r"rm\s+(-rf?|--recursive)\s+/",
    r"del\s+/[sfq]",
    r"format\s+[a-z]:",
    r"shutdown\s+(-[rs]|/t)",
    r"reg\s+(delete|add)",
    r"net\s+(user|localgroup|share)",
    r"icacls\s+.*(/grant|/deny|/setowner)",
    r"Remove-Item\s+-Recurse\s+-Force",
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard",
    r"drop\s+(table|database)",
    r"DELETE\s+FROM\s+.*WHERE\s+1\s*=\s*1",
]

# Caminhos sensíveis
SENSITIVE_PATHS = [
    r"\.ssh[\\/]",
    r"\.env",
    r"\.aws[\\/]",
    r"\.hermes[\\/](\.env|config\.yaml|identity)",
    r"cofre[\\/]",
    r"\.gnupg[\\/]",
    r"\.pki[\\/]",
]

# Unicode invisíveis usados em ataques
INVISIBLE_UNICODE = [
    '\u200b',  # Zero-width space
    '\u200c',  # Zero-width non-joiner
    '\u200d',  # Zero-width joiner
    '\u2060',  # Word joiner
    '\ufeff',  # BOM / Zero-width no-break space
    '\u00ad',  # Soft hyphen
    '\u034f',  # Combining grapheme joiner
]


class SecurityEvent:
    """Registra evento de segurança para auditoria."""
    
    def __init__(self, event_type: str, severity: str, detail: str, source: str = "koldi"):
        self.timestamp = datetime.now().isoformat()
        self.event_type = event_type
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW, INFO
        self.detail = detail
        self.source = source
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "type": self.event_type,
            "severity": self.severity,
            "detail": self.detail,
            "source": self.source,
        }
    
    def log(self):
        with open(SECURITY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.to_dict(), ensure_ascii=False) + "\n")


class OutputValidator:
    """Valida outputs de LLM antes de executar (OWASP LLM Top 10)."""
    
    @staticmethod
    def validate(output: str, context: str = "general") -> dict:
        """
        Valida output de modelo.
        Returns: {"safe": bool, "risk_level": str, "issues": list, "action": str}
        """
        issues = []
        risk_level = "LOW"
        action = "allow"
        
        # 1. Verificar comandos de sistema
        for pattern in HIGH_RISK_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"HIGH_RISK_COMMAND: {pattern}")
                risk_level = "HIGH"
                action = "confirm"
        
        # 2. Verificar acesso a caminhos sensíveis
        for pattern in SENSITIVE_PATHS:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"SENSITIVE_PATH_ACCESS: {pattern}")
                if risk_level != "HIGH":
                    risk_level = "MEDIUM"
                if action == "allow":
                    action = "confirm"
        
        # 3. Verificar exfiltração de dados
        exfil_patterns = [
            r"curl\s+.*POST.*-d\s+",
            r"wget\s+.*--post-data",
            r"Invoke-WebRequest.*-Body",
            r"fetch\s*\(.*method:\s*['\"]POST",
        ]
        for pattern in exfil_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"DATA_EXFILTRATION_PATTERN: {pattern}")
                risk_level = "HIGH"
                action = "block"
        
        # 4. Verificar code injection
        if re.search(r"<script|javascript:|on\w+\s*=", output, re.IGNORECASE):
            issues.append("CODE_INJECTION: script tag or event handler detected")
            risk_level = "HIGH"
            action = "block"
        
        # 5. Verificar se contradiz SOUL.md (heurística)
        soul_contradictions = [
            r"ignore\s+(my\s+)?(soul|identity|values|ethics)",
            r"override\s+(my\s+)?(rules|principles|boundaries)",
            r"bypass\s+(safety|security|protection)",
        ]
        for pattern in soul_contradictions:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"SOUL_CONTRADICTION: {pattern}")
                risk_level = "CRITICAL"
                action = "block"
        
        result = {
            "safe": len(issues) == 0,
            "risk_level": risk_level,
            "issues": issues,
            "action": action,  # allow, confirm, block
        }
        
        if not result["safe"]:
            event = SecurityEvent(
                event_type="OUTPUT_VALIDATION",
                severity=risk_level,
                detail=f"Output blocked/flagged: {json.dumps(issues)}",
                source="output_validator"
            )
            event.log()
        
        return result


class InputSanitizer:
    """Sanitiza inputs externos antes de processar."""
    
    @staticmethod
    def sanitize(text: str) -> dict:
        """
        Sanitiza input de texto.
        Returns: {"clean": bool, "threats": list, "sanitized_text": str}
        """
        threats = []
        sanitized = text
        
        # 1. Detectar prompt injection
        for pattern in PROMPT_INJECTION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                threats.append(f"PROMPT_INJECTION: {pattern}")
        
        # 2. Detectar Unicode invisíveis
        for char in INVISIBLE_UNICODE:
            if char in text:
                threats.append(f"INVISIBLE_UNICODE: U+{ord(char):04X}")
                sanitized = sanitized.replace(char, '')
        
        # 3. Detectar salami slicing (heurística: múltiplas solicitações de escalada)
        escalation_keywords = [
            "more permissive", "less restrictive", "expand access",
            "increase limit", "remove constraint", "bypass limit",
            "mais permissivo", "menos restritivo", "expandir acesso",
        ]
        escalation_count = sum(1 for kw in escalation_keywords if kw.lower() in text.lower())
        if escalation_count >= 2:
            threats.append(f"SALAMI_SLICING: {escalation_count} escalation keywords")
        
        # 4. Detectar hidden instructions em markdown/HTML
        hidden_patterns = [
            r'<!--\s*.*?(?:ignore|override|system).*?-->',
            r'\[.*?\]\(javascript:.*?\)',
            r'!\[.*?\]\(https?://.*?\)',  # Imagens com URLs externas (potential tracking)
        ]
        for pattern in hidden_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                threats.append(f"HIDDEN_INSTRUCTION: {len(matches)} matches for {pattern[:30]}")
        
        result = {
            "clean": len(threats) == 0,
            "threats": threats,
            "sanitized_text": sanitized,
        }
        
        if threats:
            event = SecurityEvent(
                event_type="INPUT_SANITIZATION",
                severity="HIGH" if len(threats) > 2 else "MEDIUM",
                detail=f"Input threats detected: {json.dumps(threats)}",
                source="input_sanitizer"
            )
            event.log()
        
        return result


class MemoryIntegrityChecker:
    """Verifica integridade da memória do agente."""
    
    def __init__(self, checksums_file: str = None):
        if checksums_file is None:
            checksums_file = str(Path.home() / ".hermes" / "checksums.sha256")
        self.checksums_file = checksums_file
        self.base_dir = str(Path.home() / ".hermes")
    
    def compute_checksum(self, filepath: str) -> str:
        """Calcula SHA256 de um arquivo."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    
    def verify_file(self, filepath: str, expected_checksum: str) -> bool:
        """Verifica se o checksum de um arquivo corresponde ao esperado."""
        actual = self.compute_checksum(filepath)
        return actual.lower() == expected_checksum.lower()
    
    def verify_all(self) -> dict:
        """Verifica todos os arquivos listados no checksums.sha256."""
        results = {"ok": [], "failed": [], "missing": []}
        
        if not os.path.exists(self.checksums_file):
            return {"error": "checksums.sha256 not found", **results}
        
        with open(self.checksums_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    checksum = parts[0]
                    filepath = parts[1].lstrip("*")
                    
                    # Resolver caminho relativo ao diretório .hermes
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(self.base_dir, filepath)
                    
                    if not os.path.exists(filepath):
                        results["missing"].append(filepath)
                    elif self.verify_file(filepath, checksum):
                        results["ok"].append(filepath)
                    else:
                        results["failed"].append(filepath)
        
        if results["failed"]:
            event = SecurityEvent(
                event_type="MEMORY_INTEGRITY",
                severity="CRITICAL",
                detail=f"Checksum mismatch: {json.dumps(results['failed'])}",
                source="memory_integrity"
            )
            event.log()
        
        return results


class AnomalyDetector:
    """Detecta comportamento anômalo do agente."""
    
    def __init__(self):
        self.log_file = LOG_DIR / "agent_actions.jsonl"
    
    def log_action(self, action: str, details: str = ""):
        """Registra ação para análise posterior."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def check_anomalies(self) -> list:
        """Verifica anomalias nos logs recentes."""
        anomalies = []
        
        if not self.log_file.exists():
            return anomalies
        
        # Ler últimas 100 ações
        actions = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    actions.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        recent = actions[-100:]
        
        # 1. Ações repetitivas (mais de 10 iguais em sequência)
        if len(recent) >= 10:
            last_10 = [a["action"] for a in recent[-10:]]
            if len(set(last_10)) <= 2:
                anomalies.append("REPETITIVE_ACTIONS: 10+ ações similares consecutivas")
        
        # 2. Volume anormal (mais de 50 ações em 5 minutos)
        if len(recent) >= 50:
            try:
                t_first = datetime.fromisoformat(recent[-50]["timestamp"])
                t_last = datetime.fromisoformat(recent[-1]["timestamp"])
                delta = (t_last - t_first).total_seconds()
                if delta < 300:  # 5 minutos
                    anomalies.append(f"HIGH_VOLUME: {len(recent)} ações em {delta:.0f}s")
            except (ValueError, KeyError):
                pass
        
        # 3. Acesso a arquivos sensíveis
        sensitive_access = [a for a in recent if any(
            p in a.get("details", "").lower() 
            for p in [".ssh", ".env", "cofre", "password", "token", "secret"]
        )]
        if len(sensitive_access) > 3:
            anomalies.append(f"SENSITIVE_ACCESS: {len(sensitive_access)} acessos a arquivos sensíveis")
        
        if anomalies:
            event = SecurityEvent(
                event_type="ANOMALY_DETECTION",
                severity="HIGH",
                detail=f"Anomalies: {json.dumps(anomalies)}",
                source="anomaly_detector"
            )
            event.log()
        
        return anomalies


# === CLI ===
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python security_layer.py <comando> [args]")
        print("Comandos:")
        print("  validate-output <text>  - Valida output de LLM")
        print("  sanitize-input <text>   - Sanitiza input externo")
        print("  check-integrity         - Verifica integridade dos arquivos")
        print("  check-anomalies         - Detecta anomalias no comportamento")
        print("  full-check              - Executa todas as verificações")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "validate-output":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Texto: ")
        result = OutputValidator.validate(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "sanitize-input":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Texto: ")
        result = InputSanitizer.sanitize(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "check-integrity":
        checker = MemoryIntegrityChecker()
        result = checker.verify_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "check-anomalies":
        detector = AnomalyDetector()
        anomalies = detector.check_anomalies()
        if anomalies:
            print("ANOMALIAS DETECTADAS:")
            for a in anomalies:
                print(f"  ⚠ {a}")
        else:
            print("✅ Nenhuma anomalia detectada")
    
    elif cmd == "full-check":
        print("=== OUTPUT VALIDATION ===")
        print("✅ OutputValidator carregado")
        
        print("\n=== INPUT SANITIZATION ===")
        print("✅ InputSanitizer carregado")
        
        print("\n=== MEMORY INTEGRITY ===")
        checker = MemoryIntegrityChecker()
        result = checker.verify_all()
        if "error" in result:
            print(f"⚠ {result['error']}")
        else:
            print(f"✅ OK: {len(result['ok'])} arquivos")
            if result['failed']:
                print(f"❌ FALHOU: {len(result['failed'])} arquivos")
            if result['missing']:
                print(f"⚠ AUSENTES: {len(result['missing'])} arquivos")
        
        print("\n=== ANOMALY DETECTION ===")
        detector = AnomalyDetector()
        anomalies = detector.check_anomalies()
        if anomalies:
            for a in anomalies:
                print(f"  ⚠ {a}")
        else:
            print("✅ Nenhuma anomalia")
        
        print("\n=== SECURITY LOG ===")
        if SECURITY_LOG.exists():
            with open(SECURITY_LOG, "r") as f:
                lines = f.readlines()
            print(f"Total eventos: {len(lines)}")
            if lines:
                print("Últimos 3:")
                for line in lines[-3:]:
                    try:
                        evt = json.loads(line)
                        print(f"  [{evt['severity']}] {evt['type']}: {evt['detail'][:80]}")
                    except json.JSONDecodeError:
                        pass
        else:
            print("Nenhum evento registrado ainda")
    
    else:
        print(f"Comando desconhecido: {cmd}")
