# IMPORTANT: Monkey patch MUST be first
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enhanced CORS configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

socketio = SocketIO(app, 
                    cors_allowed_origins="*",
                    async_mode='eventlet',
                    logger=True,
                    engineio_logger=True)

controller = None

def set_controller(ctrl):
    global controller
    controller = ctrl
    logger.info("Controller set in API server")

@app.route('/api/intents', methods=['GET', 'OPTIONS'])
def get_intents():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        if controller:
            intents = controller.get_intents()
            logger.info(f"Returning {len(intents)} intents")
            return jsonify(intents)
        return jsonify([])
    except Exception as e:
        logger.error(f"Error getting intents: {e}")
        return jsonify([])

@app.route('/api/intents', methods=['POST'])
def create_intent():
    try:
        data = request.json
        logger.info(f"Creating intent: {data}")
        if controller:
            intent = controller.add_intent(data)
            socketio.emit('intent_updated', intent)
            return jsonify(intent), 201
        return jsonify({'error': 'Controller not available'}), 503
    except Exception as e:
        logger.error(f"Error creating intent: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intents/<int:intent_id>', methods=['DELETE'])
def delete_intent(intent_id):
    try:
        logger.info(f"Deleting intent: {intent_id}")
        if controller:
            controller.remove_intent(intent_id)
            socketio.emit('intent_deleted', {'id': intent_id})
            return jsonify({'status': 'deleted'})
        return jsonify({'error': 'Controller not available'}), 503
    except Exception as e:
        logger.error(f"Error deleting intent: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/flows', methods=['GET'])
def get_flows():
    try:
        if controller:
            flows = controller.get_flows()
            return jsonify(flows)
        return jsonify({})
    except Exception as e:
        logger.error(f"Error getting flows: {e}")
        return jsonify({})

@app.route('/api/topology', methods=['GET'])
def get_topology():
    try:
        if controller:
            topology = controller.get_topology()
            logger.info(f"Topology: {topology}")
            return jsonify(topology)
        return jsonify({'switches': [], 'links': [], 'hosts': 0})
    except Exception as e:
        logger.error(f"Error getting topology: {e}")
        return jsonify({'switches': [], 'links': [], 'hosts': 0})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        # Generate realistic stats
        stats = {
            'throughput': 756 + random.randint(-100, 100),
            'latency': 12 + random.uniform(-5, 5),
            'active_flows': len(controller.get_flows()) if controller else 0,
            'packet_loss': 0.02 + random.uniform(-0.01, 0.01)
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'throughput': 0,
            'latency': 0,
            'active_flows': 0,
            'packet_loss': 0
        })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'controller_connected': controller is not None
    })

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

def run_api_server(port=8080):
    logger.info(f"Starting API server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_api_server()
