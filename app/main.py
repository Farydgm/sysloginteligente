from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
import re
import time
import socket
import threading
from datetime import datetime

from multivendor.templates_engine import MULTIVENDOR_CONFIGS, execute_safe_command

# Importar gestor SSH interactivo actualizado
try:
    from app.ssh_manager import handle_ssh_action
except ModuleNotFoundError:
    from ssh_manager import handle_ssh_action

app = Flask(__name__, template_folder='web/templates')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "noc_syslog.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_and_load_sample_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS syslog_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_ip TEXT NOT NULL,
            manufacturer TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            facility INTEGER NOT NULL,
            severity INTEGER NOT NULL,
            message TEXT NOT NULL,
            component TEXT,
            is_synthetic BOOLEAN DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT UNIQUE NOT NULL,
            device_ip TEXT NOT NULL,
            manufacturer TEXT NOT NULL,
            model TEXT NOT NULL,
            serial_number TEXT,
            location TEXT,
            status TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE devices_inventory ADD COLUMN serial_number TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE devices_inventory ADD COLUMN location TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE syslog_events ADD COLUMN component TEXT;")
    except sqlite3.OperationalError:
        pass

    # Cargar / Actualizar inventario de clase
    sample_devices = [
        ("MX68CW-Edge-01", "192.168.10.1", "Meraki", "MX68CW", "Q2KN-89XY-WZ12", "Datacenter / SASE Perímetro", "Activo", "2026-10-15 08:00:00"),
        ("Core-Switch-C1000", "192.168.1.254", "Cisco", "Catalyst C1000 (Capa 2)", "FOC2540X9ZQ", "Rack Principal - Unid 5", "Activo", "2026-10-15 08:00:00"),
        ("TP-Link-Mesh-A6", "192.168.20.1", "TP-Link", "Archer A6", "TPL98234100", "Oficinas Administrativas", "Activo", "2026-10-15 08:00:00"),
        ("TP-Link-AP-C50", "192.168.20.2", "TP-Link", "C50", "TPL50293111", "Pasillo Piso 2", "En Mantenimiento", "2026-10-15 08:00:00"),
        ("Edge-Firewall", "10.0.0.1", "Fortinet", "FortiGate 60F", "FGT60FTK22001920", "Perímetro / Oficina Central", "Activo", "2026-10-15 08:00:00")
    ]
    
    for dev in sample_devices:
        cursor.execute("""
            INSERT OR REPLACE INTO devices_inventory (hostname, device_ip, manufacturer, model, serial_number, location, status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, dev)

    # Cargar eventos sintéticos iniciales si la tabla no tiene datos propios recientes
    cursor.execute("SELECT COUNT(*) FROM syslog_events WHERE is_synthetic = 1")
    count_syn = cursor.fetchone()[0]
    
    if count_syn == 0:
        sample_events = [
            ("192.168.1.1", "Cisco", "2026-10-15 08:00:00", 0, 0, "Emergency: System thermal shutdown imminent due to high core temperature on core chassis", "Hardware / Chasis", 1),
            ("192.168.10.1", "Meraki", "2026-10-15 08:15:22", 1, 1, "Alert: BGP neighbor down on WAN interface, routing redundancy lost for SASE perimeter", "Enrutamiento / BGP", 1),
            ("192.168.1.254", "Cisco", "2026-10-15 08:30:05", 2, 2, "Critical: Catalyst C1000 port Gi0/5 security violation, DACL blocked unauthorized MAC", "Seguridad / MAB", 1),
            ("10.0.0.1", "Fortinet", "2026-10-15 09:12:30", 3, 3, "Error: IPsec VPN tunnel phase 1 failed negotiation with peer branch office", "VPN / IPsec", 1),
            ("192.168.20.1", "TP-Link", "2026-10-15 09:40:10", 4, 4, "Warning: High CPU usage (85%) detected on Archer A6 Mesh node administration", "Sistema / CPU", 1),
            ("192.168.1.1", "Cisco", "2026-10-15 10:00:00", 5, 5, "Notice: Line protocol on Interface GigabitEthernet0/1, changed state to up", "Interfaz: Gi0/1", 1),
            ("192.168.20.2", "TP-Link", "2026-10-15 10:10:00", 6, 6, "Informational: User admin successfully logged in via SSH management plane", "Acceso / AAA", 1),
            ("192.168.10.1", "Meraki", "2026-10-15 10:20:00", 7, 7, "Debug: SASE packet flow trace enabled for rule ID 402 on SD-WAN interface", "Debug / SD-WAN", 1)
        ]
        cursor.executemany("""
            INSERT INTO syslog_events (device_ip, manufacturer, timestamp, facility, severity, message, component, is_synthetic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_events)
              
    conn.commit()
    conn.close()


# --- MOTOR DE ESCUCHA SYSLOG UDP EN VIVO (PUERTO 514) ---
def parsear_syslog_remoto(mensaje):
    """Extrae el nivel de severidad y el texto del mensaje syslog de equipos reales"""
    m = re.search(r'%[A-Z0-9_]+-(\d)-[A-Z0-9_]+:\s*(.*)', mensaje)
    if m:
        return int(m.group(1)), m.group(2)
    return 5, mensaje # Por defecto Notice/Info si no aplica expresión exacta de Cisco

def servidor_syslog_udp():
    """Hilo en segundo plano para escuchar eventos físicos reales"""
    puerto = 514
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        servidor.bind(('0.0.0.0', puerto))
        print(f"==================================================")
        print(f"🟢 [SYSLOG REAL] Escuchando paquetes en puerto UDP {puerto}")
        print(f"==================================================")
    except Exception as e:
        print(f"⚠️ [SYSLOG REAL] No se pudo abrir el puerto 514: {e}")
        print("💡 RECUERDA: En Windows debes ejecutar VS Code como Administrador.")
        return

    while True:
        try:
            data, addr = servidor.recvfrom(2048)
            ip_origen = addr[0]
            mensaje_raw = data.decode('utf-8', errors='ignore').strip()
            
            severidad, texto_limpio = parsear_syslog_remoto(mensaje_raw)
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Guardar el log real directamente en SQLite
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO syslog_events (device_ip, manufacturer, timestamp, facility, severity, message, component, is_synthetic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ip_origen, "Cisco/Físico", fecha_hora, 1, severidad, texto_limpio, "Hardware Real", 0))
            conn.commit()
            conn.close()

            print(f"📥 [LOG EN VIVO] De: {ip_origen} | Sev: {severidad} | Msg: {texto_limpio}")
        except Exception as err:
            print(f"❌ Error al procesar paquete Syslog UDP: {err}")


