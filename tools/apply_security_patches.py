"""
security_patches.py — Correções de segurança baseadas na auditoria
Aplica as correções P0 e P1 identificadas no relatório de segurança.
"""
import os
import re

def patch_file(path, patches):
    """Aplica patches (old, new) em um arquivo."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    applied = 0
    for old, new in patches:
        if old in content:
            content = content.replace(old, new)
            applied += 1
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return applied

base = r"C:\Users\dell-\AppData\Local\hermes\atena_evolution"

print("=== Aplicando Patches de Seguranca ===\n")

# P0-1: Remover traceback.print_exc() em produção
p1 = patch_file(os.path.join(base, "train_atena_cpu.py"), [
    (
        '    except Exception as e:\n        logger.error(f"Erro no treinamento: {e}")\n        import traceback\n        traceback.print_exc()',
        '    except Exception as e:\n        logger.error(f"Erro no treinamento: {type(e).__name__}: {str(e)[:100]}")'
    )
])
print(f"  P0-1: traceback.print_exc() removido: {p1} patch(es)")

# P0-2: Corrigir [PI:{m.group(0)}] que vaza input
p2 = patch_file(os.path.join(base, "core/security_guard.py"), [
    (
        're.sub(pattern, lambda m: f"[PI:{m.group(0)][:20}]", sanitized)',
        're.sub(pattern, "[PI:BLOCKED]", sanitized)'
    )
])
print(f"  P0-2: PI leak corrigido: {p2} patch(es)")

# P0-3: CORS wildcard -> origins explícitos
p3 = patch_file(os.path.join(base, "core/atena_api.py"), [
    (
        'allow_origins=["*"],',
        'allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],'
    )
])
print(f"  P0-3: CORS corrigido: {p3} patch(es)")

# P0-4: Esconder str(e) em HTTPException
p4 = patch_file(os.path.join(base, "core/atena_api.py"), [
    (
        'raise HTTPException(status_code=500, detail=str(e))',
        'raise HTTPException(status_code=500, detail="Erro interno do servidor")'
    )
])
print(f"  P0-4: HTTPException str(e) removido: {p4} patch(es)")

# P0-5: Esconder str(e) em atena_evolution_core.py
p5 = patch_file(os.path.join(base, "core/atena_evolution_core.py"), [
    (
        'return TaskResponse(success=False, content=f"Erro: {str(e)}",',
        'return TaskResponse(success=False, content=f"Erro interno: {type(e).__name__}",'
    )
])
print(f"  P0-5: str(e) em TaskResponse removido: {p5} patch(es)")

# P1-1: Adicionar max_length no ChatRequest
p6 = patch_file(os.path.join(base, "core/atena_api.py"), [
    (
        'message: str',
        'message: str = Field(..., min_length=1, max_length=8192)'
    )
])
print(f"  P1-1: max_length no ChatRequest: {p6} patch(es)")

# P1-7: Adicionar Field import se necessário
p12 = patch_file(os.path.join(base, "core/atena_api.py"), [
    (
        'from pydantic import BaseModel',
        'from pydantic import BaseModel, Field'
    )
])
print(f"  P1-7: Field import: {p12} patch(es)")

# P1-8: Adicionar max_tokens/temperature validation
p13 = patch_file(os.path.join(base, "core/atena_api.py"), [
    (
        'max_tokens: int = 512',
        'max_tokens: int = Field(default=512, gt=0, le=8192)'
    ),
    (
        'temperature: float = 0.7',
        'temperature: float = Field(default=0.7, ge=0.0, le=1.5)'
    )
])
print(f"  P1-8: Validacao de max_tokens/temperature: {p13} patch(es)")

# P1-4: Default host para 127.0.0.1
p9 = patch_file(os.path.join(base, "atena_evolution_app.py"), [
    (
        'host: str = "0.0.0.0"',
        'host: str = "127.0.0.1"'
    )
])
print(f"  P1-4: Default host 127.0.0.1: {p9} patch(es)")

# P1-5: Adicionar check_same_thread=False no SQLite
p10 = patch_file(os.path.join(base, "core/security_guard.py"), [
    (
        'self._conn = sqlite3.connect(self.db_path)',
        'self._conn = sqlite3.connect(self.db_path, check_same_thread=False)'
    )
])
print(f"  P1-5: SQLite thread-safe: {p10} patch(es)")

total = p1+p2+p3+p4+p5+p6+p9+p10+p12+p13
print(f"\n=== Total: {total} patches aplicados ===")

# Verificar sintaxe dos arquivos modificados
import py_compile
files_to_check = [
    os.path.join(base, "core/security_guard.py"),
    os.path.join(base, "core/atena_api.py"),
    os.path.join(base, "core/atena_evolution_core.py"),
    os.path.join(base, "atena_evolution_app.py"),
    os.path.join(base, "train_atena_cpu.py"),
]

print("\nVerificando sintaxe:")
for f in files_to_check:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {os.path.basename(f)}")
    except py_compile.PyCompileError as e:
        print(f"  ERRO: {os.path.basename(f)}: {e}")
