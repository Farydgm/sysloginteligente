# Historias de Usuario - Alfa
# Historias de Usuario y Criterios de Aceptación - NOC Syslog Inteligente

**Estudiante:** Faryd Albenis Garcia Moreno  
**Asignatura:** Administración y Gestión de Redes  

---

## HU01: Ingesta y Almacenamiento de Syslog
* **Como** operador del NOC,  
* **Quiero** que el sistema escuche tramas UDP y las guarde automáticamente en la base de datos,  
* **Para** no perder ningún evento crítico de los dispositivos de red.
* **Criterios de Aceptación:**
  1. El colector debe iniciarse en el puerto `5140`.
  2. Los paquetes recibidos deben parsear correctamente su cabecera y nivel de severidad.

## HU02: Filtrado y Visualización en Dashboard
* **Como** administrador de red,  
* **Quiero** filtrar los eventos en el panel web por IP o severidad,  
* **Para** aislar rápidamente comportamientos anómalos o fallos de hardware.
* **Criterios de Aceptación:**
  1. El dashboard debe mostrar insignias de color distintivas según la severidad (Crítica, Advertencia, Normal).
  2. Debe existir un botón de reinicio de filtros funcionales.

## HU03: Consola Segura y Plantillas Multivendor
* **Como** ingeniero de redes junior,  
* **Quiero** consultar plantillas de configuración y ejecutar comandos permitidos,  
* **Para** configurar equipos Cisco, Fortinet y Huawei de forma estandarizada y segura.
* **Criterios de Aceptación:**
  1. Las plantillas deben mostrarse claramente documentadas en el panel.
  2. La consola interactiva debe rechazar cualquier comando que no se encuentre en la lista blanca (*allowlist*).