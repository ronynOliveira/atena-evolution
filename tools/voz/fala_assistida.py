#!/usr/bin/env python3
"""
Koldi's Fala Assistida — Ferramenta de Comunicação Aumentativa

Para o Senhor Robério, que tem distonia generalizada afetando a fala.
Baseado em pesquisa sobre AAC, disartria hipercinética, e predição textual.

Funcionalidades:
  1. PREDIÇÃO — Sugere palavras enquanto o senhor digita
  2. FRASES — Biblioteca de frases prontas para acesso rápido
  3. CORREÇÃO — Normaliza padrões comuns de digitação irregular
  4. TTS — Fala o texto em voz alta (integra com voz.py)

Uso:
  python scripts/fala_assistida.py                        # Menu interativo
  python scripts/fala_assistida.py --predizer "disto"     # Sugerir palavras
  python scripts/fala_assistida.py --frases               # Listar frases prontas
  python scripts/fala_assistida.py --falar "bom dia"      # Falar texto
"""

import json
import os
import sys
import subprocess

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
from pathlib import Path
from typing import List, Optional

HERMES = Path.home() / "AppData/Local/hermes"
DICT_FILE = HERMES / "lib" / "fala_dicionario.json"
FRASES_FILE = HERMES / "lib" / "fala_frases.json"
TTS_SCRIPT = HERMES / "scripts" / "voz.py"


# ─── Dicionário Base ─────────────────────────────────────────────────────

DICIONARIO_BASE = {
    "bom": ["dia", "tarde", "noite", "saber", "trabalho"],
    "boa": ["tarde", "noite", "sorte", "ideia"],
    "obrig": ["ado", "ada", "ado pela ajuda"],
    "por": ["favor", "gentileza", "enquanto"],
    "com": ["licença", "certeza", "carinho", "precisão"],
    "precis": ["o", "a", "amos", "o de ajuda"],
    "gost": ["o", "aria", "aria de", "ei de"],
    "quero": ["saber", "falar", "pedir", "ajuda", "tentar"],
    "koldi": ["?", "ajuda", "fale", "faça", "procure", "analise"],
    "senhor": ["?", ",", "Robério"],
    "desculp": ["e", "a", "o incômodo"],
    "ajuda": ["?", "-me", "rápido"],
    "nao": ["sei", "consigo", "quero", "agora"],
    "sim": [", obrigado", ", por favor"],
    "muito": ["obrigado", "bem", "tempo"],
}

# Frases de acesso rápido para momentos de dificuldade
FRASES_PRONTA = [
    # Emergência
    {"id": "emergencia_ajuda", "texto": "Preciso de ajuda, por favor.", "categoria": "🚨 Emergência"},
    {"id": "emergencia_crise", "texto": "Estou tendo uma crise. Preciso de assistência.", "categoria": "🚨 Emergência"},
    {"id": "emergencia_medico", "texto": "Preciso de atendimento médico.", "categoria": "🚨 Emergência"},
    
    # Saudações
    {"id": "saudacao_bomdia", "texto": "Bom dia!", "categoria": "👋 Saudações"},
    {"id": "saudacao_boatarde", "texto": "Boa tarde!", "categoria": "👋 Saudações"},
    {"id": "saudacao_boanoite", "texto": "Boa noite!", "categoria": "👋 Saudações"},
    {"id": "saudacao_ola", "texto": "Olá, tudo bem?", "categoria": "👋 Saudações"},
    
    # Pedidos comuns
    {"id": "pedido_repetir", "texto": "Pode repetir, por favor?", "categoria": "📝 Pedidos"},
    {"id": "pedido_esperar", "texto": "Só um momento, por favor.", "categoria": "📝 Pedidos"},
    {"id": "pedido_ajuda", "texto": "Você pode me ajudar?", "categoria": "📝 Pedidos"},
    {"id": "pedido_devagar", "texto": "Pode falar mais devagar?", "categoria": "📝 Pedidos"},
    
    # Koldi
    {"id": "koldi_pesquisar", "texto": "Koldi, pesquise sobre isso para mim.", "categoria": "🤖 Koldi"},
    {"id": "koldi_analisar", "texto": "Koldi, analise este texto.", "categoria": "🤖 Koldi"},
    {"id": "koldi_salvar", "texto": "Koldi, salve esta informação.", "categoria": "🤖 Koldi"},
    {"id": "koldi_obrigado", "texto": "Obrigado, Koldi.", "categoria": "🤖 Koldi"},
    
    # Humor/Saúde
    {"id": "saude_bem", "texto": "Estou bem hoje.", "categoria": "❤️ Saúde"},
    {"id": "saude_cansado", "texto": "Estou cansado.", "categoria": "❤️ Saúde"},
    {"id": "saude_dor", "texto": "Estou com dor.", "categoria": "❤️ Saúde"},
    {"id": "saude_medicacao", "texto": "Tomei a medicação.", "categoria": "❤️ Saúde"},
    
    # Social
    {"id": "social_obrigado", "texto": "Muito obrigado!", "categoria": "💬 Social"},
    {"id": "social_desculpe", "texto": "Desculpe pelo transtorno.", "categoria": "💬 Social"},
    {"id": "social_parabens", "texto": "Parabéns!", "categoria": "💬 Social"},
    {"id": "social_bom", "texto": "Que bom!", "categoria": "💬 Social"},
]

