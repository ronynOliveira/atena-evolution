import importlib
import os
import sys
from pathlib import Path
import traceback

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

def check_modules():
    # Adiciona o diretório 'backend' ao path do Python
    backend_dir = Path(__file__).parent.resolve()
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    app_dir = backend_dir / "app"
    
    # Lista de todos os arquivos .py no diretório app
    py_files = [f for f in app_dir.glob("**/*.py")]
    
    problematic_modules = []

    for py_file in py_files:
        # Constrói o nome do módulo a partir do caminho do arquivo
        # e.g., C:\...\backend\app\atena_core.py -> app.atena_core
        module_name = ".".join(py_file.relative_to(backend_dir).with_suffix("").parts)

        # Ignora arquivos com nomes inválidos para módulos
        if not all(part.isidentifier() for part in module_name.split(".")) or "reorganize_files" in module_name:
            print(f"Skipping file with non-identifier name: {py_file.name}")
            continue
        
        # O __init__ é especial
        if py_file.name == "__init__.py":
            module_name = module_name.replace(".__init__", "")
            if not module_name:
                continue

        try:
            importlib.import_module(module_name)
            print(f"Successfully imported {module_name}")
        except Exception as e:
            print(f"Error importing {module_name}: {e}")
            print(traceback.format_exc())
            problematic_modules.append(module_name)

    if problematic_modules:
        print("\nThe following modules have import errors:")
        for module in problematic_modules:
            print(module)
    else:
        print("\nAll modules imported successfully!")

if __name__ == "__main__":
    check_modules()