#!/bin/bash

echo "=========================================="
echo "Starting Virtual SDN Router"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd ~/sdn-router

echo -e "${GREEN}[1/3] Setting up virtual network...${NC}"
./scripts/setup_network.sh

echo -e "${GREEN}[2/3] Starting SDN Controller...${NC}"
cd controller
source ../venv/bin/activate

# Start controller in background
python3 launcher.py > ../logs/controller.log 2>&1 &
CONTROLLER_PID=$!
echo "Controller PID: $CONTROLLER_PID"

# Wait for controller to start
sleep 3

echo -e "${GREEN}[3/3] Starting Web Interface...${NC}"
cd ../web
python3 -m http.server 8000 > ../logs/web.log 2>&1 &
WEB_PID=$!
echo "Web Server PID: $WEB_PID"

echo ""
echo -e "${GREEN}=========================================="
echo "SDN Router Started Successfully!"
echo "==========================================${NC}"
echo ""
echo "📊 Web Interface: http://localhost:8000"
echo "🔌 API Server: http://localhost:8080"
echo "🌐 Controller Port: 6654"
echo ""
echo "📝 Logs:"
echo "   Controller: ~/sdn-router/logs/controller.log"
echo "   Web: ~/sdn-router/
echo "Web: ~/sdn-router/logs/web.log"
echo ""
echo "🧪 Test Commands:"
echo "   sudo ip netns exec host1 ping 10.0.0.2"
echo "   curl http://localhost:8080/api/intents"
echo "   sudo ovs-ofctl dump-flows br0 -O OpenFlow13"
echo ""
echo "⏹️  To stop: sudo ./stop_all.sh"
echo ""
