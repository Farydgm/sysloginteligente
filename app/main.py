from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime
from multivendor.templates_engine import MULTIVENDOR_CONFIGS, execute_safe_command

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
            serial_number TEXT,
            location TEXT,
            status TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
    
    # Asegurar columnas en bases de datos existentes de versiones anteriores
    try:
        cursor.execute("ALTER TABLE devices_inventory ADD COLUMN serial_number TEXT;")
    except sqlite3.OperationalError:
        pass # La columna ya existe
        
    try:
        cursor.execute("ALTER TABLE devices_inventory ADD COLUMN location TEXT;")
    except sqlite3.OperationalError:
        pass # La columna ya existe

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
            ("Core-Router-01", "192.168.1.1", "Cisco", "Catalyst 3850", "FOC2540X9ZQ", "Datacenter Principal (Rack A1)", "Activo", "2026-10-01"),
            ("Edge-Firewall", "10.0.0.1", "Fortinet", "FortiGate 60F", "FGT60FTK22001920", "Perímetro / Oficina Central", "Activo", "2026-10-05"),
            ("Access-Switch-02", "192.168.1.254", "Cisco", "Catalyst 2960", "CAT0920M3AB", "Piso 2 - Oficinas", "En Mantenimiento", "2026-10-10")
        ]
        cursor.executemany("""
            INSERT INTO devices_inventory (hostname, device_ip, manufacturer, model, serial_number, location, status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_devices)
        
    conn.commit()
    conn.close()

@app.route("/")
def index():
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
    
    critical_count = conn.execute("SELECT COUNT(*) FROM syslog_events WHERE severity <= 2").fetchone()[0]
    conn.close()

    noc_status = "CRÍTICO - Atención Requerida" if critical_count > 0 else "OPERATIVO - Sistema Estable"

    return render_template(
        "index.html", 
        events=events, 
        devices=devices, 
        ip_filter=ip_filter, 
        sev_filter=sev_filter,
        multivendor_configs=MULTIVENDOR_CONFIGS,
        noc_status=noc_status,
        critical_count=critical_count
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
    last_updated = datetime.now().strftime("%d-%m-%Y")
    
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
    """Ruta para actualizar estado, ubicación y detalles de un equipo existente."""
    location = request.form.get("location")
    status = request.form.get("status")
    model = request.form.get("model")
    last_updated = datetime.now().strftime("%d-%m-%Y")
    
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
    data = request.get_json() or {}
    vendor = data.get("vendor", "Cisco")
    command = data.get("command", "")
    result = execute_safe_command(vendor, command)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)