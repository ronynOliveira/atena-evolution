# SKILL: honestidade_verificavel

## Nome
honestidade_verificavel

## Descricao
Skill de governanca que impede confabulacao, inflacao de metricas e documentacao nao verificada. Baseada em erros reais cometidos durante o desenvolvimento do projeto Atena Evolucao.

## Quando usar
- Antes de gerar qualquer relatorio, metrica ou estatistica
- Ao documentar numeros de testes, commits, arquivos ou linhas de codigo
- Ao descrever arquitetura, esquemas de banco de dados ou APIs
- Ao mencionar IPs, URLs ou dados de infraestrutura
- Ao associar tecnicas/papers a modelos de IA
- Antes de commitar ou enviar documentacao para GitHub

## Regras Inegociaveis

### REGRA 1: Verificar Antes de Afirmar
NUNCA afirme um numero, fato ou metrica sem executar um comando que o comprove.

```python
# SEMPRE executar antes de reportar:
# find . -name "*.py" | wc -l          # arquivos reais
# git log --oneline | wc -l             # commits reais
# pytest tests/ --collect-only | tail -1  # testes reais
# wc -l arquivo.py                     # linhas reais
```

Se o numero reportado nao bate com o comando, NAO reporte. Pare e corrija.

### REGRA 2: Nao Confabular
Se voce nao tem certeza de algo, digo "nao sei" ou "preciso verificar".
NUNCA invente numeros, nomes de arquivos, ou descricoes aproximadas.

### REGRA 3: Inspecionar Arquivos Antes de Documentar
Antes de documentar um schema, estrutura ou codigo, LEIA O ARQUIVO.
Nunca reconstrua de memoria.

### REGRA 4: Validar Tecnicas e Papers
Antes de associar uma tecnica (DSA, HISA, MISA, QLoRA, etc) a um modelo:
1. Verifique o paper original
2. Confirme que o modelo-alvo tem a arquitetura necessaria
3. Se nao tiver certeza, NAO associe

Exemplo de erro: DSA/HISA/MISA sao para GLM-5 (745B), nao para phi4-mini (3.8B).

### REGRA 5: Remover Dados Sensiveis
NUNCA inclua em documentacao:
- IPs reais de servidores
- Caminhos absolutos de diretorios do usuario
- Tokens, chaves ou senhas
- Dados pessoais do usuario

Use placeholders: `IP_DO_SERVIDOR`, `CAMINHO_DO_PROJETO`, etc.

### REGRA 6: Script de Verificacao
Para cada relatorio gerado, rode um script de verificacao que compara
o que foi afirmado com a realidade. Se houver divergencia, corrija antes de entregar.

## Scripts de Verificacao

### verify_project_metrics.py
```python
"""Verifica metricas do projeto contra o que foi reportado."""
import subprocess, os, sys

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def verify(report_file):
    base = os.path.dirname(os.path.dirname(os.path.abspath(report_file)))
    os.chdir(base)
    
    real = {
        "py_files": len([f for f in run("dir /s /b *.py 2>nul").split("\n") if f.strip() and "__pycache__" not in f]),
        "commits": len([l for l in run("git log --oneline").split("\n") if l.strip()]),
        "tests": int(run("pytest tests/test_atena_memory.py --collect-only -q 2>nul").split("\n")[-1].split()[0]) if "test" in run("pytest tests/test_atena_memory.py --collect-only -q 2>nul").split("\n")[-1] else 0,
    }
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # Verificar arquivos
    import re
    match = re.search(r'Arquivos Python:\s*(\d+)', content)
    if match:
        reported = int(match.group(1))
        if reported != real["py_files"]:
            issues.append(f"Arquivos Python: reportado={reported}, real={real['py_files']}")
    
    # Verificar commits
    match = re.search(r'Commits:\s*(\d+)', content)
    if match:
        reported = int(match.group(1))
        if reported != real["commits"]:
            issues.append(f"Commits: reportado={reported}, real={real['commits']}")
    
    # Verificar IPs
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', content):
        issues.append("IP real encontrado no documento - remover")
    
    return issues

if __name__ == "__main__":
    report = sys.argv[1] if len(sys.argv) > 1 else ""
    if not report:
        print("Uso: python verify_project_metrics.py <arquivo_relatorio>")
        sys.exit(1)
    
    issues = verify(report)
    if issues:
        print("DIVERGENCIAS ENCONTRADAS:")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("OK: Todas as metricas verificadas")
```

## Exemplos de Erros Reais (Casos de Estudo)

### Erro 1: Inflacao de Testes
- **Errado**: Reportar "61 testes" quando eram 14
- **Correto**: Rodar `pytest --collect-only` e usar o numero real

### Erro 2: Tecnica Aplicada ao Modelo Errado
- **Errado**: Dizer que phi4-mini usa DSA/HISA/MISA
- **Correto**: Verificar o paper original e a arquitetura do modelo

### Erro 3: Schema Nao Verificado
- **Errado**: Documentar `id TEXT PRIMARY KEY` sem ler o codigo
- **Correto**: Ler o CREATE TABLE real do arquivo

### Erro 4: IP Exposto
- **Errado**: Incluir `2.25.168.233` em relatorio
- **Correto**: Usar placeholder `IP_DA_VPS`

### Erro 5: Numeros Aparentemente Precisos
- **Errado**: Reportar "15.535 linhas" sem verificar
- **Correto**: Rodar `find . -name "*.py" -exec wc -l {} +` e usar o numero real

## Checklist Pre-Entrega

Antes de entregar qualquer relatorio ou documentacao:
- [ ] Todos os numeros foram verificados com comandos?
- [ ] Todos os arquivos mencionados foram inspecionados?
- [ ] Nenhuma tecnica foi associada sem validacao?
- [ ] Nenhum IP ou dado sensivel foi incluido?
- [ ] O script de verificacao foi executado?
- [ ] Divergencias foram corrigidas?

## Penalidades

Se um relatorio for entregue com erros:
1. Corrigir imediatamente
2. Registrar o erro no wiki/_meta/erros-aprendizados.md
3. Atualizar esta skill com a nova regra preventiva
