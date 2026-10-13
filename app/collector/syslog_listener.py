import socket
import sqlite3
import os
from datetime import datetime

# Rutas absolutas robustas para ubicar la base de datos en la raíz del proyecto (data/noc_syslog.db)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))       # Carpeta collector/
APP_DIR = os.path.dirname(BASE_DIR)                         # Carpeta app/
PROJECT_ROOT = os.path.dirname(APP_DIR)                     # Carpeta raíz del proyecto
DB_PATH = os.path.join(PROJECT_ROOT, "data", "noc_syslog.db")

# Configuración del servidor UDP
HOST = "0.0.0.0"  # Escucha en todas las interfaces de red locales
PORT = 5140       # Puerto seguro no privilegiado

def save_event_to_db(device_ip, raw_message):
    """Parsea el mensaje syslog entrante y lo guarda de forma segura en la BD."""
    facility = 1
    severity = 5
    manufacturer = "Cisco/Genérico"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = raw_message

    # Normalización básica de la cabecera PRI si la trae el paquete (<PRI>)
    if raw_message.startswith("<") and ">" in raw_message:
        try:
            end_idx = raw_message.index(">")
            pri = int(raw_message[1:end_idx])
            facility = pri >> 3
            severity = pri & 7
            message = raw_message[end_idx+1:].strip()
        except ValueError:
            pass

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO syslog_events (device_ip, manufacturer, timestamp, facility, severity, message, is_synthetic)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (device_ip, manufacturer, timestamp, facility, severity, message))
        conn.commit()
        conn.close()
        print(f"📥 [Syslog Real Capturado] IP: {device_ip} | Sev: {severity} | Msg: {message[:50]}...")
    except Exception as e:
        print(f"❌ Error al guardar en la base de datos: {e}")

def start_syslog_listener():
    """Inicia el socket UDP para la captura de logs en tiempo real."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    
    print("==================================================")
    print(f"🚀 Colector UDP Syslog activo y escuchando en el puerto {PORT}")
    print(f"📂 Base de datos destino: {DB_PATH}")
    print("==================================================")
    
    try:
        while True:
            data, addr = sock.recvfrom(2048)
            device_ip = addr[0]
            raw_message = data.decode("utf-8", errors="ignore").strip()
            save_event_to_db(device_ip, raw_message)
    except KeyboardInterrupt:
        print("\n🛑 Colector UDP detenido por el usuario.")
    finally:
        sock.close()

if __name__ == "__main__":
    start_syslog_listener()