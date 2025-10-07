#!/bin/bash

echo "Stopping Virtual SDN Router..."

# Kill processes
pkill -f launcher.py
pkill -f "python3 -m http.server 8000"
pkill -f os-ken-manager

# Clean up network
./scripts/cleanup_network.sh

echo "✅ SDN Router stopped"
