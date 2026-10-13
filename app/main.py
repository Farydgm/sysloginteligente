from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from multivendor.templates_engine import MULTIVENDOR_CONFIGS, execute_safe_command

app = Flask(__name__, template_folder='web/templates')

# Rutas absolutas seguras
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "noc_syslog.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_and_load_sample_logs():
    """Garantiza la creación de tablas e inserta datos iniciales si están vacías."""
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
            is_synthetic BOOLEAN DEFAULT 1
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            device_ip TEXT NOT NULL,
            manufacturer TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM syslog_events")
    if cursor.fetchone()[0] == 0:
        sample_events = [
            ("192.168.1.1", "Cisco", "2026-10-12 18:30:00", 1, 5, "Line protocol on Interface GigabitEthernet0/1, changed state to up", 1),
            ("192.168.1.254", "Cisco", "2026-10-12 18:31:15", 23, 4, "list ADMIN denied tcp 10.0.0.5(54321) -> 192.168.1.1(22), 1 packet", 1),
            ("10.0.0.1", "Fortinet", "2026-10-12 18:32:10", 20, 2, "Critical: Admin login failed multiple times from 10.0.0.99", 1)
        ]
        cursor.executemany("""
            INSERT INTO syslog_events (device_ip, manufacturer, timestamp, facility, severity, message, is_synthetic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_events)

    cursor.execute("SELECT COUNT(*) FROM devices_inventory")
    if cursor.fetchone()[0] == 0:
        sample_devices = [
            ("Core-Router-01", "192.168.1.1", "Cisco", "Catalyst 3850", "Activo", "2026-10-12"),
            ("Edge-Firewall", "10.0.0.1", "Fortinet", "FortiGate 60F", "Activo", "2026-10-12"),
            ("Access-Switch-02", "192.168.1.254", "Cisco", "Catalyst 2960", "En Mantenimiento", "2026-10-11")
        ]
        cursor.executemany("""
            INSERT INTO devices_inventory (hostname, device_ip, manufacturer, model, status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_devices)
        
    conn.commit()
    conn.close()

@app.route("/")
def index():
    """Ruta principal con filtros, inventario y plantillas multivendor."""
    parse_and_load_sample_logs()
    
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
    conn.close()

    return render_template(
        "index.html", 
        events=events, 
        devices=devices, 
        ip_filter=ip_filter, 
        sev_filter=sev_filter,
        multivendor_configs=MULTIVENDOR_CONFIGS
    )

@app.route("/api/console", methods=["POST"])
def api_console():
    """Endpoint para la consola segura simulada con allowlist."""
    data = request.get_json() or {}
    command = data.get("command", "")
    result = execute_safe_command(command)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)