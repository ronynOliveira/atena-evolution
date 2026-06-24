import subprocess

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
import sys
import os
import socket

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    print("⚕ Iniciando Servidor Koldi para Acesso Android...")
    
    local_ip = get_ip()
    port = 9119
    
    print(f"→ Endereço Local: http://{local_ip}:{port}")
    print(f"→ Se o Tailscale estiver ativo, use o IP do Tailscale.")
    print(f"→ No Android, abra este endereço e selecione 'Adicionar à tela de início'.")
    
    # Start the hermes dashboard (web UI)
    # --insecure is required to bind to non-localhost
    cmd = ["hermes", "web", "--host", "0.0.0.0", "--port", str(port), "--insecure"]
    
    try:
        subprocess.run(cmd, check=True,
                       creationflags=WIN_FLAGS)
    except KeyboardInterrupt:
        print("\n✓ Servidor Koldi parado.")
    except Exception as e:
        print(f"✗ Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main()
