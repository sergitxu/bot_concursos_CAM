import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata
import hashlib

# ==========================================
# CONFIGURACIÓN
# ==========================================
# Configura estas variables directamente o a través de variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'TU_TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'TU_CHAT_ID')

# Configuración de reintentos por defecto
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 5))     # 5 intentos por defecto
RETRY_DELAY = int(os.getenv('RETRY_DELAY', 1800))  # 1800 segundos = 30 minutos

# Archivo persistente para llevar el control de los avisos enviados
VISTOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vistos.txt')

def get_bocm_url():
    """Genera la URL del BOCM correspondiente al día actual."""
    today = datetime.now()
    return today.strftime('https://www.bocm.es/boletin-completo/%Y/%m/%d')

def load_vistos():
    """Carga los identificadores de los avisos ya procesados y enviados."""
    if not os.path.exists(VISTOS_FILE):
        return set()
    with open(VISTOS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f.readlines())

def save_visto(item_id):
    """Guarda un identificador en el historial (vistos.txt)."""
    with open(VISTOS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{item_id}\n")

def normalize_text(text):
    """Elimina tildes y convierte el texto a mayúsculas para las comparaciones."""
    text = text.upper()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def is_target_disposition(title):
    """Aplica las reglas de negocio, devolviendo True si pasa todos los filtros."""
    title_norm = normalize_text(title)
    
    # Si no tiene al menos una de estas 3, lo descartamos
    target_roles = ['A2', 'GESTION', 'COMUNICACION']
    if not any(role in title_norm for role in target_roles):
        return False
        
    inclusives = ['CONVOCATORIA', 'BASES', 'PLAZAS', 'PROCESO SELECTIVO']
    if not any(keyword in title_norm for keyword in inclusives):
        return False
        
    exclusions = ['LISTA DE ADMITIDOS', 'TRIBUNAL', 'APROBADOS']
    if any(exclusion in title_norm for exclusion in exclusions):
        return False
        
    return True

def send_telegram_alert(title, item_link, bulletin_url):
    """Envía un mensaje de alerta a través de la API de Telegram."""
    if TELEGRAM_TOKEN == 'TU_TOKEN_TELEGRAM' or TELEGRAM_CHAT_ID == 'TU_CHAT_ID':
        print("⚠️ Telegram Token o Chat ID no configurados. Omite el envío real.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    message = (
        f"🚨 <b>¡Nueva Oposición BOCM!</b> 🚨\n\n"
        f"📌 <b>Disposición:</b> {title}\n"
        f"🔗 <b>Enlace disposición:</b> <a href='{item_link}'>Ver Disposición</a>\n\n"
        f"📅 <b>Boletín del día:</b> <a href='{bulletin_url}'>BOCM Completo de hoy</a>"
    )
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'link_preview_options': {'is_disabled': False}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Alerta enviada correctamente por Telegram.")
    except Exception as e:
        print(f"❌ Error al enviar mensaje por Telegram: {e}")

def send_telegram_status(message_text):
    """Envía un mensaje informativo (sin formato de oposición) a Telegram."""
    if TELEGRAM_TOKEN == 'TU_TOKEN_TELEGRAM' or TELEGRAM_CHAT_ID == 'TU_CHAT_ID':
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'HTML',
        'link_preview_options': {'is_disabled': True}
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Error al enviar estado por Telegram: {e}")

def scrape_bocm():
    """Función principal que lee el BOCM y busca oposiciones."""
    bulletin_url = get_bocm_url()
    print(f"🔎 Analizando publicación BOCM del día:\n {bulletin_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = None
    # Bucle de reintentos
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"⏳ Intento {attempt} de {MAX_RETRIES}...")
            # Peticion HTTP
            res = requests.get(bulletin_url, headers=headers, timeout=15)
            
            # Si es 404, el boletín no se ha publicado
            if res.status_code == 404:
                print("⚠️ El boletín del día de hoy aún no ha sido publicado (Error 404).")
                if attempt < MAX_RETRIES:
                    print(f"💤 Esperando {RETRY_DELAY // 60} minutos para el siguiente intento...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print("⛔ Se agotaron los reintentos por hoy. Saliendo.")
                    send_telegram_status(f"⚠️ <b>Aviso:</b> Tras {MAX_RETRIES} intentos, el BOCM de hoy no parece estar publicado aún. Finalizando ejecución por hoy.")
                    return
            
            # Lanzar error general de HTTP si lo hay y no es 200/404
            res.raise_for_status()
            
            # Si llega aquí, es 200 OK
            response = res
            print("✅ Boletín cargado correctamente.")
            break
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error HTTP al acceder al BOCM: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"❌ Error de conexión al acceder al BOCM: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    if not response or response.status_code != 200:
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    dispositions = soup.find_all('li')
    
    vistos = load_vistos()
    nuevos_encontrados = 0
    
    for item in dispositions:
        title = item.get_text(strip=True)
        if not title:
            continue
            
        if is_target_disposition(title):
            link_tag = item.find('a') if item.name != 'a' else item
            item_link = bulletin_url
            
            if link_tag and link_tag.has_attr('href'):
                href = link_tag['href']
                if href.startswith('/'):
                    item_link = f"https://www.bocm.es{href}"
                elif href.startswith('http'):
                    item_link = href
                    
            item_id = hashlib.md5((item_link + title).encode('utf-8')).hexdigest()
            
            if item_id not in vistos:
                print(f"\n🎯 ¡Coincidencia encontrada!\n📑 Título: {title}")
                send_telegram_alert(title, item_link, bulletin_url)
                
                # Guardamos como visto
                save_visto(item_id)
                vistos.add(item_id)
                nuevos_encontrados += 1

    if nuevos_encontrados == 0:
        print("\nℹ️ No se encontraron nuevas disposiciones para el perfil 'A2 Gestión'.")
        send_telegram_status(f"ℹ️ <b>BOCM revisado ({datetime.now().strftime('%d/%m/%Y')}):</b> No hay oposiciones para A2 Gestión hoy (o ya te avisé antes).")

if __name__ == '__main__':
    print(f"🚀 Iniciando monitorización del BOCM (Máx. reintentos: {MAX_RETRIES}, Espera: {RETRY_DELAY // 60} min)")
    scrape_bocm()
