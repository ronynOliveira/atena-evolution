from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

# URL do novo site alvo
CHAT_URL = "https://chatgpt.com.br/" 
# Podemos manter um diretório de dados do usuário, mesmo que não haja login,
# pois pode armazenar preferências do site ou estados de consentimento de cookies.
USER_DATA_DIR = "./playwright_user_data_com_br" 

def enviar_prompt_chat_com_br_sync(prompt_usuario: str, headless_mode: bool = True) -> str | None: # Default para headless True agora
    """
    Envia um prompt para chatgpt.com.br usando Playwright SÍNCRONO e retorna a resposta.
    Assumindo que não requer login para uso básico.
    """
    print(f"INFO_SYNC: Iniciando enviar_prompt_chat_com_br_sync para '{CHAT_URL}'")
    with sync_playwright() as p:
        print("INFO_SYNC: sync_playwright() contexto iniciado.")
        browser_context = None
        try:
            print("INFO_SYNC: Tentando launch_persistent_context (síncrono)...")
            browser_context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=headless_mode,
                args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
                slow_mo=150 # Aumentado um pouco para melhor observação e para ser mais gentil com o site
            )
            print("INFO_SYNC: launch_persistent_context bem-sucedido.")
            page = browser_context.new_page()
            print("INFO_SYNC: Nova página criada.")
            
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"}) # User agent genérico
            print("INFO_SYNC: User-agent definido.")

            print(f"Navegando para {CHAT_URL}...")
            page.goto(CHAT_URL, timeout=90000, wait_until='domcontentloaded') # 'domcontentloaded' pode ser mais rápido se networkidle demorar
            print("Página carregada (domcontentloaded). Dando um tempo para scripts...")
            time.sleep(5) # Espera explícita para scripts da página carregarem

            # --- Identificar Seletores para chatgpt.com.br ---
            # Estes são PALPITES baseados na sua imagem e precisarão de AJUSTE!
            # Inspecione (F12) em chatgpt.com.br para encontrar os corretos.

            # Seletor para a caixa de texto onde se digita o prompt
            # Na sua imagem, parece ser um <textarea> com placeholder "Escreva uma mensagem"
            prompt_textarea_selector = 'textarea[placeholder="Escreva uma mensagem"]' 
            # Alternativa, se houver um ID ou um nome: 'textarea#meuIdDoPrompt' ou 'textarea[name="nomeDoPrompt"]'

            # Seletor para o botão de enviar o prompt
            # Pode ser um botão próximo à textarea, talvez com um ícone.
            send_button_selector = f'{prompt_textarea_selector} ~ button' # Palpite: botão irmão da textarea
            # Ou inspecione para um ID, classe ou data-testid específico. Ex: 'button#btnEnviar'

            # Seletor para o contêiner da ÚLTIMA resposta da IA
            # Isso é o mais difícil. Pode ser o último div com uma classe específica.
            # Ex: 'div.message.assistant:last-child' ou algo similar.
            # Pela sua imagem, as respostas aparecem em balões. Precisamos de um seletor que pegue o texto do último balão da IA.
            assistant_message_container_selector = "div.message-bubble.assistant" # PALPITE - se as respostas da IA tiverem essa classe
                                                                               # e quisermos a última:
                                                                               # 'div.message-bubble.assistant:last-of-type'
                                                                               # ou pegar todas e selecionar a última via código.

            print(f"Verificando se o campo de prompt ('{prompt_textarea_selector}') está visível...")
            if not page.is_visible(prompt_textarea_selector, timeout=20000): # Timeout maior
                print(f"ERRO_SYNC: Campo de prompt ('{prompt_textarea_selector}') não encontrado ou não visível.")
                raise Exception("Campo de prompt não encontrado.")
            
            print("Campo de prompt encontrado. Prosseguindo...")

            # 1. Inserir o prompt
            print(f"Tentando preencher o prompt: '{prompt_usuario[:50]}...'")
            page.fill(prompt_textarea_selector, prompt_usuario, timeout=10000)
            
            # 2. Clicar no botão de enviar
            print(f"Tentando encontrar e clicar no botão de enviar ('{send_button_selector}')...")
            if not page.is_visible(send_button_selector, timeout=5000):
                print(f"ERRO_SYNC: Botão de enviar ('{send_button_selector}') não encontrado ou não visível.")
                # Se tiver um botão de enviar mais óbvio (ex: com um ícone de avião de papel dentro)
                # send_button_selector_alt = 'button:has(svg[data-icon="paper-plane"])' # Exemplo
                # if page.is_visible(send_button_selector_alt, timeout=2000):
                #     print("Usando seletor alternativo para botão de enviar.")
                #     page.click(send_button_selector_alt, timeout=5000)
                # else:
                raise Exception("Botão de enviar não encontrado.")
            else:
                page.click(send_button_selector, timeout=5000)

            print("Prompt enviado. Aguardando resposta...")

            # 3. Esperar pela resposta e detectar quando ela terminou
            # Estratégia: Observar se um novo balão de mensagem do assistente aparece.
            # Ou se o campo de prompt é limpo/reabilitado, ou se um indicador de "digitando" desaparece.
            # Esta parte é MUITO dependente da interface do site.
            
            # Contar quantos balões de resposta do assistente existem ANTES de esperar um novo.
            initial_assistant_messages_count = len(page.query_selector_all(assistant_message_container_selector))
            
            print(f"Aguardando nova resposta do assistente (contagem inicial de mensagens: {initial_assistant_messages_count})...")
            
            # Espera até que o número de mensagens do assistente aumente OU um timeout.
            # Timeout longo, pois a IA pode demorar para responder.
            timeout_espera_resposta_ms = 180000 # 3 minutos
            start_time = time.time()
            nova_resposta_detectada = False
            while time.time() - start_time < (timeout_espera_resposta_ms / 1000):
                current_assistant_messages = page.query_selector_all(assistant_message_container_selector)
                if len(current_assistant_messages) > initial_assistant_messages_count:
                    print(f"Nova mensagem do assistente detectada (total agora: {len(current_assistant_messages)}).")
                    nova_resposta_detectada = True
                    break
                time.sleep(0.5) # Verifica a cada meio segundo
            
            if not nova_resposta_detectada:
                print("Timeout esperando por uma nova resposta do assistente.")
                # Mesmo com timeout, tenta extrair se algo mudou ou se há uma última mensagem
            
            time.sleep(1) # Pequena pausa para garantir que o DOM está totalmente atualizado

            # 4. Extrair a última resposta da IA
            last_response_text = "ERRO_SYNC: Não foi possível extrair a resposta final."
            all_assistant_messages = page.query_selector_all(assistant_message_container_selector)
            
            if all_assistant_messages:
                last_message_element = all_assistant_messages[-1] # Pega o último
                # O texto pode estar diretamente no elemento ou em um filho.
                # Tenta inner_text(), mas pode precisar de um seletor mais específico para o texto dentro do balão.
                last_response_text = last_message_element.inner_text() 
                print(f"Resposta extraída: '{last_response_text[:100]}...'")
            else:
                if initial_assistant_messages_count > 0: # Se havia mensagens antes mas não conseguiu pegar a nova
                     print(f"ERRO_SYNC: Não encontrou novas mensagens do assistente, mas havia {initial_assistant_messages_count} antes.")
                else: # Se nunca houve mensagens do assistente
                    print(f"ERRO_SYNC: Nenhum bloco de mensagem do assistente encontrado com o seletor '{assistant_message_container_selector}'.")
            
            time.sleep(1)

        except PlaywrightTimeoutError as e:
            print(f"Timeout durante a operação com Playwright (SYNC) em {CHAT_URL}: {e}")
            error_message = f"ERRO_SYNC: Timeout - {str(e)}"
            # ... (lógica de salvar HTML/screenshot como antes) ...
            if 'page' in locals() and page and not page.is_closed():
                try:
                    html_content = page.content()
                    with open(f"timeout_sync_page_content_com_br_{int(time.time())}.html", "w", encoding="utf-8") as f: f.write(html_content)
                    print(f"HTML da página no momento do timeout salvo.")
                except Exception as e_html: print(f"Não foi possível obter URL/HTML no timeout: {e_html}")
            return error_message
        except Exception as e:
            print(f"Erro inesperado durante a automação com {CHAT_URL} (SYNC): {e}")
            # ... (lógica de salvar screenshot como antes) ...
            if 'page' in locals() and page and not page.is_closed():
                try:
                    page.screenshot(path=f"erro_sync_chat_com_br_{int(time.time())}.png")
                    print(f"Screenshot do erro salvo.")
                except Exception as se: print(f"Não foi possível salvar o screenshot: {se}")
            return f"ERRO_SYNC: Inesperado - {str(e)}"
        finally:
            if browser_context:
                browser_context.close()
                print("INFO_SYNC: Contexto do navegador fechado.")
        
        return last_response_text

def main_test_sync_com_br():
    print("INFO_SYNC: Função main_test_sync_com_br iniciada.")
    # Mude headless_mode para False para ver o navegador durante os testes iniciais e identificação de seletores
    # Mude para True depois que estiver funcionando, para rodar em segundo plano.
    resposta = enviar_prompt_chat_com_br_sync("Qual o seu nome e suas capacidades?", headless_mode=False) 
    
    if resposta:
        print("\n--- Resposta do ChatGPT (chatgpt.com.br - SYNC) ---")
        print(resposta)
    else:
        print("\nNenhuma resposta recebida ou erro (resposta foi None) (SYNC).")
    print("INFO_SYNC: Função main_test_sync_com_br concluída.")

if __name__ == "__main__":
    main_test_sync_com_br()
    print("INFO_SYNC: Script rpa_chatgpt_com_br_sync.py concluído.")