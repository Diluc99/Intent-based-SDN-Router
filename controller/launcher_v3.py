#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()

import sys
import threading
import time
import signal
import os
import logging
import requests
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

# Global controller reference
controller_instance = None

def wait_for_api_server(port, timeout=60):
    """Wait for API server to become available with retry logic"""
    import socket
    import time
    
    start_time = time.time()
    retry_count = 0
    max_retries = 12  # 12 attempts over 60 seconds
    
    while time.time() - start_time < timeout:
        try:
            # First check if port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                # Port is open, now check health endpoint
                time.sleep(1)  # Give it a moment to be fully ready
                response = requests.get(f'http://localhost:{port}/api/health', timeout=5)
                if response.status_code == 200:
                    return True
        except Exception as e:
            retry_count += 1
            logger.debug(f"Health check attempt {retry_count}: {e}")
        
        time.sleep(5)  # Wait 5 seconds between attempts
    
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
    
    if not groq_key or groq_key == 'your-groq-api-key-here':
        logger.error("❌ GROQ_API_KEY not configured in .env file")
        logger.error("   Get your key from: https://console.groq.com/")
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
        model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        logger.info(f"   - Using model: {model}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize conversation manager: {e}")
        logger.error("   Check if Groq API key is valid")
        sys.exit(1)
    
    # Start API server in separate thread
    api_port = 8080
    logger.info(f"🌐 Starting API server on port {api_port}...")
    api_thread = threading.Thread(
        target=api_server.run_api_server,
        args=(api_port, '0.0.0.0'),
        daemon=True,
        name="APIServerThread"
    )
    api_thread.start()

    # Wait for API server
    logger.info("   Waiting for API server to start...")
    if not wait_for_api_server(api_port, timeout=60):
        logger.error("❌ API server failed to start within 60 seconds")
        sys.exit(1)
    
    # Verify API server health
    try:
        response = requests.get(f'http://localhost:{api_port}/api/health', timeout=15)
        if response.status_code == 200:
            health = response.json()
            logger.info("✅ API server started successfully")
            logger.info(f"   - Status: {health.get('status')}")
            logger.info(f"   - LLM Enabled: {health.get('llm_enabled')}")
            logger.info(f"   - Controller Active: {health.get('controller_active')}")
        else:
            logger.error(f"❌ API server health check failed: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
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
    
    # Controller will self-register with API server when it initializes
    logger.info("🔧 Controller will auto-register when it initializes...")
    
    logger.info("=" * 70)
    logger.info("🎮 Starting OS-KEN SDN Controller on port 6653")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📡 Services Running:")
    logger.info("   - Web Interface: http://localhost:8080")
    logger.info("   - API Server: http://localhost:8080/api/")
    logger.info("   - OpenFlow Controller: 0.0.0.0:6653")
    logger.info("")
    logger.info("🔗 Connect your switch:")
    logger.info("   sudo ovs-vsctl set-controller br0 tcp:<YOUR_PC_IP>:6653")
    logger.info("")
    logger.info("💬 Chat with the AI to configure your network!")
    logger.info("   Example: 'Block gaming ports'")
    logger.info("=" * 70)
    logger.info("")
    
    # Prepare os-ken arguments
    sys.argv = [
        'os-ken-manager',
        '--ofp-tcp-listen-port', '6653',
        controller_path,
        '--verbose'
    ]
    
    try:
        # Import and start os-ken manager
        from os_ken.cmd import manager
        
        logger.info("🚀 OS-KEN manager starting...")
        manager.main()
        
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 70)
        logger.info("🛑 Received shutdown signal")
        logger.info("=" * 70)
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ OSKen controller failed: {e}")
        logger.error("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("👋 Shutdown complete")

if __name__ == '__main__':
    main()