# Correções comuns para digitação com distonia (teclas adjacentes, tremores)
CORRECOES = {
    # Substituições comuns devido a tremor
    "oias": "olá",
    "oal": "olá",
    "bmo": "bom",
    "bm": "bom",
    "tarde": "tarde",
    "noiyte": "noite",
    "noitee": "noite",
    "obrigdao": "obrigado",
    "obrigadao": "obrigado",
    "obrigadpo": "obrigado",
    "pfvr": "por favor",
    "pfv": "por favor",
    "blz": "beleza",
    "tdb": "tudo bem",
    "vlw": "valeu",
    "brigado": "obrigado",
    "enta": "então",
    "entao": "então",
    "cmo": "como",
    "comoo": "como",
    "to": "estou",
    "tou": "estou",
    "tbm": "também",
    "tb": "também",
    "konsigo": "consigo",
    "konseguir": "conseguir",
    "vc": "você",
    "vcs": "vocês",
    "esta": "está",
    "ta": "está",
    "tá": "está",
    "tudo bem": "tudo bem",
    "dskulpa": "desculpa",
    "desculpa": "desculpe",
    "gnt": "gente",
    "pq": "porque",
    "pq?": "por quê?",
    "q": "que",
    "eh": "é",
    "éh": "é",
    "nej": "não",
    "nao": "não",
    "ñ": "não",
    "sims": "sim",
    "ss": "sim",
}


# ─── Funções ──────────────────────────────────────────────────────────

