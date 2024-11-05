from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# Configuraciones centralizadas
configurations = {
    "usuarios": {
        "USERS_SERVICE_PORT": 5000,
        "DATABASE_URL": "sqlite:///usuarios.db"
    },
    "pedidos": {
        "ORDERS_SERVICE_PORT": 5001,
        "DATABASE_URL": "sqlite:///pedidos.db"
    }
}

@app.route('/config/<service_name>', methods=['GET'])
def get_configuration(service_name):
    """Devuelve la configuración para un servicio específico."""
    config = configurations.get(service_name)
    if config:
        return jsonify(config)
    return jsonify({"error": "Servicio no encontrado"}), 404

@app.route('/config/<service_name>', methods=['POST'])
def set_configuration(service_name):
    """Actualiza la configuración de un servicio específico."""
    new_config = request.json
    configurations[service_name] = new_config
    return jsonify({"status": "Configuración actualizada"})

@app.route('/health', methods=['GET'])
def healthcheck():
    """Verifica el estado del servicio de configuración."""
    return jsonify({"status": "healthy", "service": "configuración"})

if __name__ == '__main__':
    app.run(port=5002, debug=True)

