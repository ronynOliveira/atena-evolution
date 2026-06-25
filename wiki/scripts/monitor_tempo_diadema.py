#!/usr/bin/env python3
"""
Monitor de Previsão do Tempo para Diadema/SP.
Verifica a cada 12h se a temperatura vai cair e alerta o Senhor Robério.
VERSÃO REFLEXÃO - Integrada com Reflexion Engine para aprendizado contínuo.

Uso: python monitor_tempo_diadema.py
"""

import urllib.request
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════
# RELEXION ENGINE INTEGRATION
# ═══════════════════════════════════════════
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from scripts.reflexion_tools import DistoniaAwareMonitor
    HAS_REFLEXION = True
except ImportError:
    HAS_REFLEXION = False

# ═══════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════

CIDADE = "Diadema"
ESTADO = "SP"
PAIS = "BR"
LATITUDE = -23.6861
LONGITUDE = -46.6167

# Limiar de temperatura para alerta (°C)
TEMP_LIMITE = 15.0

# Arquivo de log
LOG_DIR = Path.home() / "AppData" / "Local" / "hermes" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "monitor-tempo.log"


# ═══════════════════════════════════════════
# API DE PREVISÃO DO TEMPO (Open-Meteo - gratuita)
# ═══════════════════════════════════════════

def obter_previsao():
    """Obtém previsão do tempo da API Open-Meteo (gratuita, sem API key)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
        f"&current_weather=true"
        f"&timezone=America/Sao_Paulo"
        f"&forecast_days=3"
    )
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OWL-Agent/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        return data
    except Exception as e:
        log_error(f"Erro ao obter previsão: {e}")
        return None


def obter_previsao_alternativa():
    """Fallback: usa wttr.in (gratuito, sem API key)."""
    url = f"https://wttr.in/{CIDADE}+{ESTADO}+{PAIS}?format=j1"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OWL-Agent/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        return data
    except Exception as e:
        log_error(f"Erro ao obter previsão alternativa: {e}")
        return None


# ═══════════════════════════════════════════
# ANÁLISE E ALERTA
# ═══════════════════════════════════════════

def analisar_previsao(data):
    """Analisa a previsão e retorna alerta se temperatura cair."""
    if not data:
        return None
    
    alertas = []
    
    try:
        # Formato Open-Meteo
        if 'daily' in data:
            daily = data['daily']
            datas = daily.get('time', [])
            temps_min = daily.get('temperature_2m_min', [])
            temps_max = daily.get('temperature_2m_max', [])
            weathercodes = daily.get('weathercode', [])
            
            for i, data_str in enumerate(datas):
                temp_min = temps_min[i] if i < len(temps_min) else None
                temp_max = temps_max[i] if i < len(temps_max) else None
                code = weathercodes[i] if i < len(weathercodes) else 0
                
                if temp_min is not None and temp_min <= TEMP_LIMITE:
                    descricao = descricao_clima(code)
                    alertas.append({
                        'data': data_str,
                        'temp_min': temp_min,
                        'temp_max': temp_max,
                        'descricao': descricao,
                        'codigo': code
                    })
        
        # Formato wttr.in (fallback)
        elif 'current_condition' in data:
            current = data['current_condition'][0]
            temp_atual = float(current.get('temp_C', 0))
            
            if temp_atual <= TEMP_LIMITE:
                alertas.append({
                    'data': 'hoje',
                    'temp_min': temp_atual,
                    'temp_max': temp_atual,
                    'descricao': current.get('weatherDesc', [{}])[0].get('value', ''),
                    'codigo': 0
                })
            
            # Verificar próximos dias
            for day in data.get('weather', []):
                date = day.get('date', '')
                mintemp = float(day.get('mintempC', 0))
                maxtemp = float(day.get('maxtempC', 0))
                
                if mintemp <= TEMP_LIMITE:
                    desc = day.get('hourly', [{}])
                    descricao = desc[0].get('weatherDesc', [{}])[0].get('value', '') if desc else ''
                    alertas.append({
                        'data': date,
                        'temp_min': mintemp,
                        'temp_max': maxtemp,
                        'descricao': descricao,
                        'codigo': 0
                    })
    
    except Exception as e:
        log_error(f"Erro ao analisar previsão: {e}")
    
    return alertas


def descricao_clima(code):
    """Converte código de clima em descrição."""
    codigos = {
        0: "Céu limpo",
        1: "Principalmente limpo",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Nevoeiro",
        48: "Nevoeiro com geada",
        51: "Chuva leve",
        53: "Chuva moderada",
        55: "Chuva forte",
        61: "Chuva leve",
        63: "Chuva moderada",
        65: "Chuva forte",
        71: "Neve leve",
        73: "Neve moderada",
        75: "Neve forte",
        80: "Chuvas leves",
        81: "Chuvas moderadas",
        82: "Chuvas fortes",
        95: "Tempestade",
        96: "Tempestada com granizo",
        99: "Tempestade forte com granizo",
    }
    return codigos.get(code, f"Código {code}")


# ═══════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════

def log_info(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{ts}] INFO: {msg}"
    print(linha)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except:
        pass


def log_error(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{ts}] ERRO: {msg}"
    print(linha, file=sys.stderr)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except:
        pass


# ═══════════════════════════════════════════
# ALERTA
# ═══════════════════════════════════════════

def gerar_alerta(alertas):
    """Gera mensagem de alerta formatada."""
    if not alertas:
        return None
    
    msg = f"🌡️ ALERTA DE TEMPERATURA - {CIDADE}/{ESTADO}\n"
    msg += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    msg += f"Limite: {TEMP_LIMITE}°C\n\n"
    
    for a in alertas:
        msg += f"📅 {a['data']}: {a['temp_min']}°C a {a['temp_max']}°C"
        if a['descricao']:
            msg += f" ({a['descricao']})"
        msg += "\n"
    
    msg += f"\n⚠️ A temperatura pode piorar os sintomas da distonia."
    msg += f"\nRecomenda-se: agasalhar-se, evitar exposição ao frio, manter-se aquecido."
    
    return msg


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

def main():
    log_info(f"Monitor de tempo: verificando previsão para {CIDADE}/{ESTADO}")
    
    # Tentar Open-Meteo primeiro
    data = obter_previsao()
    
    # Fallback para wttr.in
    if not data:
        log_info("Open-Meteo falhou, tentando wttr.in...")
        data = obter_previsao_alternativa()
    
    if not data:
        log_error("Não foi possível obter previsão do tempo")
        return 1
    
    # Analisar previsão
    alertas = analisar_previsao(data)
    
    # Aplicar reflexão se disponível
    if HAS_REFLEXION and alertas:
        temp_min = alertas[0]['temp_min'] if alertas else 0
        monitor = DistoniaAwareMonitor("monitor_temperatura")
        reflection_result = monitor.check_temperature(temp_min)
        log_info(f"Reflexão: confiança={reflection_result['confianca']:.2f}")
    
    if alertas:
        msg = gerar_alerta(alertas)
        log_info(f"ALERTA: {len(alertas)} dia(s) com temperatura <= {TEMP_LIMITE}°C")
        print("\n" + msg)
        return 0  # Retorna 0 para indicar que há alerta
    else:
        log_info(f"Sem alertas. Temperatura acima de {TEMP_LIMITE}°C nos próximos dias.")
        print(f"✅ Sem alertas para {CIDADE}/{ESTADO}. Temperatura acima de {TEMP_LIMITE}°C.")
        return 2  # Retorna 2 para indicar sem alerta


if __name__ == "__main__":
    sys.exit(main())
