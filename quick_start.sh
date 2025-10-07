#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "Please run with sudo"
   exit 1
fi

echo "🚀 Starting SDN Router..."

# Setup network
cd ~/sdn-router/scripts
./setup_network.sh

# Give OVS a moment
sleep 2

# Start controller in background
cd ~/sdn-router/controller
source ../venv/bin/activate
nohup python3 launcher.py > ../logs/controller.log 2>&1 &
CONTROLLER_PID=$!
echo "Controller started (PID: $CONTROLLER_PID)"

# Wait for controller to initialize
echo "Waiting for controller to start..."
sleep 5

# Check if switch connected
if grep -q "Switch connected" ~/sdn-router/logs/controller.log; then
    echo "✅ Switch connected to controller"
else
    echo "⚠️  Switch not connected yet, waiting..."
    sleep 3
fi

# Start web server
cd ~/sdn-router/web
nohup python3 -m http.server 8000 > ../logs/web.log 2>&1 &
WEB_PID=$!
echo "Web server started (PID: $WEB_PID)"

echo ""
echo "✅ SDN Router is running!"
echo ""
echo "📊 Web Interface: http://localhost:8000"
echo "🔌 API: http://localhost:8080/api/intents"
echo ""
echo "Test with: sudo ip netns exec host1 ping 10.0.0.2"
echo ""
echo "To stop: sudo pkill -f launcher.py; sudo pkill -f 'http.server 8000'"