@app.route("/")
def index():
    parse_and_load_sample_logs()
    
    active_tab = request.args.get('tab', 'dashboard')
    ip_filter = request.args.get('ip', '').strip()
    sev_filter = request.args.get('severity', '').strip()
    
    conn = get_db_connection()
    query = "SELECT * FROM syslog_events WHERE 1=1"
    params = []
    
    if ip_filter:
        query += " AND device_ip LIKE ?"
        params.append(f"%{ip_filter}%")
    if sev_filter:
        query += " AND severity = ?"
        params.append(sev_filter)
        
    query += " ORDER BY id DESC LIMIT 20"
    
    events = conn.execute(query, params).fetchall()
    devices = conn.execute("SELECT * FROM devices_inventory").fetchall()
    
    critical_count = conn.execute("SELECT COUNT(*) FROM syslog_events WHERE severity <= 2").fetchone()[0]
    noc_status = "CRÍTICO - Atención Requerida" if critical_count > 0 else "OPERATIVO - Sistema Estable"
    
    total_events_3m = conn.execute("SELECT COUNT(*) FROM syslog_events").fetchone()[0] * 12 
    open_cases = conn.execute("SELECT COUNT(*) FROM syslog_events WHERE severity <= 3").fetchone()[0]
    resolved_cases = max(0, total_events_3m - open_cases)
    
    conn.close()
    return render_template(
        "index.html", 
        events=events, 
        devices=devices, 
        ip_filter=ip_filter, 
        sev_filter=sev_filter,
        multivendor_configs=MULTIVENDOR_CONFIGS,
        noc_status=noc_status,
        critical_count=critical_count,
        active_tab=active_tab,
        metrics={
            "total_3m": total_events_3m + 142,
            "open_cases": open_cases + 5,
            "resolved_cases": resolved_cases + 137
        }
    )

@app.route("/device/add", methods=["POST"])
def add_device():
    hostname = request.form.get("hostname")
    device_ip = request.form.get("device_ip")
    manufacturer = request.form.get("manufacturer")
    model = request.form.get("model")
    serial_number = request.form.get("serial_number")
    location = request.form.get("location")
    status = request.form.get("status", "Activo")
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO devices_inventory (hostname, device_ip, manufacturer, model, serial_number, location, status, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (hostname, device_ip, manufacturer, model, serial_number, location, status, last_updated))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route("/device/update/<int:device_id>", methods=["POST"])
def update_device(device_id):
    location = request.form.get("location")
    status = request.form.get("status")
    model = request.form.get("model")
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    conn.execute("""
        UPDATE devices_inventory 
        SET location = ?, status = ?, model = ?, last_updated = ?
        WHERE id = ?
    """, (location, status, model, last_updated, device_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route("/device/delete/<int:device_id>", methods=["POST"])
def delete_device(device_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM devices_inventory WHERE id = ?", (device_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route("/api/console", methods=["POST"])
def api_console():
    start_time = time.time()
    data = request.get_json() or {}
    mode = data.get("mode", "simulate")
    
    if mode == "ssh":
        action = data.get("action", "exec")
        ip = data.get("ip", "")
        username = data.get("username", "")
        password = data.get("password", "")
        command = data.get("command", "")
        
        result = handle_ssh_action(action, ip, username, password, command)
    else:
        vendor = data.get("vendor", "Cisco")
        command = data.get("command", "")
        result = execute_safe_command(vendor, command)
        
    execution_time_ms = round((time.time() - start_time) * 1000, 2)
    result["latency_ms"] = execution_time_ms
    
    return jsonify(result)

if __name__ == "__main__":
    # Arrancar el hilo del servidor UDP Syslog en segundo plano
    hilo_syslog = threading.Thread(target=servidor_syslog_udp, daemon=True)
    hilo_syslog.start()

    # Arrancar la aplicación Flask web
    app.run(host="0.0.0.0", debug=True, port=5000)