def carregar_dict() -> dict:
    """Carrega dicionário de predição."""
    if DICT_FILE.exists():
        with open(DICT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return DICIONARIO_BASE


def carregar_frases() -> list:
    """Carrega frases prontas."""
    if FRASES_FILE.exists():
        with open(FRASES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return FRASES_PRONTA


def salvar_dict(dict_data: dict):
    """Salva dicionário de predição."""
    DICT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(dict_data, f, indent=2, ensure_ascii=False)


def salvar_frases(frases: list):
    """Salva frases prontas."""
    FRASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FRASES_FILE, "w", encoding="utf-8") as f:
        json.dump(frases, f, indent=2, ensure_ascii=False)


def inicializar():
    """Inicializa arquivos de dicionário e frases."""
    if not DICT_FILE.exists():
        salvar_dict(DICIONARIO_BASE)
        print(f"✅ Dicionário criado: {DICT_FILE}")
    if not FRASES_FILE.exists():
        salvar_frases(FRASES_PRONTA)
        print(f"✅ Frases criadas: {FRASES_FILE}")


def predizer(prefixo: str) -> List[str]:
    """
    Prediz palavras baseado no prefixo digitado.
    Usa busca em Trie no dicionário + completude.
    """
    if not prefixo or len(prefixo) < 2:
        return []
    
    prefixo = prefixo.lower().strip()
    dict_data = carregar_dict()
    
    sugestoes = []
    for palavra, completacoes in dict_data.items():
        if palavra.startswith(prefixo):
            # Sugere a própria palavra se for completa
            if palavra != prefixo:
                sugestoes.append(palavra)
            # Sugere continuações
            for comp in completacoes:
                if comp.startswith(prefixo):
                    sugestoes.append(palavra + comp)
                else:
                    sugestoes.append(palavra + " " + comp)
    
    # Também busca por correspondência parcial (para digitação com erro)
    for palavra in dict_data:
        if prefixo in palavra and palavra not in sugestoes:
            sugestoes.append(palavra)
    
    # Limita e ordena
    sugestoes = list(dict.fromkeys(sugestoes))[:5]
    return sugestoes


def corrigir(texto: str) -> str:
    """
    Corrige padrões comuns de digitação irregular devido à distonia.
    Aplica correções do dicionário + heurísticas.
    """
    if not texto:
        return texto
    
    texto_original = texto
    
    # Aplicar correções do dicionário
    for erro, correcao in CORRECOES.items():
        # Substituir palavra inteira (com boundaries)
        import re
        texto = re.sub(r'\b' + re.escape(erro) + r'\b', correcao, texto, flags=re.IGNORECASE)
    
    # Heurísticas adicionais
    # 1. Letras repetidas no final (tremor na tecla)
    texto = re.sub(r'(.)\1{2,}$', r'\1\1', texto)  # "obrigadooo" → "obrigadoo"
    texto = re.sub(r'(..)\1{2,}', r'\1\1', texto)   # "tudotudo" → "tudo"
    
    # 2. Espaços duplicados (pressionar longe da barra)
    texto = re.sub(r'  +', ' ', texto)
    
    return texto


def falar(texto: str) -> bool:
    """Fala o texto usando o TTS."""
    if not texto or not texto.strip():
        return False
    
    try:
        subprocess.run(
            ["python", str(TTS_SCRIPT), texto.strip()],
            timeout=25, capture_output=True
        ,
                       creationflags=WIN_FLAGS)
        return True
    except:
        print(f"⚠ TTS falhou para: {texto[:50]}...")
        return False


def listar_frases(categoria: Optional[str] = None):
    """Lista frases prontas, opcionalmente filtradas por categoria."""
    frases = carregar_frases()
    
    if categoria:
        frases = [f for f in frases if f["categoria"] == categoria]
    
    cats = list(dict.fromkeys(f["categoria"] for f in frases))
    
    for cat in cats:
        print(f"\n{cat}")
        print("-" * 40)
        for f in frases:
            if f["categoria"] == cat:
                print(f"  [{f['id']}] {f['texto']}")


def menu_interativo():
    """Menu interativo para o terminal."""
    inicializar()
    
    while True:
        print("\n" + "=" * 50)
        print("🗣️  Koldi's Fala Assistida")
        print("=" * 50)
        print("1. ✏️  Digitar texto para falar")
        print("2. 🔮 Predizer palavra (autocomplete)")
        print("3. 📋 Frases prontas")
        print("4. 🩺 Correção de digitação")
        print("5. ⚙️  Gerenciar dicionário")
        print("0. Sair")
        
        opcao = input("\nOpção: ").strip()
        
        if opcao == "0":
            break
        elif opcao == "1":
            texto = input("Digite o texto: ")
            corrigido = corrigir(texto)
            if corrigido != texto:
                print(f"✏️ Corrigido: {corrigido}")
            sugestoes = predizer(texto.split()[-1] if texto.split() else "")
            if sugestoes:
                print(f"💡 Sugestões: {', '.join(sugestoes)}")
            if falar(corrigido or texto):
                print("✅ Falado!")
        elif opcao == "2":
            prefixo = input("Digite o início da palavra: ")
            sugestoes = predizer(prefixo)
            if sugestoes:
                print(f"💡 Sugestões: {', '.join(sugestoes)}")
            else:
                print("Nenhuma sugestão encontrada.")
        elif opcao == "3":
            listar_frases()
            escolha = input("\nDigite o ID da frase (ou Enter para voltar): ").strip()
            if escolha:
                frases = carregar_frases()
                for f in frases:
                    if f["id"] == escolha:
                        if falar(f["texto"]):
                            print(f"✅ Falado: {f['texto']}")
                        break
        elif opcao == "4":
            texto = input("Digite o texto com erro: ")
            corrigido = corrigir(texto)
            print(f"✏️ Original: {texto}")
            print(f"✅ Corrigido: {corrigido}")
        elif opcao == "5":
            print("\nDigite novas palavras no formato: palavra,completação1,completação2")
            print("Exemplo: estud,andando,ar,o")
            entrada = input("> ").strip()
            if entrada and "," in entrada:
                partes = [p.strip() for p in entrada.split(",")]
                palavra = partes[0]
                completacoes = partes[1:]
                dict_data = carregar_dict()
                dict_data[palavra] = completacoes
                salvar_dict(dict_data)
                print(f"✅ '{palavra}' adicionado ao dicionário!")
        else:
            print("Opção inválida.")


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    inicializar()
    
    if len(sys.argv) < 2:
        menu_interativo()
        return
    
    cmd = sys.argv[1]
    
    if cmd in ("-h", "--help", "help"):
        print(__doc__)
    
    elif cmd in ("--predizer", "-p"):
        if len(sys.argv) > 2:
            sugestoes = predizer(sys.argv[2])
            if sugestoes:
                print("\n".join(sugestoes))
            else:
                print("(sem sugestões)")
    
    elif cmd in ("--frases", "-f"):
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        listar_frases(cat)
    
    elif cmd in ("--falar", "-t"):
        texto = " ".join(sys.argv[2:])
        if not texto:
            texto = sys.stdin.read().strip()
        if texto:
            corrigido = corrigir(texto)
            if corrigido != texto:
                print(f"✏️ Corrigido: {corrigido}", file=sys.stderr)
            falar(corrigido or texto)
    
    elif cmd in ("--corrigir", "-c"):
        texto = " ".join(sys.argv[2:])
        if texto:
            print(corrigir(texto))
    
    else:
        print(f"Comando desconhecido: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()