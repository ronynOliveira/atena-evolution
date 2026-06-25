import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

# --- TENTATIVA DE CORREÇÃO PARA NotImplementedError ---
# Aplicar a política de loop ANTES de qualquer outra coisa do asyncio
if os.name == 'nt': # 'nt' é para Windows
    try:
        # Tenta definir a política de loop que geralmente funciona melhor no Windows para subprocessos
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("INFO: Política de loop de eventos do asyncio definida para WindowsSelectorEventLoopPolicy.")
    except Exception as e_policy:
        print(f"AVISO: Não foi possível definir WindowsSelectorEventLoopPolicy: {e_policy}")
        # Se falhar, pode tentar outras ou deixar o padrão (que pode ser o problema)
# --- FIM DA TENTATIVA DE CORREÇÃO ---


CHATGPT_URL = "https://chat.openai.com/"
USER_DATA_DIR = "./playwright_user_data"

async def enviar_prompt_chatgpt(prompt_usuario: str, headless_mode: bool = False) -> str | None:
    """
    Envia um prompt para o chat.openai.com usando Playwright e retorna a resposta.
    USA LOGIN MANUAL INICIALMENTE.
    """
    # Adicionado um print para indicar o início da função
    print("INFO: Função enviar_prompt_chatgpt iniciada.")
    async with async_playwright() as p:
        print("INFO: async_playwright() contexto iniciado.")
        browser_context = None 
        try:
            print("INFO: Tentando launch_persistent_context...")
            browser_context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=headless_mode,
                args=['--start-maximized', '--disable-blink-features=AutomationControlled'],
                slow_mo=100 
            )
            print("INFO: launch_persistent_context bem-sucedido.")
            page = await browser_context.new_page()
            print("INFO: Nova página criada.")
            
            await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"})
            print("INFO: User-agent definido.")

            print(f"Navegando para {CHATGPT_URL}...")
            await page.goto(CHATGPT_URL, timeout=90000, wait_until='networkidle')
            print("Página carregada ou timeout de networkidle atingido.")

            prompt_textarea_selector = "textarea#prompt-textarea"
            await asyncio.sleep(5) 
            is_logged_in = await page.is_visible(prompt_textarea_selector, timeout=15000)

            if not is_logged_in:
                print("\n--- ATENÇÃO ---")
                print("Parece que você não está logado no ChatGPT nesta sessão do navegador (ou o seletor do prompt não foi encontrado).")
                print(f"Por favor, faça login manualmente na janela do navegador que abriu ({CHATGPT_URL}).")
                print("Após fazer o login e chegar à tela principal do chat, volte aqui e pressione Enter.")
                input("Pressione Enter para continuar após o login manual...")
                
                await page.reload(wait_until='networkidle', timeout=60000)
                await asyncio.sleep(5)
                is_logged_in = await page.is_visible(prompt_textarea_selector, timeout=15000)
                if not is_logged_in:
                    print("Login ainda não detectado após reload ou seletor do prompt não encontrado. Saindo.")
                    if browser_context: await browser_context.close() # Fechar antes de retornar
                    return "ERRO: Login manual não foi detectado ou falha ao encontrar o campo de prompt."
            
            print("Login detectado ou etapa de login manual concluída. Prosseguindo...")

            print(f"Tentando preencher o prompt: '{prompt_usuario[:50]}...' no seletor '{prompt_textarea_selector}'")
            try:
                await page.fill(prompt_textarea_selector, prompt_usuario, timeout=10000)
            except PlaywrightTimeoutError:
                print(f"ERRO: Timeout ao tentar preencher o prompt. O seletor '{prompt_textarea_selector}' está correto e visível?")
                raise 
            
            send_button_selector = 'button[data-testid="send-button"]'
            print(f"Tentando encontrar o botão de enviar com o seletor: {send_button_selector}")
            if not await page.is_visible(send_button_selector, timeout=5000):
                print(f"ERRO: Botão de enviar principal ({send_button_selector}) não encontrado ou não visível.")
                possible_buttons = await page.query_selector_all(f'#{prompt_textarea_selector.split("#")[1].split(" ")[0]} ~ button')
                send_button_found_alt = False
                for button in possible_buttons:
                    if await button.is_visible():
                        svg_inside = await button.query_selector('svg')
                        if svg_inside:
                            print(f"Encontrado botão alternativo com SVG. Tentando clicar...")
                            await button.click(timeout=5000)
                            send_button_found_alt = True
                            break
                if not send_button_found_alt:
                    print("Nenhum botão de enviar alternativo promissor encontrado.")
                    raise Exception("Botão de enviar não encontrado com nenhum seletor testado.")
            else:
                await page.click(send_button_selector, timeout=5000)

            print("Prompt enviado. Aguardando resposta...")
            
            try:
                print(f"Aguardando o botão de enviar ({send_button_selector}) ficar desabilitado (IA processando)...")
                await page.wait_for_selector(f'{send_button_selector}[disabled]', state='visible', timeout=10000)
                print("Botão de enviar desabilitado, IA está gerando resposta.")
            except PlaywrightTimeoutError:
                print("Aviso: Não foi detectado que o botão de enviar ficou desabilitado. A IA pode já ter respondido muito rápido ou o fluxo mudou.")

            completion_indicator_selector_regenerate = 'button:has-text("Regenerate")'
            print(f"Aguardando conclusão da resposta (botão enviar reabilitado OU '{completion_indicator_selector_regenerate}' visível)...")
            
            await page.wait_for_function(f"""
                () => {{
                    const sendButton = document.querySelector('{send_button_selector}');
                    const regenerateButton = document.querySelector('{completion_indicator_selector_regenerate}');
                    return (sendButton && !sendButton.disabled) || (regenerateButton && getComputedStyle(regenerateButton).display !== 'none');
                }}
            """, timeout=180000)
            
            print("Conclusão da resposta detectada.")
            await asyncio.sleep(1)

            all_message_groups_selector = "div.group"
            last_response_text = "ERRO: Não foi possível extrair a resposta final."
            message_groups = await page.query_selector_all(all_message_groups_selector)
            if message_groups:
                for i in range(len(message_groups) - 1, -1, -1):
                    group = message_groups[i]
                    markdown_element = await group.query_selector("div.markdown")
                    if markdown_element:
                        last_response_text = await markdown_element.inner_text()
                        print(f"Resposta extraída do grupo {i+1} (de trás para frente).")
                        break 
            else:
                print(f"ERRO: Nenhum grupo de mensagem encontrado com o seletor '{all_message_groups_selector}'.")
            
            await asyncio.sleep(2)

        except PlaywrightTimeoutError as e:
            print(f"Timeout durante a operação com Playwright: {e}")
            error_message = f"ERRO: Timeout - {str(e)}"
            if 'page' in locals() and page and not page.is_closed(): # Verifica se page existe e não está fechada
                try:
                    current_url = page.url
                    print(f"URL atual no momento do timeout: {current_url}")
                    html_content = await page.content()
                    with open(f"timeout_page_content_{int(time.time())}.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"HTML da página no momento do timeout salvo.")
                except Exception as e_html:
                    print(f"Não foi possível obter URL/HTML no timeout: {e_html}")
            return error_message
        except Exception as e:
            print(f"Erro inesperado durante a automação com ChatGPT: {e}")
            screenshot_path = f"erro_chatgpt_{int(time.time())}.png"
            if 'page' in locals() and page and not page.is_closed():
                try:
                    await page.screenshot(path=screenshot_path)
                    print(f"Screenshot do erro salvo em: {screenshot_path}")
                except Exception as se:
                    print(f"Não foi possível salvar o screenshot: {se}")
            return f"ERRO: Inesperado - {str(e)}" # Adicionado 'Inesperado' para diferenciar
        finally:
            if browser_context:
                await browser_context.close()
                print("INFO: Contexto do navegador fechado.")
        
        return last_response_text

async def main_test():
    print("INFO: Função main_test iniciada.")
    resposta = await enviar_prompt_chatgpt("Explique o conceito de singularidade tecnológica em 3 frases.", headless_mode=False)
    
    if resposta:
        print("\n--- Resposta do ChatGPT ---")
        print(resposta)
    else:
        print("\nNenhuma resposta recebida ou erro (resposta foi None).")
    print("INFO: Função main_test concluída.")


if __name__ == "__main__":
    # A política de loop já foi tentada no topo do script.
    # A linha original 'if os.name == 'nt': asyncio.set_event_loop_policy(...)'
    # é redundante se a do topo funcionar, mas não fará mal deixá-la se a do topo falhar
    # por algum motivo (embora seja improvável). Para clareza, vamos manter apenas uma tentativa.
    print("INFO: Script rpa_chatgpt.py iniciado.")
    asyncio.run(main_test())
    print("INFO: Script rpa_chatgpt.py concluído.")