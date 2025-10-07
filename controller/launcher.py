#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()

from os_ken.cmd import manager
import sys
import threading
import time
from api_server import run_api_server, set_controller
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global to store controller reference
controller_instance = None

def get_controller():
    """Wait for controller to be initialized"""
    max_wait = 30  # Wait up to 30 seconds
    waited = 0
    while controller_instance is None and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
    return controller_instance

def main():
    logger.info("Starting SDN Router...")
    
    # Start API server in separate thread
    api_thread = threading.Thread(target=run_api_server, args=(8080,), daemon=True)
    api_thread.start()
    
    logger.info("API server starting on port 8080...")
    time.sleep(2)
    
    # Use port 6655
    logger.info("Starting os-ken controller on port 6655...")
    sys.argv = ['os-ken-manager', '--ofp-tcp-listen-port', '6655', 'sdn_controller.py', '--verbose']
    
    try:
        manager.main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()
