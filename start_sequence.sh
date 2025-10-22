#!/bin/bash

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $1 is already in use"
        return 1
    fi
    return 0
}

# Function to wait for a service to be ready
wait_for_service() {
    local port=$1
    local service=$2
    local max_attempts=30
    local attempt=1

    echo -n "Waiting for $service to be ready"
    while ! curl -s "http://localhost:$port" >/dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            echo "❌ $service failed to start"
            return 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo "✅ $service is ready"
    return 0
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "Please run with sudo: sudo ./start_sequence.sh"
   exit 1
fi

PROJECT_DIR=$(pwd)

# Check for required ports
check_port 8080 || exit 1
check_port 8001 || exit 1
check_port 6655 || exit 1

echo "=========================================="
echo "Starting Conversational AI SDN Router V3"
echo "=========================================="

# 1. Setup virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "[1/5] Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 2. Setup Network
echo "[2/5] Setting up virtual network..."
cd "$PROJECT_DIR/scripts"
./setup_network.sh

# 3. Start Controller
echo "[3/5] Starting SDN Controller..."
cd "$PROJECT_DIR/controller"
sudo -u $SUDO_USER bash -c "source ../venv/bin/activate && python3 launcher_v3.py > ../logs/controller.log 2>&1 &"

# Wait for controller and API
echo "[4/5] Waiting for services to be ready..."
sleep 5  # Give initial time for controller to start
wait_for_service 8080 "API Server" || exit 1

# 4. Start Web Interface
echo "[5/5] Starting web interface..."
cd "$PROJECT_DIR/web"
cp index_v3.html index.html
sudo -u $SUDO_USER python3 -m http.server 8001 > ../logs/web.log 2>&1 &

# Final check
if wait_for_service 8001 "Web Interface"; then
    echo ""
    echo "=========================================="
    echo "✅ Conversational AI SDN Router Running!"
    echo "=========================================="
    echo ""
    echo "💬 Chat Interface: http://localhost:8001"
    echo "🔌 API Server:     http://localhost:8080"
    echo ""
    echo "📝 Logs:"
    echo "   Controller: tail -f $PROJECT_DIR/logs/controller.log"
    echo "   Web:        tail -f $PROJECT_DIR/logs/web.log"
    echo ""
    echo "⏹️  Stop: sudo ./stop_all.sh"
    echo ""
else
    echo "❌ Failed to start all services"
    exit 1
fi