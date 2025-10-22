#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "Please run with sudo: sudo ./start_v2.sh"
   exit 1
fi

echo "=========================================="
echo "Starting AI-Powered SDN Router V2"
echo "=========================================="

USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_DIR="$USER_HOME/sdn-router"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"
chown $SUDO_USER:$SUDO_USER "$PROJECT_DIR/logs"

# Step 1: Setup Network
echo ""
echo "[1/4] Setting up virtual network..."
cd "$PROJECT_DIR/scripts"
./setup_network.sh

# Step 2: Start Controller V2
echo ""
echo "[2/4] Starting AI-Powered SDN Controller..."
cd "$PROJECT_DIR/controller"

# Kill any existing controller
pkill -f launcher 2>/dev/null
sleep 2

# Start V2 controller
sudo -u $SUDO_USER bash -c "cd $PROJECT_DIR/controller && source ../venv/bin/activate && nohup python3 launcher_v2.py > $PROJECT_DIR/logs/controller.log 2>&1 &"

echo "Waiting for controller to initialize..."
for i in {1..10}; do
    sleep 1
    if grep -q "SDN Controller V2 initialized" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
        echo "✅ AI Controller initialized"
        break
    fi
    echo -n "."
done
echo ""

# Wait for switch connection
echo "Waiting for switch to connect..."
for i in {1..10}; do
    sleep 1
    if grep -q "Switch connected" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
        echo "✅ Switch connected"
        break
    fi
    echo -n "."
done
echo ""

# Step 3: Test Connectivity
echo ""
echo "[3/4] Testing network connectivity..."
if ip netns exec host1 ping -c 2 -W 2 10.0.0.2 > /dev/null 2>&1; then
    echo "✅ Network connectivity working"
else
    echo "⚠️  Network test failed"
fi

# Step 4: Start Web Interface V2
echo ""
echo "[4/4] Starting AI-powered web interface..."
cd "$PROJECT_DIR/web"

# Kill any existing web server
pkill -f "http.server 8001" 2>/dev/null
sleep 1

# Copy V2 interface to default
cp index_v2.html index.html

sudo -u $SUDO_USER nohup python3 -m http.server 8001 > "$PROJECT_DIR/logs/web.log" 2>&1 &
sleep 2

if curl -s http://localhost:8001 > /dev/null 2>&1; then
    echo "✅ Web interface started"
else
    echo "⚠️  Web interface may not have started properly"
fi

echo ""
echo "=========================================="
echo "✅ AI-Powered SDN Router is Running!"
echo "=========================================="
echo ""
echo "🤖 Natural Language Interface: http://localhost:8001"
echo "🔌 API Server:    http://localhost:8080"
echo "📊 Health Check:  curl http://localhost:8080/api/health"
echo ""
echo "📝 Logs:"
echo "   Controller: tail -f $PROJECT_DIR/logs/controller.log"
echo "   Web:        tail -f $PROJECT_DIR/logs/web.log"
echo ""
echo "🧪 Try natural language:"
echo '   curl -X POST http://localhost:8080/api/intents/natural \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"input":"Make video streaming fast"}'"'"
echo ""
echo "⏹️  Stop: sudo ./stop_all.sh"
echo ""
