import logging
import win32evtlogutil
import win32con
from flask import Flask, jsonify, request, Response
import os
import redis
import requests
import psutil  # Para monitoreo del sistema

# Obtener configuración desde el servicio de configuración centralizado
response = requests.get('http://localhost:5002/config/usuarios')
config = response.json()

# Configuración del cliente Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Configurar el logger
logging.basicConfig(level=logging.INFO)

# Crear la aplicación Flask
app = Flask(__name__)

def log_event(message):
    logging.info(message)
    win32evtlogutil.ReportEvent("UsuariosService", 1001, eventCategory=0, eventType=win32con.EVENTLOG_INFORMATION_TYPE, strings=[message])

# Usuario y contraseña codificados para pruebas
users = {
    "camisebas": "2003004",
}

def authenticate_user(username, password):
    return users.get(username) == password

@app.before_request
def before_request():
    auth = request.authorization
    if not auth or not authenticate_user(auth.username, auth.password):
        return Response("Could not verify your access level for that URL.\nYou have to login with proper credentials", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})

log_event("El servicio de usuarios ha sido iniciado.")

# Datos simulados de usuarios
usuarios = [
    {"id": 1, "nombre": "Ana García", "email": "ana@email.com"},
    {"id": 2, "nombre": "Carlos López", "email": "carlos@email.com"},
    {"id": 3, "nombre": "María Rodríguez", "email": "maria@email.com"}
]

@app.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    """Endpoint para obtener todos los usuarios"""
    log_event("Solicitud GET a /usuarios")
    return jsonify({"usuarios": usuarios, "total": len(usuarios)})

@app.route('/usuarios/<int:usuario_id>', methods=['GET'])
def obtener_usuario(usuario_id):
    """Endpoint para obtener un usuario específico por ID"""
    log_event(f"Solicitud GET a /usuarios/{usuario_id}")
    # Verificar en caché Redis
    usuario_cache = redis_client.get(f"usuario:{usuario_id}")
    if usuario_cache:
        return jsonify({"usuario": eval(usuario_cache.decode('utf-8'))})
    # Buscar en base de datos local si no está en caché
    usuario = next((u for u in usuarios if u["id"] == usuario_id), None)
    if usuario:
        # Almacenar en caché
        redis_client.set(f"usuario:{usuario_id}", str(usuario))
        return jsonify({"usuario": usuario})
    log_event(f"Usuario {usuario_id} no encontrado")
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/health', methods=['GET'])
def healthcheck():
    """Endpoint para verificar el estado del servicio"""
    return jsonify({"status": "healthy", "service": "usuarios"})

@app.route('/monitor', methods=['GET'])
def monitor():
    """Endpoint para monitorear el uso de recursos del sistema"""
    uso_cpu = psutil.cpu_percent(interval=1)
    uso_memoria = psutil.virtual_memory().percent
    uso_disco = psutil.disk_usage('/').percent
    return jsonify({
        "cpu_percent": uso_cpu,
        "memory_percent": uso_memoria,
        "disk_percent": uso_disco
    })

if __name__ == '__main__':
    # Usar el puerto que viene del servicio de configuración
    puerto = config['USERS_SERVICE_PORT']
    app.run(port=puerto, debug=True)
