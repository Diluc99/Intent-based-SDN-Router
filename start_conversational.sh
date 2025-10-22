#!/bin/bash

# Exit on any error
set -e

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
    echo "Error: Please run with sudo: sudo ./start_conversational.sh"
    exit 1
fi

# Define project directory (configurable via env var or default to user's home)
USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_DIR="${PROJECT_DIR:-$USER_HOME/sdn-router}"
LOG_FILE="$PROJECT_DIR/logs/startup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log messages
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Function for cleanup on failure
cleanup() {
    log "Error occurred. Cleaning up..."
    pkill -f "launcher_v3.py" 2>/dev/null || true
    pkill -f "http.server 8001" 2>/dev/null || true
    if [ -f "$PROJECT_DIR/scripts/stop_all.sh" ]; then
        bash "$PROJECT_DIR/scripts/stop_all.sh" || log "Warning: Cleanup script failed"
    else
        ovs-vsctl del-br br0 2>/dev/null || true
        ip netns delete host1 2>/dev/null || true
        ip netns delete host2 2>/dev/null || true
        ip link delete veth1 2>/dev/null || true
        ip link delete veth2 2>/dev/null || true
    fi
    exit 1
}

# Trap errors to trigger cleanup
trap cleanup ERR

# Check dependencies
log "Checking dependencies..."
for cmd in ovs-vsctl ip curl python3; do
    command -v $cmd >/dev/null 2>&1 || { log "Error: $cmd not found. Please install it."; exit 1; }
done

# Validate project directory structure
log "Validating project directory..."
for dir in "$PROJECT_DIR/scripts" "$PROJECT_DIR/controller" "$PROJECT_DIR/web" "$PROJECT_DIR/venv"; do
    [ -d "$dir" ] || { log "Error: Directory $dir not found."; exit 1; }
done
[ -f "$PROJECT_DIR/scripts/setup_network.sh" ] || { log "Error: setup_network.sh not found."; exit 1; }
[ -f "$PROJECT_DIR/controller/launcher_v3.py" ] || { log "Error: launcher_v3.py not found."; exit 1; }
[ -f "$PROJECT_DIR/web/index_v3.html" ] || { log "Error: index_v3.html not found."; exit 1; }

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"
chown $SUDO_USER:$SUDO_USER "$PROJECT_DIR/logs"
log "Created logs directory"

# Create .env with Groq settings if missing
if [ ! -f "$PROJECT_DIR/.env" ]; then
    log "Creating default .env..."
    cat > "$PROJECT_DIR/.env" << 'ENVEOF'
GROQ_API_KEY=your-api-key-here
GROQ_MODEL=llama-3.1-70b-versatile
USE_LLM=false
MAX_CHAT_HISTORY=10
CONVERSATION_TIMEOUT=300
ENVEOF
    chown $SUDO_USER:$SUDO_USER "$PROJECT_DIR/.env"
fi

# Validate virtual environment
if [ ! -f "$PROJECT_DIR/venv/bin/activate" ]; then
    log "Error: Virtual environment not found at $PROJECT_DIR/venv"
    exit 1
fi
source "$PROJECT_DIR/venv/bin/activate"
pip show os-ken >/dev/null 2>&1 || { log "Error: os-ken not installed in venv."; exit 1; }

# Step 1: Setup Network
log "[1/4] Setting up virtual network..."
cd "$PROJECT_DIR/scripts"
if ! ./setup_network.sh >> "$LOG_FILE" 2>&1; then
    log "Error: Network setup failed. Check $LOG_FILE"
    exit 1
fi

# Step 2: Start Controller
log "[2/4] Starting Conversational AI Controller..."
cd "$PROJECT_DIR/controller"

# Kill existing controller
pkill -f "launcher_v3.py" 2>/dev/null || true
sleep 2

# Start controller
sudo -u $SUDO_USER bash -c "source $PROJECT_DIR/venv/bin/activate && nohup python3 launcher_v3.py > $PROJECT_DIR/logs/controller.log 2>&1 &"

# Wait for controller initialization
log "Waiting for controller to initialize..."
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:8080/api/health >/dev/null 2>&1; then
        log "✅ Conversational AI Controller initialized"
        break
    fi
    [ $i -eq 10 ] && { log "Error: Controller failed to start. Check $PROJECT_DIR/logs/controller.log"; exit 1; }
    log -n "."
done

# Check mode
if grep -q "LLM + Rules" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
    log "🤖 Mode: Hybrid (LLM + Rules)"
else
    log "⚡ Mode: Rule-Based Only"
    log "   (To enable LLM: Edit .env, set USE_LLM=true, and add GROQ_API_KEY)"
fi

# Wait for switch connection
log "Waiting for switch to connect..."
for i in {1..10}; do
    sleep 1
    if grep -q "Switch connected" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
        log "✅ Switch connected"
        break
    fi
    [ $i -eq 10 ] && { log "Warning: Switch not connected. Proceeding anyway..."; break; }
    log -n "."
done

# Step 3: Test Connectivity
log "[3/4] Testing network connectivity..."
if ip netns exec host1 ping -c 4 -q -W 2 10.0.0.2 >/dev/null 2>&1; then
    log "✅ Network connectivity working"
else
    log "⚠️ Network test failed. Check OVS and controller logs."
fi

# Step 4: Start Web Interface
log "[4/4] Starting conversational web interface..."
cd "$PROJECT_DIR/web"

# Kill existing web server
pkill -f "http.server 8001" 2>/dev/null || true
sleep 1

# Copy V3 interface
cp index_v3.html index.html || { log "Error: Failed to copy index_v3.html"; exit 1; }

# Start web server
sudo -u $SUDO_USER nohup python3 -m http.server 8001 > "$PROJECT_DIR/logs/web.log" 2>&1 &
sleep 2

# Verify web server
if curl -s http://localhost:8001 >/dev/null 2>&1; then
    log "✅ Web interface started"
else
    log "⚠️ Web interface may not have started. Check $PROJECT_DIR/logs/web.log"
fi

log ""
log "=========================================="
log "✅ Conversational AI SDN Router Running!"
log "=========================================="
log ""
log "💬 Chat Interface: http://localhost:8001"
log "🔌 API Server:     http://localhost:8080"
log "📊 Health Check:   curl http://localhost:8080/api/health"
log ""
log "📝 Logs:"
log "   Startup:    tail -f $PROJECT_DIR/logs/startup.log"
log "   Controller: tail -f $PROJECT_DIR/logs/controller.log"
log "   Web:        tail -f $PROJECT_DIR/logs/web.log"
log ""
log "💡 Try chatting:"
log "   Open browser and say: 'Our Zoom calls are freezing'"
log "   The assistant will ask questions and configure everything!"
log ""
log "🧪 Test via API:"
log "   curl -X POST http://localhost:8080/api/chat \\"
log "     -H 'Content-Type: application/json' \\"
log "     -d '{\"user_id\":\"test\",\"message\":\"Make video calls smooth\"}'"
log ""
log "⏹️ Stop: sudo $PROJECT_DIR/scripts/stop_all.sh"
log ""
