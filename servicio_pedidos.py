import logging
import win32evtlogutil
import win32con
from flask import Flask, jsonify, request, Response
from dotenv import load_dotenv
import os
import redis
import requests
import psutil  # Para monitoreo del sistema

# Cargar las variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración del cliente Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Configurar el logger
logging.basicConfig(level=logging.INFO)

def log_event(message):
    logging.info(message)
    win32evtlogutil.ReportEvent("PedidosService", 1002, eventCategory=0, eventType=win32con.EVENTLOG_INFORMATION_TYPE, strings=[message])

# Obtener configuración desde el servicio de configuración centralizado
response = requests.get('http://localhost:5002/config/pedidos')
config = response.json()

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

# Datos simulados de pedidos
pedidos = [
    {"id": 1, "usuario_id": 1, "producto": "Laptop", "cantidad": 1, "total": 999.99},
    {"id": 2, "usuario_id": 1, "producto": "Mouse", "cantidad": 2, "total": 49.98},
    {"id": 3, "usuario_id": 2, "producto": "Monitor", "cantidad": 1, "total": 299.99},
    {"id": 4, "usuario_id": 3, "producto": "Teclado", "cantidad": 1, "total": 89.99}
]

def verificar_usuario(usuario_id):
    """Verifica si existe un usuario consultando al servicio de usuarios"""
    try:
        puerto_usuarios = config['USERS_SERVICE_PORT']
        response = requests.get(f'http://localhost:{puerto_usuarios}/usuarios/{usuario_id}')
        return response.status_code == 200
    except requests.RequestException:
        return False

@app.route('/pedidos', methods=['GET'])
def obtener_pedidos():
    """Endpoint para obtener todos los pedidos"""
    log_event("Solicitud GET a /pedidos")
    return jsonify({"pedidos": pedidos, "total": len(pedidos)})

@app.route('/pedidos/usuario/<int:usuario_id>', methods=['GET'])
def obtener_pedidos_usuario(usuario_id):
    """Endpoint para obtener los pedidos de un usuario específico"""
    # Verificar en caché Redis
    pedidos_cache = redis_client.get(f"pedidos_usuario:{usuario_id}")
    if pedidos_cache:
        return jsonify({"pedidos": eval(pedidos_cache.decode('utf-8'))})
    log_event(f"Solicitud GET a /pedidos/usuario/{usuario_id}")
    if not verificar_usuario(usuario_id):
        log_event(f"Usuario {usuario_id} no encontrado")
        return jsonify({"error": "Usuario no encontrado"}), 404
    pedidos_usuario = [p for p in pedidos if p["usuario_id"] == usuario_id]
    # Guardar en caché Redis
    redis_client.set(f"pedidos_usuario:{usuario_id}", str(pedidos_usuario))
    return jsonify({
        "usuario_id": usuario_id,
        "pedidos": pedidos_usuario,
        "total_pedidos": len(pedidos_usuario)
    })

@app.route('/health', methods=['GET'])
def healthcheck():
    """Endpoint para verificar el estado del servicio"""
    return jsonify({"status": "healthy", "service": "pedidos"})

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
    try:
        puerto = config['ORDERS_SERVICE_PORT']
        app.run(port=puerto, debug=True)
    except Exception as e:
        log_event(f"Error al iniciar el servicio de pedidos: {str(e)}")
        print(f"Error: {str(e)}")
