import os

def build_structure():
    # Definimos la estructura exacta solicitada para el proyecto NOC Syslog
    directories = [
        "docs/evidencias",
        "app/collector",
        "app/incidents",
        "app/ssh_adapter",
        "app/web",
        "tests",
        "data"
    ]
    
    # 1. Crear carpetas y archivos __init__.py en los submódulos de app
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[Carpeta creada/verificada]: {dir_path}")
        
        if dir_path.startswith("app/") and dir_path != "app/":
            init_file = os.path.join(dir_path, "__init__.py")
            if not os.path.exists(init_file):
                open(init_file, 'w').close()

    # 2. Crear archivos base esenciales (vacíos o con estructura inicial segura)
    base_files = {
        "README.md": "# NOC Syslog Inteligente (v0.2.0 Alfa)\n\nProyecto de Administración y Gestión de Redes - 2026-2.\n",
        ".gitignore": "__pycache__/\n*.db\n.env\nvenv/\n.vscode/\n",
        ".env.example": "SECRET_KEY=cambiar_por_una_llave_segura\nDB_PATH=data/noc_syslog.db\n",
        "requirements.txt": "Flask==3.0.2\nWerkzeug==3.0.1\n",
        "docs/requisitos.md": "# Requisitos del Sistema - NOC Syslog Inteligente\n",
        "docs/historias.md": "# Historias de Usuario - Alfa\n",
        "app/__init__.py": ""
    }

    for filepath, content in base_files.items():
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[Archivo creado]: {filepath}")
        else:
            print(f"[Ya existe]: {filepath}")

    print("\n¡Estructura del proyecto desplegada con éxito!")

if __name__ == "__main__":
    build_structure()