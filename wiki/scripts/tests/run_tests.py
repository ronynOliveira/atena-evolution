#!/usr/bin/env python3
"""
Script de execucao de testes automatizados do OWL.
Uso: python run_tests.py [--verbose] [--coverage] [--html]
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Diretorio do script
SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent


def check_pytest():
    """Verifica se pytest esta instalado."""
    try:
        import pytest
        print(f"[OK] pytest {pytest.__version__} encontrado")
        return True
    except ImportError:
        print("[ERRO] pytest nao instalado. Execute: pip install pytest")
        return False


def run_tests(verbose=False, coverage=False, html=False):
    """Executa a suite de testes."""
    pytest_args = [sys.executable, "-m", "pytest"]

    # Diretorio de testes
    pytest_args.append(str(SCRIPT_DIR))

    # Verbose
    if verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-v")  # Sempre verbose para melhor output

    # Cobertura
    if coverage:
        try:
            import pytest_cov
            pytest_args.extend(["--cov=lib", "--cov-report=term-missing"])
            print("[OK] Cobertura de codigo habilitada")
        except ImportError:
            print("[AVISO] pytest-cov nao instalado. Sem cobertura.")
            print("        Instale com: pip install pytest-cov")

    # HTML report
    if html:
        report_path = SCRIPT_DIR / "report.html"
        pytest_args.extend([f"--html={report_path}", "--self-contained-html"])
        print(f"[OK] Relatorio HTML: {report_path}")

    # Mostrar resumo de testes coletados
    pytest_args.append("--tb=short")  # Traceback curto
    pytest_args.append("-ra")  # Mostrar resumo de todos os testes

    print(f"\n{'='*60}")
    print(f"  OWL - Suite de Testes Automatizados")
    print(f"  Data: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    print(f"Executando: {' '.join(pytest_args)}\n")

    # Adiciona tools/ ao PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(TOOLS_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(pytest_args, cwd=str(TOOLS_DIR), env=env)

    print(f"\n{'='*60}")
    if result.returncode == 0:
        print("  TODOS OS TESTES PASSARAM [OK]")
    else:
        print(f"  FALHAS DETECTADAS (exit code: {result.returncode})")
    print(f"{'='*60}")

    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="OWL - Suite de Testes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Output detalhado")
    parser.add_argument("--coverage", "-c", action="store_true", help="Com cobertura de codigo")
    parser.add_argument("--html", action="store_true", help="Gerar relatorio HTML")
    args = parser.parse_args()

    print("\n[1/3] Verificando dependencias...")
    if not check_pytest():
        sys.exit(1)

    print("\n[2/3] Coletando testes...")
    test_files = list(SCRIPT_DIR.glob("test_*.py"))
    print(f"      Encontrados: {len(test_files)} arquivo(s) de teste")
    for tf in test_files:
        print(f"        - {tf.name}")

    print("\n[3/3] Executando testes...\n")
    exit_code = run_tests(
        verbose=args.verbose,
        coverage=args.coverage,
        html=args.html,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
