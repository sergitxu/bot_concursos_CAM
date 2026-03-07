import os
import sys
import requests

def test_connection():
    token = os.getenv('TELEGRAM_TOKEN', 'TU_TOKEN_TELEGRAM')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', 'TU_CHAT_ID')
    
    if token == 'TU_TOKEN_TELEGRAM' or chat_id == 'TU_CHAT_ID':
        print("❌ Error: No se han configurado TELEGRAM_TOKEN o TELEGRAM_CHAT_ID.")
        print("Por favor, ejecuta el script pasando las variables de entorno, por ejemplo:")
        print("TELEGRAM_TOKEN='tu_token' TELEGRAM_CHAT_ID='tu_chat_id' python3 test_telegram.py")
        sys.exit(1)
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': "🤖 <b>Mensaje de prueba</b>\n¡La conexión con el bot de Telegram funciona correctamente!",
        'parse_mode': 'HTML'
    }
    
    print("Enviando mensaje de prueba a Telegram...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ ¡Mensaje enviado con éxito!")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error HTTP al enviar el mensaje: {e}")
        try:
            print(f"Detalle: {response.json()}")
        except:
            print(f"Detalle: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    test_connection()
