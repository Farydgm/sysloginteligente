import paramiko
import time

# Diccionario global para mantener las sesiones SSH activas por usuario@ip
active_ssh_sessions = {}

class SSHInteractiveSession:
    def __init__(self, ip, username, password, port=22):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(ip, port=int(port), username=username, password=password, timeout=5)
        
        # Abrir pseudo-terminal interactiva (tipo PuTTY)
        self.channel = self.client.invoke_shell()
        self.channel.settimeout(1.5)
        time.sleep(0.5)
        
        # Capturar el banner inicial de bienvenida
        self.buffer = ""
        if self.channel.recv_ready():
            self.buffer = self.channel.recv(65535).decode('utf-8', errors='ignore')

    def send_command(self, command):
        if self.channel.closed:
            raise Exception("El canal SSH está cerrado.")
        
        # Enviar comando con salto de línea
        self.channel.send(command + "\n")
        time.sleep(1) # Pausa breve para que el dispositivo responda
        
        output = ""
        while self.channel.recv_ready():
            output += self.channel.recv(65535).decode('utf-8', errors='ignore')
        return output

    def close(self):
        try:
            self.channel.close()
            self.client.close()
        except:
            pass

def handle_ssh_action(action, ip, username, password, command="", port=22):
    """Administra la sesión interactiva: 'connect' o 'exec'."""
    session_key = f"{username}@{ip}"
    
    if not ip or not username or not password:
        return {
            "status": "error",
            "output": "ERROR: Debe ingresar IP, usuario y contraseña para la conexión SSH."
        }

    try:
        if action == "connect":
            # Si ya existía una sesión previa, cerrarla limpiamente
            if session_key in active_ssh_sessions:
                active_ssh_sessions[session_key].close()
            
            ssh_sess = SSHInteractiveSession(ip, username, password, port)
            active_ssh_sessions[session_key] = ssh_sess
            return {
                "status": "success",
                "output": f"[CONEXIÓN INTERACTIVA ESTABLECIDA CON ÉXITO - {ip}]\n{ssh_sess.buffer}"
            }
            
        elif action == "exec":
            # Si no hay sesión activa, intentar conectarse automáticamente
            if session_key not in active_ssh_sessions:
                ssh_sess = SSHInteractiveSession(ip, username, password, port)
                active_ssh_sessions[session_key] = ssh_sess
            
            ssh_sess = active_ssh_sessions[session_key]
            output = ssh_sess.send_command(command)
            return {
                "status": "success",
                "output": output if output else "[Comando enviado sin respuesta visual de retorno]"
            }
            
    except Exception as e:
        if session_key in active_ssh_sessions:
            del active_ssh_sessions[session_key]
        return {
            "status": "error",
            "output": f"ERROR SSH INTERACTIVO: {str(e)}"
        }