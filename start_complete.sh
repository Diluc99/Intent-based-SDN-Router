#!/bin/bash

# --- Main SDN startup logic below ---

if [[ $EUID -ne 0 ]]; then
   echo "Please run with sudo: sudo ./start_complete.sh"
   exit 1
fi

echo "=========================================="
echo "Starting Complete SDN Router System"
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
if [ $? -ne 0 ]; then
    echo "❌ Network setup failed"
    exit 1
fi

# Step 2: Start Controller
echo ""
echo "[2/4] Starting SDN Controller..."
cd "$PROJECT_DIR/controller"

# Kill any existing controller
pkill -f launcher.py 2>/dev/null
sleep 2

# Start as the user (not root)
sudo -u $SUDO_USER bash -c "cd $PROJECT_DIR/controller && source ../venv/bin/activate && nohup python3 launcher_v3.py > $PROJECT_DIR/logs/controller.log 2>&1 &"

echo "Waiting for controller to initialize..."
for i in {1..10}; do
    sleep 1
    if grep -q "SDN Controller initialized" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
        echo "✅ Controller initialized"
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

# Step 4: Start Web Interface
echo ""
echo "[4/4] Starting web interface..."
cd "$PROJECT_DIR/web"

# Kill any existing web server
pkill -f "http.server 8001" 2>/dev/null
sleep 1

sudo -u $SUDO_USER nohup python3 -m http.server 8001 > "$PROJECT_DIR/logs/web.log" 2>&1 &
sleep 2

if curl -s http://localhost:8001 > /dev/null 2>&1; then
    echo "✅ Web interface started"
else
    echo "⚠️  Web interface may not have started properly"
fi

echo ""
echo "=========================================="
echo "✅ SDN Router System is Running!"
echo "=========================================="
echo ""
echo "🌐 Web Interface: http://localhost:8001"
echo "🔌 API Server:    http://localhost:8080"
echo "📊 Health Check:  curl http://localhost:8080/api/health"
echo ""
echo "📝 Logs:"
echo "   Controller: tail -f $PROJECT_DIR/logs/controller.log"
echo "   Web:        tail -f $PROJECT_DIR/logs/web.log"
echo ""
echo "🧪 Test:"
echo "   sudo ip netns exec host1 ping 10.0.0.2"
echo "   sudo $PROJECT_DIR/test/comprehensive_test.sh"
echo ""
echo "⏹️  Stop: sudo $PROJECT_DIR/stop_all.sh"
echo ""

