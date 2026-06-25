# verify_voice_api.py
# Script para testar os novos endpoints de voz da Atena

import requests
import wave
import numpy as np
import os
import logging
import time

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "http://127.0.0.1:8000/api"
DUMMY_AUDIO_PATH = "dummy_audio.wav"
LEXICO_PATH = "memoria_do_usuario/lexico_fonetico.json"
SAMPLE_RATE = 44100
DURATION = 1  # seconds
FREQUENCY = 440  # Hz (A4 note)

# Simula uma transcrição que o Whisper poderia gerar com erro
# e a correção que o usuário forneceria.
RAW_TEXT_SIMULATED = "bodia atena"
CORRECTED_TEXT = "bom dia atena"

# --- 1. Gerar arquivo de áudio WAV de teste ---
def generate_dummy_wav():
    """Gera um arquivo WAV simples para usar nos testes."""
    logging.info(f"Gerando arquivo de áudio de teste: {DUMMY_AUDIO_PATH}")
    num_samples = int(SAMPLE_RATE * DURATION)
    t = np.linspace(0., DURATION, num_samples, endpoint=False)
    amplitude = np.iinfo(np.int16).max * 0.3
    data = amplitude * np.sin(2. * np.pi * FREQUENCY * t)

    try:
        with wave.open(DUMMY_AUDIO_PATH, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(data.astype(np.int16).tobytes())
        logging.info("Arquivo de áudio gerado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Falha ao gerar arquivo de áudio: {e}", exc_info=True)
        return False

# --- 2. Testar o endpoint /v1/voice/transcribe ---
def test_transcribe():
    """Envia o áudio para o endpoint de transcrição e valida a resposta."""
    logging.info("--- Testando endpoint /v1/voice/transcribe ---")
    url = f"{BASE_URL}/v1/voice/transcribe"

    if not os.path.exists(DUMMY_AUDIO_PATH):
        logging.error("Arquivo de áudio de teste não encontrado.")
        return None

    try:
        with open(DUMMY_AUDIO_PATH, 'rb') as f:
            files = {'audio_file': (DUMMY_AUDIO_PATH, f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=90) # Timeout longo para o Whisper

        logging.info(f"Status Code: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        logging.info(f"Resposta da API de transcrição: {data}")

        assert "raw_text" in data, "A chave 'raw_text' não foi encontrada na resposta."
        assert "corrected_text" in data, "A chave 'corrected_text' não foi encontrada na resposta."

        logging.info("✅ Teste de transcrição BEM-SUCEDIDO.")
        # Retornamos um texto simulado porque a transcrição real do áudio de teste pode variar.
        # Para um teste consistente do próximo passo, usamos um valor fixo.
        return RAW_TEXT_SIMULATED

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erro no teste de transcrição: {e}")
        return None
    except AssertionError as e:
        logging.error(f"❌ Falha na validação da resposta de transcrição: {e}")
        return None

# --- 3. Testar o endpoint /v1/voice/learn_correction ---
def test_learn_correction(raw_text: str):
    """Envia uma correção para o endpoint de aprendizado."""
    if not raw_text:
        logging.warning("Pulando teste de aprendizado por falta de transcrição crua.")
        return False

    logging.info("--- Testando endpoint /v1/voice/learn_correction ---")
    url = f"{BASE_URL}/v1/voice/learn_correction"
    payload = {
        "raw_text": raw_text,
        "corrected_text": CORRECTED_TEXT
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        logging.info(f"Status Code: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        logging.info(f"Resposta da API de aprendizado: {data}")

        assert data.get("status") == "success", "O status da resposta de aprendizado não foi 'success'."

        logging.info("✅ Teste de aprendizado de correção BEM-SUCEDIDO.")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erro no teste de aprendizado: {e}")
        return False
    except AssertionError as e:
        logging.error(f"❌ Falha na validação da resposta de aprendizado: {e}")
        return False

# --- 4. Verificar o arquivo de léxico ---
def verify_lexico_file():
    """Verifica se a correção foi de fato salva no arquivo JSON."""
    logging.info(f"--- Verificando o arquivo de léxico: {LEXICO_PATH} ---")
    if not os.path.exists(LEXICO_PATH):
        logging.error(f"❌ Arquivo de léxico não encontrado em '{LEXICO_PATH}'.")
        return False

    try:
        with open(LEXICO_PATH, 'r', encoding='utf-8') as f:
            lexico = json.load(f)

        normalized_raw_text = RAW_TEXT_SIMULATED.lower().strip()

        if normalized_raw_text in lexico:
            entry = lexico[normalized_raw_text]
            if entry['texto_confirmado'] == CORRECTED_TEXT:
                logging.info("✅ Verificação do léxico BEM-SUCEDIDA. A correção foi salva corretamente.")
                return True
            else:
                logging.error(f"❌ Falha na verificação do léxico. Texto esperado '{CORRECTED_TEXT}', encontrado '{entry['texto_confirmado']}'.")
                return False
        else:
            logging.error(f"❌ Falha na verificação do léxico. A chave '{normalized_raw_text}' não foi encontrada.")
            return False

    except Exception as e:
        logging.error(f"❌ Erro ao ler ou validar o arquivo de léxico: {e}", exc_info=True)
        return False

# --- Execução Principal ---
def main():
    """Orquestra a execução dos testes."""
    if not generate_dummy_wav():
        return

    # Pausa para garantir que o servidor esteja pronto
    logging.info("Aguardando 5 segundos para o servidor iniciar completamente...")
    time.sleep(5)

    raw_transcription = test_transcribe()

    if raw_transcription:
        learn_success = test_learn_correction(raw_transcription)
        if learn_success:
            # Pausa para garantir que o arquivo foi salvo no disco
            time.sleep(1)
            verify_lexico_file()

    # --- Limpeza ---
    if os.path.exists(DUMMY_AUDIO_PATH):
        os.remove(DUMMY_AUDIO_PATH)
        logging.info(f"\nArquivo de áudio de teste '{DUMMY_AUDIO_PATH}' removido.")

if __name__ == "__main__":
    logging.info(">>> INICIANDO SCRIPT DE VERIFICAÇÃO DA API DE VOZ <<<")
    logging.info("Este script assume que o servidor FastAPI está sendo iniciado em paralelo.")
    main()
    logging.info(">>> SCRIPT DE VERIFICAÇÃO CONCLUÍDO <<<")