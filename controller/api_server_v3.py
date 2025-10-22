#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global references
controller = None
conversation_mgr = None
next_intent_id = 1

def set_controller(ctrl):
    """Set the SDN controller instance"""
    global controller
    controller = ctrl
    logger.info("✅ SDN Controller registered with API server")

def set_conversation_manager(conv_mgr):
    """Set the conversation manager instance"""
    global conversation_mgr
    conversation_mgr = conv_mgr
    logger.info("✅ Conversation Manager registered with API server")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'controller_connected': controller is not None,
        'llm_enabled': conversation_mgr.use_llm if conversation_mgr else False
    })

@app.route('/api/intents', methods=['GET'])
def get_intents():
    """Get all active intents"""
    try:
        if controller:
            intents = controller.get_intents()
            logger.info(f"📋 Returning {len(intents)} intents")
            return jsonify(intents)
        else:
            logger.warning("⚠️ Controller not available")
            return jsonify([]), 200
    except Exception as e:
        logger.error(f"❌ Error getting intents: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intents/<int:intent_id>', methods=['DELETE'])
def delete_intent(intent_id):
    """Delete an intent"""
    try:
        if controller:
            success = controller.delete_intent(intent_id)
            if success:
                socketio.emit('intent_deleted', {'id': intent_id})
                logger.info(f"🗑️ Intent {intent_id} deleted")
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Intent not found'}), 404
        else:
            return jsonify({'error': 'Controller not available'}), 503
    except Exception as e:
        logger.error(f"❌ Error deleting intent: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/flows', methods=['GET'])
def get_flows():
    """Get all active flows"""
    try:
        if controller:
            flows = controller.get_flow_stats()
            logger.info(f"🌊 Returning flows data")
            return jsonify(flows)
        else:
            return jsonify({}), 200
    except Exception as e:
        logger.error(f"❌ Error getting flows: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get network statistics"""
    try:
        if controller:
            stats = controller.get_network_load()
            logger.debug(f"📊 Stats: {stats}")
            return jsonify(stats)
        else:
            # Return simulated data when controller not available
            import random
            return jsonify({
                'throughput': round(random.uniform(50, 150), 2),  # Simulate 50-150 Mbps
                'latency': round(random.uniform(3, 15), 2),
                'activeFlows': random.randint(5, 20),
                'packetLoss': round(random.uniform(0, 0.05), 4)
            })
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        return jsonify({
            'throughput': 0,
            'latency': 0,
            'activeFlows': 0,
            'packetLoss': 0
        }), 200

@app.route('/api/topology', methods=['GET'])
def get_topology():
    """Get network topology"""
    try:
        if controller:
            # Get connected switches
            switches = list(controller.datapaths.keys())
            
            # Get hosts from MAC table
            hosts = []
            for dpid, mac_table in controller.mac_to_port.items():
                for mac in mac_table.keys():
                    hosts.append({
                        'mac': mac,
                        'port': mac_table[mac],
                        'switch': dpid
                    })
            
            topology = {
                'switches': switches,
                'hosts': hosts,
                'controller': {
                    'id': 'main_controller',
                    'address': '127.0.0.1:6655'
                }
            }
            
            logger.info(f"📡 Topology: {len(switches)} switches, {len(hosts)} hosts")
            return jsonify(topology)
        else:
            # Return default topology
            return jsonify({
                'switches': ['br0'],
                'hosts': [],
                'controller': {
                    'id': 'main_controller',
                    'address': '127.0.0.1:6655'
                }
            })
    except Exception as e:
        logger.error(f"❌ Error getting topology: {e}")
        return jsonify({
            'switches': ['br0'],
            'hosts': [],
            'controller': {'id': 'main_controller', 'address': '127.0.0.1:6655'}
        }), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat message"""
    global next_intent_id
    
    try:
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data received")
            return jsonify({
                'response': 'No data received',
                'action': 'error'
            }), 400
        
        user_id = data.get('user_id', 'anonymous')
        message = data.get('message', '').strip()
        
        if not message:
            logger.error("❌ Empty message received")
            return jsonify({
                'response': 'Please provide a message',
                'action': 'error'
            }), 400
        
        logger.info(f"💬 Chat from {user_id}: {message}")
        
        if not conversation_mgr:
            logger.error("❌ Conversation manager not available")
            return jsonify({
                'response': 'Conversation manager not initialized. Please check server logs.',
                'action': 'error'
            }), 503
        
        # Process with conversation manager
        response = conversation_mgr.process_message(user_id, message)
        logger.info(f"🤖 Raw response from LLM: {response}")
        
        # Parse response (it should be JSON from Groq)
        parsed_response = None
        if isinstance(response, str):
            try:
                parsed_response = json.loads(response)
                logger.info(f"✅ Parsed JSON response: {parsed_response}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse JSON response: {e}")
                logger.error(f"❌ Raw response was: {response}")
                # Return the raw string as response
                parsed_response = {
                    'response': response,
                    'action': 'error'
                }
        else:
            parsed_response = response
        
        # Validate response structure
        if not isinstance(parsed_response, dict):
            logger.error(f"❌ Response is not a dict: {type(parsed_response)}")
            parsed_response = {
                'response': str(parsed_response),
                'action': 'error'
            }
        
        # Ensure response has required fields
        if 'response' not in parsed_response:
            logger.warning("⚠️ Response missing 'response' field, adding default")
            parsed_response['response'] = 'I processed your request but couldn\'t generate a proper response.'
        
        # Check if intent should be applied
        if parsed_response.get('action') == 'apply' and parsed_response.get('intent'):
            intent_data = parsed_response['intent']
            intent_id = next_intent_id
            next_intent_id += 1
            
            # Apply intent to controller
            if controller:
                intent_to_apply = {
                    'message': message,
                    'intent': intent_data
                }
                success = controller.apply_intent(intent_id, intent_to_apply)
                
                if success:
                    parsed_response['action'] = 'applied'
                    parsed_response['intent_id'] = intent_id
                    logger.info(f"✅ Intent {intent_id} applied successfully")
                    
                    # Emit update to all connected clients
                    socketio.emit('intent_updated', {
                        'id': intent_id,
                        'intent': controller.intents.get(intent_id)
                    })
                else:
                    parsed_response['action'] = 'failed'
                    parsed_response['response'] += '\n\nFailed to apply the configuration to the network.'
                    logger.error(f"❌ Failed to apply intent {intent_id}")
            else:
                parsed_response['action'] = 'no_controller'
                parsed_response['response'] += '\n\nController not available.'
                logger.warning("⚠️ Controller not available for intent application")
        
        logger.info(f"📤 Final response: {parsed_response}")
        return jsonify(parsed_response), 200
        
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}", exc_info=True)
        return jsonify({
            'response': f'An error occurred: {str(e)}',
            'action': 'error'
        }), 500

@app.route('/api/chat/clear/<user_id>', methods=['DELETE'])
def clear_chat(user_id):
    """Clear chat history for a user"""
    try:
        if conversation_mgr and user_id in conversation_mgr.conversations:
            del conversation_mgr.conversations[user_id]
            logger.info(f"🗑️ Cleared chat for user {user_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ Error clearing chat: {e}")
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"🔌 Client connected: {request.sid}")
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"🔌 Client disconnected: {request.sid}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat message via WebSocket"""
    logger.info(f"💬 WebSocket chat message: {data}")
    emit('chat_message', data, broadcast=True)

def run_api_server(port=8080):
    """Run the API server"""
    logger.info(f"🚀 Starting API server on port {port}")
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ API server failed: {e}")
        raise

if __name__ == '__main__':
    run_api_server()
