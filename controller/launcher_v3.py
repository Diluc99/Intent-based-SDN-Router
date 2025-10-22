#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()

import sys
import threading
import time
import signal
import os
import logging
from logging.handlers import RotatingFileHandler

# Local imports
import api_server_v3 as api_server
from conversation_manager import ConversationManager

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'controller.log'),
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def wait_for_api_server(port, timeout=30):
    """Wait for API server to be available"""
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except (socket.error, socket.timeout):
            time.sleep(1)
    return False

def main():
    logger.info("=" * 70)
    logger.info("🚀 Starting SDN Router V3 with Conversational AI")
    logger.info("=" * 70)
    
    # Check environment
    from dotenv import load_dotenv
    load_dotenv()
    
    use_llm = os.getenv('USE_LLM', 'false').lower() == 'true'
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not use_llm:
        logger.error("❌ LLM mode is required. Set USE_LLM=true in .env file")
        sys.exit(1)
    
    if not groq_key:
        logger.error("❌ GROQ_API_KEY not found in .env file")
        sys.exit(1)
    
    logger.info(f"✅ Environment check passed")
    logger.info(f"   - LLM Mode: {use_llm}")
    logger.info(f"   - Groq API Key: {'*' * 20}{groq_key[-4:]}")
    
    # Initialize conversation manager
    try:
        logger.info("🤖 Initializing Conversation Manager...")
        conversation_mgr = ConversationManager()
        api_server.set_conversation_manager(conversation_mgr)
        logger.info("✅ Conversation Manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize conversation manager: {e}")
        sys.exit(1)
    
    # Start API server in separate thread
    logger.info("🌐 Starting API server on port 8080...")
    api_thread = threading.Thread(
        target=api_server.run_api_server,
        args=(8080,),
        daemon=True,
        name="APIServerThread"
    )
    api_thread.start()
    
    # Wait for API server
    if not wait_for_api_server(8080):
        logger.error("❌ API server failed to start")
        sys.exit(1)
    
    # Verify API server health
    import requests
    try:
        response = requests.get('http://localhost:8080/api/health', timeout=5)
        if response.status_code == 200:
            health = response.json()
            logger.info("✅ API server started successfully")
            logger.info(f"   - Status: {health.get('status')}")
            logger.info(f"   - LLM Enabled: {health.get('llm_enabled')}")
        else:
            logger.error(f"❌ API server health check failed: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to connect to API server: {e}")
        sys.exit(1)
    
    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info("\n" + "=" * 70)
        logger.info("🛑 Shutting down gracefully...")
        logger.info("=" * 70)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure controller directory is in path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Set up SDN controller path
    controller_path = os.path.join(current_dir, 'sdn_controller_v2.py')
    
    if not os.path.exists(controller_path):
        logger.error(f"❌ Controller file not found: {controller_path}")
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("🎮 Starting OS-KEN SDN Controller on port 6655")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📡 Services Running:")
    logger.info("   - Web Interface: http://localhost:8001")
    logger.info("   - API Server: http://localhost:8080")
    logger.info("   - OpenFlow Controller: localhost:6655")
    logger.info("")
    logger.info("💬 Chat with the AI to configure your network!")
    logger.info("=" * 70)
    logger.info("")
    
    # Prepare os-ken arguments
    sys.argv = [
        'os-ken-manager',
        '--ofp-tcp-listen-port', '6655',
        controller_path,
        '--verbose'
    ]
    
    try:
        from os_ken.cmd import manager
        manager.main()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
    except Exception as e:
        logger.error(f"❌ OSKen controller failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
