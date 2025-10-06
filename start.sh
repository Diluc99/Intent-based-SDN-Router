#!/bin/bash

echo "Starting Virtual SDN Router..."

# Activate virtual environment
source venv/bin/activate

# Setup network
./scripts/setup_network.sh

# Start controller
cd controller
python3 launcher.py
