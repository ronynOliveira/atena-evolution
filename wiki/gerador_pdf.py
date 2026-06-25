
import os
import glob
from fpdf import FPDF
import traceback

# --- Configuracoes ---
# O script deve ser executado a partir da raiz do projeto 'Atena_Consolidada'
ROOT_DIR = '.' 
OUTPUT_FILENAME = 'documentacao_atena.pdf'

# Lista de diretorios a serem completamente ignorados
EXCLUDED_DIRS = [
    'node_modules', 
    '.git', 
    '__pycache__', 
    'target', 
    'dist', 
    'data', # Contem DB, cache, etc.
    'models' # Contem modelos binarios
]

# Lista de extensoes de arquivo a serem ignoradas
EXCLUDED_EXTENSIONS = [
    '.zip', '.png', '.jpg', '.jpeg', '.gif', '.wav', '.mp3', '.ico', '.onnx', 
    '.db', '.pdf', '.docx', '.pickle', '.lockb', '.dll', '.lib', '.pdb', 
    '.exe', '.msi', '.wixobj', '.wixpdb', '.rlib', '.rmeta', '.d', '.exp', 
    '.a', '.msi', '.svg', '.ttf', '.woff', '.woff2', '.eot'
]

class PDF(FPDF):
    """ Classe customizada para o PDF, com cabecalho e rodape. """
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Documentacao do Projeto Atena', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 14)
        # Trata o titulo para evitar problemas de codificacao
        title_encoded = title.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 10, title_encoded, 0, 'L')
        self.ln(5)

    def chapter_body(self, content):
        self.set_font('Courier', '', 8)
        # Trata o conteudo para evitar problemas de codificacao no FPDF
        content_encoded = content.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 4, content_encoded)
        self.ln()

def is_path_excluded(path, root_dir):
    """ Verifica se um caminho deve ser excluido. """
    try:
        rel_path = os.path.relpath(path, root_dir)
        parts = rel_path.split(os.sep)
        
        if any(part in EXCLUDED_DIRS for part in parts):
            return True
            
        if any(path.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
            return True
    except ValueError:
        # Pode acontecer se o path estiver em um drive diferente no Windows
        return True # Exclui por seguranca
        
    return False

def main():
    """ Funcao principal para gerar o PDF. """
    print("Iniciando a geracao do PDF de documentacao...")
    
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    files_to_process = []
    for root, _, files in os.walk(ROOT_DIR):
        # Pula diretorios excluidos
        if any(excluded_dir in root.split(os.sep) for excluded_dir in EXCLUDED_DIRS):
            continue
            
        for name in files:
            filepath = os.path.join(root, name)
            if not is_path_excluded(filepath, ROOT_DIR):
                files_to_process.append(filepath)

    print(f"Encontrados {len(files_to_process)} arquivos para documentar.")

    for filepath in sorted(files_to_process):
        print(f"Processando: {filepath}")
        
        pdf.add_page()
        pdf.chapter_title(f'ARQUIVO: {filepath}')
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f_in:
                content = f_in.read()
                pdf.chapter_body(content)
        except Exception as e:
            error_message = f"Erro ao ler o arquivo: {filepath}\n{traceback.format_exc()}"
            print(error_message)
            pdf.chapter_body(error_message)

    print(f"Salvando PDF em '{OUTPUT_FILENAME}'...")
    try:
        pdf.output(OUTPUT_FILENAME)
        print(f"PDF '{OUTPUT_FILENAME}' gerado com sucesso!")
    except Exception as e:
        print(f"Falha ao salvar o PDF: {e}")
        print(traceback.format_exc())

if __name__ == '__main__':
    main()
