#!/usr/bin/env python3
"""
security_manager.py — Central de Seguranca Integrada da Atena Evolucao

Integra todos os modulos de seguranca do projeto num unico ponto de entrada.
Gerencia: SafetyGuard, AsFTGuard, NeSTGuard, SecurityWatchdog,
InputSanitizer, OutputValidator, DeepScanner, HardeningManager, IntegrityChecker.

Uso:
    from safety.security_manager import get_security_manager
    sm = get_security_manager()
    print(sm.get_security_report())
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .safety_guard import SafetyGuard, AsFTGuard, NeSTGuard
from .security_watchdog import SecurityWatchdog
from .security_layer import InputSanitizer, OutputValidator, MemoryIntegrityChecker, AnomalyDetector
from . import security_scan_deep as deep_scan
from . import hardening as hrd
from . import verify_integrity as vint

logger = logging.getLogger("SecurityManager")


class IntegrityChecker:
    """Wrapper para verify_integrity.py — verifica SHA256 dos arquivos de identidade."""

    def __init__(self):
        self.results: Dict[str, Any] = {}

    def check_files(self, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Verifica integridade SHA256 de arquivos.
        Se files for None, usa a lista do checksums.sha256.
        Retorna dict com 'ok', 'failed', 'missing'.
        """
        self.results = {"ok": [], "failed": [], "missing": []}

        expected = vint.load_expected()
        if expected is None:
            return {"error": "checksums.sha256 nao encontrado", **self.results}

        for name, exp_hash in expected.items():
            if files is not None and name not in files:
                continue
            path = os.path.join(vint._BASE, name)
            if not os.path.exists(path):
                self.results["missing"].append(name)
                continue
            current = vint.sha256_file(path)
            if current == exp_hash:
                self.results["ok"].append(name)
            else:
                self.results["failed"].append(name)

        return dict(self.results)

    def verify_all(self) -> Dict[str, Any]:
        """Verifica todos os arquivos do checksums.sha256."""
        return self.check_files()

    def update_checksums(self) -> None:
        """Recalcula e salva checksums."""
        vint.update()


class DeepScanner:
    """Wrapper para security_scan_deep.py — varredura profunda de seguranca."""

    def __init__(self):
        self.last_report: Dict[str, Any] = {}
        self.last_findings: List[Dict] = []

    def scan_all(self) -> Dict[str, Any]:
        """Executa todas as varreduras profundas."""
        all_findings = []
        scan_meta: Dict[str, Any] = {}

        skill_meta = deep_scan.check_skill_patterns_loaded()
        scan_meta["skill_meta"] = skill_meta

        py_findings, scripts_scanned = deep_scan.scan_python_files_for_secrets()
        all_findings.extend(py_findings)
        scan_meta["scripts_scanned"] = scripts_scanned

        git_findings, git_meta = deep_scan.scan_git_history()
        all_findings.extend(git_findings)
        scan_meta["git_meta"] = git_meta

        cron_findings, cron_meta = deep_scan.scan_cron_jobs()
        all_findings.extend(cron_findings)
        scan_meta["cron_meta"] = cron_meta

        net_findings, net_meta = deep_scan.scan_network_services()
        all_findings.extend(net_findings)
        scan_meta["net_meta"] = net_meta

        self.last_findings = all_findings
        self.last_report = deep_scan.generate_report(all_findings, scan_meta)
        return dict(self.last_report)

    def get_findings(self) -> List[Dict]:
        """Retorna o ultimo conjunto de achados."""
        return list(self.last_findings)

    def get_critical_count(self) -> int:
        """Retorna numero de achados criticos."""
        return self.last_report.get("summary", {}).get("critical", 0)


class HardeningManager:
    """Wrapper para hardening.py — varredura e correcao de permissoes."""

    def __init__(self):
        self.last_report: Dict[str, Any] = {}

    def scan(self) -> Dict[str, Any]:
        """Executa varredura de permissoes e configuracoes."""
        self.last_report = hrd.scan()
        return dict(self.last_report)

    def fix(self) -> int:
        """Corrige problemas de permissao encontrados."""
        report = self.scan()
        hrd.fix(report)
        return report.get("total_issues", 0)

    def check_disk(self) -> Dict[str, Any]:
        """Verifica espaco em disco."""
        return hrd.check_disk()

    def generate_report(self) -> str:
        """Relatorio legivel de hardening."""
        if not self.last_report:
            self.scan()
        return hrd.generate_report(self.last_report)


