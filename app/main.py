from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__, template_folder='web/templates')

# Definimos rutas absolutas seguras
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "noc_syslog.db")

def get_db_connection():
    """Establece conexión segura con la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_and_load_sample_logs():
    """Garantiza la creación de la tabla e inserta eventos de prueba si está vacía."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear la tabla si no existe
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
    
    # Verificar si ya existen registros
    cursor.execute("SELECT COUNT(*) FROM syslog_events")
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_events = [
            ("192.168.1.1", "Cisco", "2026-10-12 18:30:00", 1, 5, "Line protocol on Interface GigabitEthernet0/1, changed state to up", 1),
            ("192.168.1.254", "Cisco", "2026-10-12 18:31:15", 23, 4, "list ADMIN denied tcp 10.0.0.5(54321) -> 192.168.1.1(22), 1 packet", 1),
            ("10.0.0.1", "Fortinet", "2026-10-12 18:32:10", 20, 2, "Critical: Admin login failed multiple times from 10.0.0.99", 1)
        ]
        cursor.executemany("""
            INSERT INTO syslog_events (device_ip, manufacturer, timestamp, facility, severity, message, is_synthetic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_events)
        conn.commit()
        
    conn.close()

# RUTA PRINCIPAL (¡El decorador que evita el 404!)
@app.route("/")
def index():
    """Ruta principal: Dashboard Alfa con eventos de red."""
    parse_and_load_sample_logs()
    
    conn = get_db_connection()
    events = conn.execute("SELECT * FROM syslog_events ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()

    # Aquí es donde Flask busca dentro de la carpeta templates/
    return render_template("index.html", events=events)

if __name__ == "__main__":
    app.run(debug=True, port=5000)