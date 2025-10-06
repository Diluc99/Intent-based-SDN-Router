#!/usr/bin/env python3
from os_ken.cmd import manager
import sys
import threading
import time
from api_server import run_api_server
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting SDN Router...")
    
    # Start API server in separate thread
    api_thread = threading.Thread(target=run_api_server, args=(8080,), daemon=True)
    api_thread.start()
    
    logger.info("API server starting on port 8080...")
    time.sleep(2)
    
    # Launch os-ken controller on port 6654
    logger.info("Starting os-ken controller on port 6654...")
    sys.argv = ['os-ken-manager', '--ofp-tcp-listen-port', '6654', 'sdn_controller.py', '--verbose']
    
    try:
        manager.main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()
