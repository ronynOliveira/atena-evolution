
import uvicorn
import sys
import os
import logging

# Configuração de logging para o lançador
logger = logging.getLogger("AtenaLauncher")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s')

# Adiciona o diretório 'backend' ao path do Python
# para que o módulo 'app' possa ser encontrado.
# __file__ é o caminho para run_server.py
# os.path.dirname(__file__) é o diretório 'backend'
# Isso garante que 'from app...' funcione corretamente.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    logger.info("Iniciando servidor da Atena através do lançador 'run_server.py'...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
