import requests
import datetime

def get_weather(city="Diadema"):
    try:
        # Use wttr.in for a simple, keyless check
        response = requests.get(f"https://wttr.in/{city}?format=%t|%C|%h")
        if response.status_code == 200:
            temp, condition, humidity = response.text.split('|')
            return {
                "temp": temp,
                "condition": condition,
                "humidity": humidity
            }
    except Exception as e:
        return None

def main():
    print("⚕ Checking local environment for Senhor Robério...")
    
    weather = get_weather()
    now = datetime.datetime.now()
    
    context = []
    
    if weather:
        context.append(f"Current weather in Diadema: {weather['temp']}, {weather['condition']}.")
        # Threshold from propostas_habilidades.md: > 30°C or > 32°C
        temp_val = int(''.join(filter(str.isdigit, weather['temp'])))
        if temp_val > 30:
            context.append("⚠ HIGH TEMPERATURE DETECTED. Consider closing curtains to reduce light and heat.")
    
    # Time-based light sensitivity context
    hour = now.hour
    if 10 <= hour <= 16:
        context.append("It is mid-day. Ambient light is likely high. Consider increasing blue light filters.")
    elif hour >= 20 or hour <= 6:
        context.append("It is night time. Screen brightness should be minimized to prevent eye strain.")
        
    if context:
        print("\n".join(context))
    else:
        print("Environment data unavailable, but stay mindful of your sensitivity to light.")

if __name__ == "__main__":
    main()
