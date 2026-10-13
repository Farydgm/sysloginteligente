# Motor de configuraciones multivendor y catálogo completo de comandos de verificación

MULTIVENDOR_CONFIGS = {
    "Cisco": {
        "model": "Cisco Catalyst / IOS",
        "description": "Configuración estándar Syslog, SSH y ACLs de seguridad.",
        "config": """
! --- CONFIGURACIÓN CISCO IOS SYSLOG & SSH ---
service timestamps log datetime msec localtime
logging 192.168.1.100
logging facility local6
logging severity informational
line vty 0 4
 transport input ssh
 login local
        """.strip(),
        "commands": {
            "show version": "Cisco IOS Software, Version 15.2(4)M1, RELEASE SOFTWARE... Uptime is 45 days, 12 hours.",
            "show ip interface brief": "Interface              IP-Address      OK? Method Status                Protocol\nGigabitEthernet0/0     192.168.1.1     YES manual up                    up\nGigabitEthernet0/1     unassigned      YES unset  administratively down down\nVlan10                 192.168.10.254  YES manual up                    up",
            "show running-config": "Building configuration...\nCurrent configuration : 2450 bytes\nversion 15.2\nservice timestamps log datetime msec\nhostname Core-Router-01\nip routing\nend",
            "show ip route": "Gateway of last resort is 192.168.1.254 to network 0.0.0.0\nC    192.168.1.0/24 is directly connected, GigabitEthernet0/0\nS*   0.0.0.0/0 [1/0] via 192.168.1.254",
            "show vlan brief": "VLAN Name                             Status    Ports\n---- -------------------------------- --------- ------------------------------\n1    default                          active    Gi0/2, Gi0/3\n10   DATA_VLANS                       active    Gi0/1\n20   VOICE_VLAN                       active    ",
            "show interfaces trunk": "Port        Mode         Encapsulation  Status        Native vlan\nGi0/1       on           802.1q         trunking      1",
            "show spanning-tree": "VLAN0001\n  Spanning tree enabled protocol ieee\n  Root ID    Priority    32768\n             Address     0011.2233.4455\n             This bridge is the root",
            "show cpu": "CPU utilization for five seconds: 12%/2%; one minute: 8%; five minutes: 5%",
            "show memory": "Processor pool total: 536870912 bytes, used: 214582310, free: 322288602 [40% Used]"
        }
    },
    "Fortinet": {
        "model": "FortiGate / FortiOS",
        "description": "Configuración de servidor syslog remoto y políticas de registro en FortiOS.",
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
        """.strip(),
        "commands": {
            "get system status": "Version: FortiGate-60F v7.2.4,build1393,230214 (GA)\nMode: NAT\nFirewall Driver: 3.0.0\nSystem time: Tue Oct 13 14:30:00 2026",
            "get system performance": "CPU states: 8% user, 3% system, 89% idle\nMemory states: 42% used, total 2048MB",
            "show system interface": "== [port1]\nname: port1 mode: static ip: 10.0.0.1 255.255.255.0 status: up\n== [port2]\nname: port2 mode: dhcp status: down",
            "get router info routing-table all": "Codes: K - kernel, C - connected, S - static, R - RIP, O - OSPF\nS*      0.0.0.0/0 [10/0] via 10.0.0.254, port1, [10/0]\nC       10.0.0.0/24 is directly connected, port1",
            "show firewall policy": "== [ 1 ]\nname: \"LAN_to_WAN\"\nsrcintf: \"port2\" dstintf: \"port1\"\naction: accept\nstatus: enable",
            "diagnose sys top": "Run: 3 running, 0 sleeping, 0 stopped; 2GB total, 840MB mem used.\n# CPU  PID   PPID   State   Mem[%]  CPU[%]\n  0    142   1      S       2.1     1.2   httpsd",
            "diagnose hardware sysinfo memory": "Total RAM: 2048 MB\nFree RAM: 1180 MB\nCached: 250 MB"
        }
    },
    "Huawei": {
        "model": "Huawei VRP",
        "description": "Configuración de canal de logging y traps en plataforma VRP de Huawei.",
        "config": """
# --- CONFIGURACIÓN HUAWEI VRP SYSLOG ---
info-center enable
info-center loghost source Vlanif10
info-center loghost 192.168.1.100 channel 2 facility local6
info-center level informational
        """.strip(),
        "commands": {
            "display version": "Huawei VRP Software Version 8.160... Quidway S5700 uptime is 30 weeks.",
            "display interface brief": "PHY: Up      \nInbound bandwidth: 1000M, Outbound bandwidth: 1000M\nInterface                      PHY   Protocol  InUti OutUti\nVlanif10                       up    up        0.01%  0.02%",
            "display current-configuration": "sysname Access-Switch-02\n#\nvlan batch 10 20\n#\ninterface Vlanif10\n ip address 192.168.1.254 255.255.255.0\n#\nreturn",
            "display ip routing-table": "Route Flags: R - relay, D - download to fib\nDestination/Mask    Proto   Pre  Cost      Flags NextHop         Interface\n127.0.0.0/8         Direct  0    0         D     127.0.0.1       InLoopBack0\n192.168.1.0/24      Direct  0    0         D     192.168.1.254   Vlanif10",
            "display vlan": "The total number of VLANs is: 2\n--------------------------------------------------------------------\nID    Type    Enports    Trunks\n1     common  GE0/0/1    GE0/0/2\n10    common  GE0/0/3    -\n--------------------------------------------------------------------",
            "display cpu-usage": "CPU Usage Stat. : 6% max: 45%\nSystem CPU Memory Threshold : 80%",
            "display memory-usage": "Total Memory: 4194304 KB, Used Memory: 1677721 KB (40%)"
        }
    }
}

def execute_safe_command(vendor, cmd):
    clean_vendor = vendor.strip()
    clean_cmd = cmd.strip().lower()
    
    if clean_vendor in MULTIVENDOR_CONFIGS:
        vendor_cmds = MULTIVENDOR_CONFIGS[clean_vendor]["commands"]
        if clean_cmd in vendor_cmds:
            return {
                "status": "success",
                "output": f"[{clean_vendor} VERIFICATION OUTPUT - COMMAND: {clean_cmd}]\n\n" + vendor_cmds[clean_cmd]
            }
        else:
            allowed = "\n - ".join(vendor_cmds.keys())
            return {
                "status": "denied",
                "output": f"ERROR: Comando '{clean_cmd}' no autorizado o no reconocido para {clean_vendor}.\n\nComandos permitidos disponibles:\n - " + allowed
            }
    return {
        "status": "error",
        "output": "ERROR: Fabricante no válido seleccionado."
    }