class SecurityManager:
    """
    Gerenciador central de seguranca.

    Inicializa e coordena todos os sub-modulos de seguranca do projeto.
    """

    _instance: Optional["SecurityManager"] = None

    def __init__(self):
        if SecurityManager._instance is not None:
            raise RuntimeError("Use get_security_manager() para obter a instancia unica")

        self.safety_guard = SafetyGuard(strict_mode=False)
        self.asft_guard = AsFTGuard()
        self.nest_guard = NeSTGuard()
        self.watchdog = SecurityWatchdog()
        self.input_sanitizer = InputSanitizer()
        self.output_validator = OutputValidator()
        self.memory_integrity = MemoryIntegrityChecker()
        self.anomaly_detector = AnomalyDetector()
        self.deep_scanner = DeepScanner()
        self.hardening = HardeningManager()
        self.integrity_checker = IntegrityChecker()

        self._scan_history: List[Dict] = []
        logger.info("SecurityManager inicializado com %d modulos", 11)

    def full_scan(self) -> Dict[str, Any]:
        """
        Executa varredura completa: integridade + credenciais + permissoes.
        Retorna relatorio consolidado.
        """
        result: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "integrity": {},
            "credentials": {},
            "permissions": {},
            "deep_scan": {},
        }

        result["integrity"] = self.integrity_checker.verify_all()

        self.watchdog.check_credential_leaks()
        result["credentials"] = {
            "events": list(self.watchdog.events),
        }

        result["permissions"] = self.hardening.scan()

        result["deep_scan"] = self.deep_scanner.scan_all()

        self._scan_history.append(result)
        return result

    def check_input(self, input_text: str) -> Dict[str, Any]:
        """
        Valida input do usuario com sanitizacao.
        Retorna resultado do InputSanitizer.
        """
        return self.input_sanitizer.sanitize(input_text)

    def check_output(self, output_text: str, context: str = "general") -> Dict[str, Any]:
        """
        Valida output antes de enviar com filtro de conteudo.
        Retorna resultado do OutputValidator.
        """
        safe_check = asyncio.run(self.safety_guard.check(output_text))
        if safe_check != output_text:
            return {
                "safe": False,
                "risk_level": "CRITICAL",
                "issues": ["SAFETY_GUARD_BLOCKED"],
                "action": "block",
            }
        return self.output_validator.validate(output_text, context)

    def check_file_integrity(self, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Verifica integridade SHA256 de arquivos especificos.
        Se files for None, verifica todos os arquivos monitorados.
        """
        return self.integrity_checker.check_files(files)

    def check_credentials(self) -> List[Dict]:
        """
        Verifica se ha credenciais expostas em scripts.
        Retorna eventos de credenciais encontradas.
        """
        self.watchdog.check_credential_leaks()
        self.watchdog.check_file_integrity()
        cred_events = [
            e for e in self.watchdog.events
            if e.get("type") == "CREDENTIAL_LEAK"
        ]
        return cred_events

    def get_security_report(self) -> Dict[str, Any]:
        """
        Relatorio completo de seguranca consolidando todos os modulos.
        """
        report: Dict[str, Any] = {
            "report_type": "full_security_report",
            "timestamp": datetime.now().isoformat(),
            "modules": {
                "safety_guard": self.safety_guard.get_stats(),
                "watchdog_events": len(self.watchdog.events),
                "anomalies": self.anomaly_detector.check_anomalies(),
                "deep_scan_findings": len(self.deep_scanner.last_findings),
            },
            "integrity": self.integrity_checker.verify_all(),
            "hardening": self.hardening.scan(),
            "score": self.get_security_score(),
        }

        return report

    def get_security_score(self) -> int:
        """
        Retorna score de seguranca 0-100.
        Calcula baseado em: integridade, credenciais, permissoes, anomalias.
        """
        score = 100

        integrity = self.integrity_checker.verify_all()
        failed_count = len(integrity.get("failed", []))
        missing_count = len(integrity.get("missing", []))
        score -= (failed_count + missing_count) * 10

        hardening_report = self.hardening.scan()
        high = hardening_report.get("high", 0)
        medium = hardening_report.get("medium", 0)
        low = hardening_report.get("low", 0)
        score -= high * 15
        score -= medium * 5
        score -= low * 2

        anomalies = self.anomaly_detector.check_anomalies()
        score -= len(anomalies) * 10

        self.watchdog.check_credential_leaks()
        cred_events = [
            e for e in self.watchdog.events
            if e.get("type") == "CREDENTIAL_LEAK"
        ]
        score -= len(cred_events) * 20

        return max(0, min(100, score))


def get_security_manager() -> SecurityManager:
    """
    Retorna instancia unica (singleton) do SecurityManager.
    """
    if SecurityManager._instance is None:
        SecurityManager._instance = SecurityManager()
    return SecurityManager._instance


if __name__ == "__main__":
    sm = get_security_manager()
    print(json.dumps(sm.get_security_report(), indent=2, ensure_ascii=False, default=str))
