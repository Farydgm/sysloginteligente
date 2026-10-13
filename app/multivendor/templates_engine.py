# Plantillas de configuración comentadas para equipos multivendor (Cisco, Fortinet, Huawei)
MULTIVENDOR_CONFIGS = {
    "Cisco": {
        "model": "Cisco Catalyst / IOS",
        "description": "Configuración estándar Syslog y SSH para equipos Cisco IOS",
        "config": """
! --- CONFIGURACIÓN CISCO IOS SYSLOG & SSH ---
service timestamps log datetime msec localtime show-timezone
logging 192.168.1.100
logging facility local6
logging severity informational
line vty 0 4
 transport input ssh
 login local
        """.strip()
    },
    "Fortinet": {
        "model": "FortiGate / FortiOS",
        "description": "Configuración de servidor syslog remoto en FortiOS",
        "config": """
# --- CONFIGURACIÓN FORTINET FORTIOS SYSLOG ---
config log syslogd setting
    set status enable
    set server "192.168.1.100"
    set mode udp
    set port 5140
    set facility local6
    set severity information
end
        """.strip()
    },
    "Huawei": {
        "model": "Huawei VRP",
        "description": "Configuración de canal de logging y trap en VRP de Huawei",
        "config": """
# --- CONFIGURACIÓN HUAWEI VRP SYSLOG ---
info-center enable
info-center loghost source Vlanif10
info-center loghost 192.168.1.100 channel 2 facility local6
info-center level informational
        """.strip()
    }
}

# Consola Segura Simulada (Allowlist de comandos permitidos de solo lectura)
ALLOWED_COMMANDS = {
    "show version": "Cisco IOS Software, Version 15.2(4)M1, RELEASE SOFTWARE (fc1)... Uptime is 45 days, 12 hours, 30 mins.",
    "show ip interface brief": "Interface              IP-Address      OK? Method Status                Protocol\nGigabitEthernet0/0     192.168.1.1     YES manual up                    up\nGigabitEthernet0/1     unassigned      YES unset  administratively down down",
    "show memory": "Processor pool total: 536870912, used: 214582310, free: 322288602 [40% Used]",
    "show cpu": "CPU utilization for five seconds: 12%/2%; one minute: 8%; five minutes: 5%"
}

def execute_safe_command(cmd):
    """Ejecuta un comando en la consola simulada validando contra la allowlist."""
    clean_cmd = cmd.strip().lower()
    if clean_cmd in ALLOWED_COMMANDS:
        return {
            "status": "success",
            "command": clean_cmd,
            "output": ALLOWED_COMMANDS[clean_cmd]
        }
    else:
        return {
            "status": "denied",
            "command": clean_cmd,
            "output": f"ERROR: Comando '{clean_cmd}' no autorizado o no permitido en la consola de solo lectura (Allowlist activa)."
        }