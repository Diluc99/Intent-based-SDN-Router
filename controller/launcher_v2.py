#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()

from os_ken.cmd import manager
import sys
import threading
import time
import api_server_v2 as api_server
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting SDN Router V2 with Natural Language Processing...")
    
    # Start API server in separate thread
    api_thread = threading.Thread(target=api_server.run_api_server, args=(8080,), daemon=True)
    api_thread.start()
    
    logger.info("API server starting on port 8080...")
    time.sleep(2)
    
    # Use port 6655
    logger.info("Starting os-ken controller on port 6655...")
    sys.argv = ['os-ken-manager', '--ofp-tcp-listen-port', '6655', 'sdn_controller_v2.py', '--verbose']
    
    try:
        manager.main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()

