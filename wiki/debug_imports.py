import traceback
import logging

# Configura um log simples para vermos a saída
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

logging.info("--- Iniciando teste de importação do servidor Atena ---")

try:
    # Tentamos importar o módulo que está falhando
    import main as atena_servidor_unified
    logging.info("SUCESSO: O módulo 'atena_servidor_unified' foi importado sem erros.")
    logging.info("Isso sugere que o problema pode estar na configuração do Docker ou do Uvicorn.")

except Exception as e:
    logging.error("FALHA: Ocorreu um erro ao tentar importar 'atena_servidor_unified'.")
    logging.error("A causa raiz provável está detalhada no traceback abaixo.")
    print("\n--- INÍCIO DO TRACEBACK DETALHADO ---\n")
    # Esta é a linha mais importante: ela imprime o "mapa" completo do erro.
    traceback.print_exc()
    print("\n--- FIM DO TRACEBACK DETALHADO ---")