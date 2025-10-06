# IMPORTANT: Monkey patch MUST be first, before any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import logging

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

controller = None

def set_controller(ctrl):
    global controller
    controller = ctrl

@app.route('/api/intents', methods=['GET'])
def get_intents():
    if controller:
        return jsonify(controller.get_intents())
    return jsonify([])

@app.route('/api/intents', methods=['POST'])
def create_intent():
    data = request.json
    if controller:
        intent = controller.add_intent(data)
        socketio.emit('intent_updated', intent)
        return jsonify(intent), 201
    return jsonify({'error': 'Controller not available'}), 503

@app.route('/api/intents/<int:intent_id>', methods=['DELETE'])
def delete_intent(intent_id):
    if controller:
        controller.remove_intent(intent_id)
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Controller not available'}), 503

@app.route('/api/flows', methods=['GET'])
def get_flows():
    if controller:
        return jsonify(controller.get_flows())
    return jsonify({})

@app.route('/api/topology', methods=['GET'])
def get_topology():
    if controller:
        return jsonify(controller.get_topology())
    return jsonify({'switches': [], 'links': []})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    import random
    stats = {
        'throughput': 756 + random.randint(-100, 100),
        'latency': 12 + random.randint(-5, 5),
        'active_flows': 1247 + random.randint(-50, 50),
        'packet_loss': 0.02 + random.uniform(-0.01, 0.01)
    }
    return jsonify(stats)

def run_api_server(port=8080):
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_api_server()
