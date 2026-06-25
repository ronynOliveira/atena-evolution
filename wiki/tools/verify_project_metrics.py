"""
verify_project_metrics.py — Verifica metricas do projeto contra o que foi reportado.
Uso: python verify_project_metrics.py <arquivo_relatorio>
"""
import subprocess
import os
import sys
import re


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()


def verify(report_file):
    base = os.path.dirname(os.path.dirname(os.path.abspath(report_file)))
    os.chdir(base)

    # Metricas reais
    py_files = run("dir /s /b *.py 2>nul | findstr /v __pycache__")
    py_count = len([f for f in py_files.split("\n") if f.strip()])

    commits = run("git log --oneline")
    commit_count = len([l for l in commits.split("\n") if l.strip()])

    # Testes reais
    test_output = run("pytest tests/test_atena_memory.py --collect-only -q 2>nul")
    test_lines = test_output.strip().split("\n")
    test_count = 0
    for line in test_lines:
        if "test_" in line and "PASSED" not in line and "FAILED" not in line:
            test_count += 1

    # Linhas de codigo
    lines_output = run("findstr /r /s /i . *.py 2>nul | find /c /v \"\"")

    real = {
        "py_files": py_count,
        "commits": commit_count,
        "tests": test_count,
    }

    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()

    issues = []

    # Verificar arquivos
    match = re.search(r"Arquivos Python:\s*(\d+)", content)
    if match:
        reported = int(match.group(1))
        if reported != real["py_files"]:
            issues.append(f"Arquivos Python: reportado={reported}, real={real['py_files']}")

    # Verificar commits
    match = re.search(r"Commits:\s*(\d+)", content)
    if match:
        reported = int(match.group(1))
        if reported != real["commits"]:
            issues.append(f"Commits: reportado={reported}, real={real['commits']}")

    # Verificar testes
    match = re.search(r"(\d+) testes.*passando", content)
    if match:
        reported = int(match.group(1))
        if reported != real["tests"]:
            issues.append(f"Testes: reportado={reported}, real={real['tests']}")

    # Verificar IPs
    ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", content)
    if ips:
        issues.append(f"IPs encontrados: {ips} - substituir por placeholders")

    # Verificar caminhos absolutos do usuario
    if "C:\\Users\\dell-" in content or "C:/Users/dell-" in content:
        issues.append("Caminhos absolutos do usuario encontrados - substituir por placeholders")

    return issues, real


if __name__ == "__main__":
    report = sys.argv[1] if len(sys.argv) > 1 else ""
    if not report:
        print("Uso: python verify_project_metrics.py <arquivo_relatorio>")
        sys.exit(1)

    issues, real = verify(report)

    print(f"=== Metricas Reais ===")
    print(f"Arquivos Python: {real['py_files']}")
    print(f"Commits: {real['commits']}")
    print(f"Testes: {real['tests']}")

    if issues:
        print(f"\n=== DIVERGENCIAS ({len(issues)}) ===")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print(f"\nOK: Todas as metricas verificadas")
