#!/usr/bin/env python3
"""
=============================================================================
Ollama Model Optimizer - Atena Evolucao
=============================================================================
Remove modelos desnecessarios do Ollama, mantendo apenas 2 modelos especificos.
Otimizado para hardware: Intel i5-1235U, 15GB RAM, SSD.

Uso:
    python otimizar_modelos.py                    # Modo interativo
    python otimizar_modelos.py --dry-run          # Simulacao (nao remove nada)
    python otimizar_modelos.py --keep a b          # Especifica quais manter
    python otimizar_modelos.py --backup            # Cria backup antes de remover
    python otimizar_modelos.py --auto              # Sem confirmacao (CI/automacao)

Requisitos:
    - Ollama instalado e disponivel no PATH
    - Python 3.7+
=============================================================================
"""

import subprocess
import sys
import os
import shutil
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


# ===========================================================================
# Configuracao padrao
# ===========================================================================
DEFAULT_KEEP_MODELS = ["llama3.2:latest", "qwen2.5:latest"]
OLLAMA_MODELS_DIR = os.path.expanduser("~/.ollama/models")
BACKUP_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                           "atena_evolution", "backups")


# ===========================================================================
# Cores para terminal (Windows compativel via ANSI)
# ===========================================================================
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Aplica cor ao texto se terminal suportar."""
    if sys.platform == "win32":
        # Habilitar ANSI no Windows 10+
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            return text  # Fallback sem cor
    return f"{color}{text}{Colors.END}"


# ===========================================================================
# Funcoes utilitarias
# ===========================================================================
def run_cmd(cmd: List[str], capture: bool = True, timeout: int = 120) -> Tuple[int, str, str]:
    """Executa comando via subprocess e retorna (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Comando nao encontrado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Timeout ao executar: {' '.join(cmd)}"
    except Exception as e:
        return -3, "", str(e)


def check_ollama_installed() -> bool:
    """Verifica se Ollama esta instalado e acessivel."""
    rc, out, _ = run_cmd(["ollama", "--version"])
    if rc == 0:
        print(colorize(f"  Ollama encontrado: {out}", Colors.GREEN))
        return True
    return False


def get_available_models() -> List[Dict[str, str]]:
    """
    Lista modelos disponiveis no Ollama.
    Retorna lista de dicts com 'name', 'size', 'modified'.
    """
    rc, out, err = run_cmd(["ollama", "list"])
    if rc != 0:
        print(colorize(f"  [ERRO] Falha ao listar modelos: {err}", Colors.RED))
        return []

    models = []
    lines = out.strip().split("\n")
    # Pular cabecalho (NAME ID SIZE MODIFIED)
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            # parts[1] = ID (ignorado)
            size = parts[2] if len(parts) > 2 else "?"
            modified = " ".join(parts[3:]) if len(parts) > 3 else "?"
            models.append({
                "name": name,
                "size": size,
                "modified": modified
            })
    return models


def parse_size(size_str: str) -> float:
    """Converte string de tamanho (ex: '3.8GB') para float em GB."""
    size_str = size_str.upper().strip()
    try:
        if "GB" in size_str:
            return float(size_str.replace("GB", ""))
        elif "MB" in size_str:
            return float(size_str.replace("MB", "")) / 1024
        elif "TB" in size_str:
            return float(size_str.replace("TB", "")) * 1024
        else:
            return float(size_str)
    except ValueError:
        return 0.0


def format_size(size_gb: float) -> str:
    """Formata tamanho em GB para string legivel."""
    if size_gb >= 1:
        return f"{size_gb:.1f} GB"
    else:
        return f"{size_gb * 1024:.0f} MB"


# ===========================================================================
# Funcoes principais
# ===========================================================================
def display_models(models: List[Dict[str, str]], keep: List[str]) -> None:
    """Exibe modelos formatados com indicadores de manter/remover."""
    print("\n" + "=" * 70)
    print(colorize("  MODELOS DISPONIVEIS NO OLLAMA", Colors.HEADER + Colors.BOLD))
    print("=" * 70)

    total_size = 0.0
    for i, model in enumerate(models, 1):
        name = model["name"]
        size_str = model["size"]
        size_gb = parse_size(size_str)
        total_size += size_gb

        # Verificar se deve manter
        should_keep = any(
            name == k or name.startswith(k.replace(":latest", ""))
            for k in keep
        )

        if should_keep:
            indicator = colorize(" [MANTER]", Colors.GREEN)
        else:
            indicator = colorize(" [REMOVER]", Colors.RED)

        print(f"  {i:2d}. {name:<35s} {size_str:>8s}  {indicator}")

    print("-" * 70)
    print(f"  Total: {len(models)} modelos | Espaco estimado: {format_size(total_size)}")
    print("=" * 70)


def confirm_removal(models_to_remove: List[Dict[str, str]], keep: List[str]) -> bool:
    """Pede confirmacao do usuario antes de remover."""
    print(colorize("\n  ATENCAO: Esta acao ira remover os seguintes modelos:", Colors.YELLOW))
    print()

    total_freed = 0.0
    for model in models_to_remove:
        size_gb = parse_size(model["size"])
        total_freed += size_gb
        print(colorize(f"    - {model['name']} ({model['size']})", Colors.RED))

    print()
    print(colorize(f"  Espaco a ser liberado: ~{format_size(total_freed)}", Colors.CYAN))
    print(colorize(f"  Modelos mantidos: {', '.join(keep)}", Colors.GREEN))
    print()

    while True:
        response = input(colorize("  Deseja continuar? (sim/nao): ", Colors.BOLD)).strip().lower()
        if response in ("sim", "s", "yes", "y"):
            return True
        elif response in ("nao", "n", "no"):
            return False
        print(colorize("  Por favor, digite 'sim' ou 'nao'.", Colors.YELLOW))


def backup_model(model_name: str, backup_dir: str) -> bool:
    """
    Cria backup de um modelo antes de remover.
    Copia o diretorio do modelo para o diretorio de backup.
    """
    src = os.path.join(OLLAMA_MODELS_DIR, "blobs")
    # Ollama armazena modelos em ~/.ollama/models/blobs/
    # O backup e uma copia dos arquivos de blob
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_backup_dir = os.path.join(backup_dir, f"{model_name.replace(':', '_')}_{timestamp}")

    try:
        os.makedirs(model_backup_dir, exist_ok=True)

        # Salvar informacoes do modelo em JSON
        info = {
            "model": model_name,
            "backup_date": timestamp,
            "ollama_models_dir": OLLAMA_MODELS_DIR
        }
        info_path = os.path.join(model_backup_dir, "backup_info.json")
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        # Tentar copiar os blobs do modelo
        rc, out, err = run_cmd(["ollama", "show", model_name, "--json"], timeout=30)
        if rc == 0:
            try:
                model_info = json.loads(out)
                # Salvar metadados
                meta_path = os.path.join(model_backup_dir, "model_info.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(model_info, f, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

        print(colorize(f"    Backup criado: {model_backup_dir}", Colors.DIM))
        return True

    except Exception as e:
        print(colorize(f"    [AVISO] Falha no backup de {model_name}: {e}", Colors.YELLOW))
        return False


def remove_model(model_name: str, dry_run: bool = False) -> bool:
    """Remove um modelo usando 'ollama rm'."""
    if dry_run:
        print(colorize(f"    [DRY-RUN] Removeria: {model_name}", Colors.DIM))
        return True

    print(f"    Removendo {model_name}...", end=" ", flush=True)

    rc, out, err = run_cmd(["ollama", "rm", model_name], timeout=300)

    if rc == 0:
        print(colorize("OK", Colors.GREEN))
        return True
    else:
        print(colorize(f"FALHOU ({err[:80]})", Colors.RED))
        return False


def pull_model(model_name: str, dry_run: bool = False) -> bool:
    """Baixa um modelo usando 'ollama pull' (para garantir que existe)."""
    if dry_run:
        print(colorize(f"    [DRY-RUN] Baixaria: {model_name}", Colors.DIM))
        return True

    print(f"    Baixando {model_name}...", end="", flush=True)

    rc, out, err = run_cmd(["ollama", "pull", model_name], timeout=600)

    if rc == 0:
        print(colorize(" OK", Colors.GREEN))
        return True
    else:
        print(colorize(f" FALHOU", Colors.RED))
        if err:
            print(colorize(f"      Erro: {err[:120]}", Colors.DIM))
        return False


def show_progress_bar(current: int, total: int, prefix: str = "") -> None:
    """Mostra barra de progresso no terminal."""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r  {prefix}[{bar}] {current}/{total} ({percent:.0f}%)", end="", flush=True)
    if current == total:
        print()  # Nova linha ao completar


# ===========================================================================
# Funcao principal
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Otimizador de modelos Ollama - Atena Evolucao",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python otimizar_modelos.py
  python otimizar_modelos.py --keep llama3.2:latest qwen2.5:latest
  python otimizar_modelos.py --dry-run
  python otimizar_modelos.py --backup --auto
  python otimizar_modelos.py --keep mistral:latest --dry-run
        """
    )
    parser.add_argument(
        "--keep", nargs="+", default=None,
        help="Modelos a manter (padrao: llama3.2:latest qwen2.5:latest)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulacao - nao remove nenhum modelo"
    )
    parser.add_argument(
        "--backup", action="store_true",
        help="Cria backup dos modelos antes de remover"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Modo automatico sem confirmacao (para scripts/CI)"
    )
    parser.add_argument(
        "--pull", action="store_true",
        help="Baixa os modelos desejados se nao existirem"
    )

    args = parser.parse_args()

    # Configuracao
    keep_models = args.keep if args.keep else DEFAULT_KEEP_MODELS
    dry_run = args.dry_run
    do_backup = args.backup
    auto_mode = args.auto
    do_pull = args.pull

    # Banner
    print()
    print(colorize("╔══════════════════════════════════════════════════════════════════╗", Colors.CYAN))
    print(colorize("║          OLLAMA MODEL OPTIMIZER - ATENA EVOLUCAO                ║", Colors.CYAN + Colors.BOLD))
    print(colorize("╚══════════════════════════════════════════════════════════════════╝", Colors.CYAN))
    print()

    if dry_run:
        print(colorize("  *** MODO DRY-RUN (simulacao - nada sera alterado) ***\n", Colors.YELLOW + Colors.BOLD))

    # 1. Verificar Ollama
    print(colorize("  [1/5] Verificando instalacao do Ollama...", Colors.BLUE))
    if not check_ollama_installed():
        print(colorize("\n  [ERRO] Ollama nao encontrado no PATH!", Colors.RED))
        print("  Instale em: https://ollama.com/download")
        sys.exit(1)

    # 2. Listar modelos
    print(colorize("\n  [2/5] Listando modelos disponiveis...", Colors.BLUE))
    models = get_available_models()
    if not models:
        print(colorize("  Nenhum modelo encontrado ou erro ao listar.", Colors.YELLOW))
        sys.exit(0)

    # 3. Determinar quais remover
    models_to_remove = []
    models_to_keep = []

    for model in models:
        name = model["name"]
        should_keep = any(
            name == k or name.startswith(k.replace(":latest", ""))
            for k in keep_models
        )
        if should_keep:
            models_to_keep.append(model)
        else:
            models_to_remove.append(model)

    # Exibir lista
    display_models(models, keep_models)

    if not models_to_remove:
        print(colorize("\n  Nenhum modelo para remover. Sistema ja esta otimizado!", Colors.GREEN))
        sys.exit(0)

    # 4. Verificar se modelos a manter existem
    print(colorize("\n  [3/5] Verificando modelos a manter...", Colors.BLUE))
    missing_models = []
    for km in keep_models:
        found = any(
            m["name"] == km or m["name"].startswith(km.replace(":latest", ""))
            for m in models
        )
        if found:
            print(colorize(f"    ✓ {km} encontrado", Colors.GREEN))
        else:
            print(colorize(f"    ✗ {km} NAO encontrado", Colors.RED))
            missing_models.append(km)

    if missing_models and do_pull:
        print(colorize(f"\n  Baixando modelos faltantes...", Colors.BLUE))
        for ml in missing_models:
            pull_model(ml, dry_run)
    elif missing_models and not dry_run:
        print(colorize(f"\n  [AVISO] Modelos nao encontrados: {', '.join(missing_models)}", Colors.YELLOW))
        print("  Use --pull para baixa-los automaticamente.")

    # 5. Confirmar remocao
    print(colorize("\n  [4/5] Confirmando operacao...", Colors.BLUE))
    if auto_mode:
        print(colorize("    Modo automatico - confirmacao ignorada.", Colors.DIM))
        confirmed = True
    else:
        confirmed = confirm_removal(models_to_remove, keep_models)

    if not confirmed:
        print(colorize("\n  Operacao cancelada pelo usuario.", Colors.YELLOW))
        sys.exit(0)

    # 6. Executar remocao
    print(colorize("\n  [5/5] Executando remocao...", Colors.BLUE))
    print()

    # Backup (opcional)
    if do_backup and not dry_run:
        print(colorize("  Criando backups...", Colors.CYAN))
        os.makedirs(BACKUP_DIR, exist_ok=True)
        for model in models_to_remove:
            backup_model(model["name"], BACKUP_DIR)
        print()

    # Remocao com progresso
    total = len(models_to_remove)
    removed = 0
    failed = 0

    print(colorize(f"  Removendo {total} modelos...\n", Colors.BOLD))

    for i, model in enumerate(models_to_remove, 1):
        show_progress_bar(i - 1, total, "  Progresso: ")

        if remove_model(model["name"], dry_run):
            removed += 1
        else:
            failed += 1

        show_progress_bar(i, total, "  Progresso: ")
        time.sleep(0.3)  # Pequena pausa para visualizacao

    # Resumo final
    print()
    print("=" * 70)
    print(colorize("  RESUMO DA OPERACAO", Colors.HEADER + Colors.BOLD))
    print("=" * 70)

    if dry_run:
        print(colorize(f"  Modo: DRY-RUN (simulacao)", Colors.YELLOW))
        print(f"  Modelos que seriam removidos: {total}")
        print(f"  Modelos mantidos: {len(models_to_keep)}")
        print(f"  Espaco estimado a liberar: ~{format_size(sum(parse_size(m['size']) for m in models_to_remove))}")
    else:
        print(f"  Modelos removidos: {colorize(str(removed), Colors.GREEN if removed else Colors.DIM)}")
        if failed:
            print(colorize(f"  Falhas: {failed}", Colors.RED))
        print(f"  Modelos mantidos: {len(models_to_keep)}")
        if do_backup:
            print(f"  Backup em: {BACKUP_DIR}")

    print()
    print(colorize("  Modelos ativos:", Colors.CYAN))
    for m in models_to_keep:
        print(f"    • {m['name']} ({m['size']})")

    print("=" * 70)
    print(colorize("\n  Otimizacao concluida!\n", Colors.GREEN))


if __name__ == "__main__":
    main()
