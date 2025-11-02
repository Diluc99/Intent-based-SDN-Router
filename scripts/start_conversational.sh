#!/bin/bash

# Exit on any error
set -e

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
    echo "Error: Please run with sudo: sudo ./start_conversational.sh"
    exit 1
fi

# Define project directory
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
    fi
    exit 1
}

# Trap errors
trap cleanup ERR

# Check dependencies
log "Checking dependencies..."
for cmd in ovs-vsctl ip curl python3; do
    command -v $cmd >/dev/null 2>&1 || { log "Error: $cmd not found. Please install it."; exit 1; }
done

# Validate project directory
log "Validating project directory..."
[ -d "$PROJECT_DIR/controller" ] || { log "Error: controller directory not found."; exit 1; }
[ -f "$PROJECT_DIR/controller/launcher_v3.py" ] || { log "Error: launcher_v3.py not found."; exit 1; }

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"
chown $SUDO_USER:$SUDO_USER "$PROJECT_DIR/logs"
log "Created logs directory"

# Validate virtual environment
if [ ! -f "$PROJECT_DIR/venv/bin/activate" ]; then
    log "Error: Virtual environment not found at $PROJECT_DIR/venv"
    exit 1
fi

# Apply critical fixes before starting
log "Applying critical fixes..."

# Fix 1: Update sdn_controller_v2.py to extract ports from intent names
if ! grep -q "Extracted port from name" "$PROJECT_DIR/controller/sdn_controller_v2.py" 2>/dev/null; then
    log "  → Patching sdn_controller_v2.py to extract ports from intent names..."
    
    # Backup
    cp "$PROJECT_DIR/controller/sdn_controller_v2.py" "$PROJECT_DIR/controller/sdn_controller_v2.py.backup_$(date +%s)"
    
    # Add port extraction logic to apply_intent method
    python3 << 'PYPATCH'
import re

with open("$PROJECT_DIR/controller/sdn_controller_v2.py", "r") as f:
    content = f.read()

# Find apply_intent method and add port extraction
if "# Extract intent parameters" in content:
    # Add port extraction after "Extract intent parameters"
    old_section = """    # Extract intent parameters
    policy = intent_data.get('policy', 'custom')
    action = intent_data.get('action', 'allow')
    priority = intent_data.get('priority', 50)
    protocol = intent_data.get('protocol', 'tcp')
    ports = intent_data.get('ports', '')"""
    
    new_section = """    # Extract intent parameters
    policy = intent_data.get('policy', 'custom')
    action = intent_data.get('action', 'allow')
    priority = intent_data.get('priority', 50)
    protocol = intent_data.get('protocol', 'tcp')
    
    # NEW: Extract port from name if not in ports field
    ports = intent_data.get('ports', '')
    if not ports:
        # Try to extract port from name (e.g., "Block UDP 27015")
        import re
        name = intent_data.get('name', '')
        port_match = re.search(r'\b(\d{1,5})\b', name)
        if port_match:
            ports = port_match.group(1)
            logger.info(f"📍 Extracted port from name: {ports}")"""
    
    content = content.replace(old_section, new_section)
    
    with open("$PROJECT_DIR/controller/sdn_controller_v2.py", "w") as f:
        f.write(content)
PYPATCH
    
    log "  ✅ sdn_controller_v2.py patched"
else
    log "  ✅ sdn_controller_v2.py already patched"
fi

# Fix 2: Update api_server_v3.py to pass intent correctly
if grep -q "controller.apply_intent(intent_id, intent_to_apply)" "$PROJECT_DIR/controller/api_server_v3.py" 2>/dev/null; then
    log "  → Patching api_server_v3.py to pass intent correctly..."
    
    # Backup
    cp "$PROJECT_DIR/controller/api_server_v3.py" "$PROJECT_DIR/controller/api_server_v3.py.backup_$(date +%s)"
    
    # Fix the intent application call
    sed -i 's/success = controller.apply_intent(intent_id, intent_to_apply)/success = controller.apply_intent(intent_data)/' "$PROJECT_DIR/controller/api_server_v3.py"
    
    # Also remove the intent_to_apply wrapper
    sed -i '/intent_to_apply = {/,/}/d' "$PROJECT_DIR/controller/api_server_v3.py"
    
    log "  ✅ api_server_v3.py patched"
else
    log "  ✅ api_server_v3.py already patched"
fi

log "✅ All critical fixes applied"

# Setup Network (if script exists)
if [ -f "$PROJECT_DIR/scripts/setup_network.sh" ]; then
    log "[1/3] Setting up virtual network..."
    cd "$PROJECT_DIR/scripts"
    if ! ./setup_network.sh >> "$LOG_FILE" 2>&1; then
        log "⚠️ Network setup failed (may already be configured)"
    fi
else
    log "[1/3] Skipping network setup (setup_network.sh not found)"
fi

# Start Controller
log "[2/3] Starting Conversational AI Controller..."
cd "$PROJECT_DIR/controller"

# Kill existing controller
pkill -f "launcher_v3.py" 2>/dev/null || true
sleep 2

# Start controller as regular user with venv
sudo -u $SUDO_USER bash -c "source $PROJECT_DIR/venv/bin/activate && nohup python3 launcher_v3.py > $PROJECT_DIR/logs/controller.log 2>&1 &"

# Wait for controller initialization
log "Waiting for controller to initialize..."
for i in {1..15}; do
    sleep 1
    if curl -s http://localhost:8080/api/health >/dev/null 2>&1; then
        log "✅ Controller initialized"
        break
    fi
    if [ $i -eq 15 ]; then
        log "❌ Controller failed to start. Check $PROJECT_DIR/logs/controller.log"
        tail -20 "$PROJECT_DIR/logs/controller.log"
        exit 1
    fi
done

# Check LLM mode
if grep -q "LLM Mode: True" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
    log "🤖 Mode: LLM-Only (Groq AI Active)"
elif grep -q "LLM + Rules" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
    log "🤖 Mode: Hybrid (LLM + Rules)"
else
    log "⚡ Mode: Rule-Based Only"
fi

# Wait for switch connection
log "Waiting for switches to connect..."
for i in {1..15}; do
    sleep 1
    if grep -q "Switch connected" "$PROJECT_DIR/logs/controller.log" 2>/dev/null; then
        SWITCH_COUNT=$(grep -c "Switch connected" "$PROJECT_DIR/logs/controller.log" 2>/dev/null || echo 0)
        log "✅ $SWITCH_COUNT switch(es) connected"
        break
    fi
    if [ $i -eq 15 ]; then
        log "⚠️ No switches connected yet (they can connect later)"
    fi
done

# Start Web Interface
log "[3/3] Starting web interface..."

# Use index.html if it exists, otherwise skip
if [ -f "$PROJECT_DIR/web/index.html" ]; then
    cd "$PROJECT_DIR/web"
    
    # Kill existing web server
    pkill -f "http.server 8001" 2>/dev/null || true
    sleep 1
    
    # Start web server
    sudo -u $SUDO_USER nohup python3 -m http.server 8001 > "$PROJECT_DIR/logs/web.log" 2>&1 &
    sleep 2
    
    if curl -s http://localhost:8001 >/dev/null 2>&1; then
        log "✅ Web interface started"
    else
        log "⚠️ Web interface failed to start"
    fi
else
    log "⚠️ Web interface not found (continuing without it)"
fi

log ""
log "=========================================="
log "✅ Conversational AI SDN Router Running!"
log "=========================================="
log ""
log "💬 Web Interface:  http://localhost:8080"
log "🔌 API Server:     http://localhost:8080/api/"
log "📊 Health Check:   curl http://localhost:8080/api/health"
log ""
log "📝 Logs:"
log "   Controller: tail -f $PROJECT_DIR/logs/controller.log"
log "   Startup:    tail -f $PROJECT_DIR/logs/startup.log"
log ""
log "💡 Try chatting in browser:"
log "   Open http://localhost:8080 and say: 'block port 27015'"
log ""
log "🧪 Test via API:"
log "   curl -X POST http://localhost:8080/api/chat \\"
log "     -H 'Content-Type: application/json' \\"
log "     -d '{\"user_id\":\"test\",\"message\":\"block gaming ports\"}'"
log ""
log "🔗 Connect your Raspberry Pi switch:"
log "   sudo ovs-vsctl set-controller br0 tcp:$(hostname -I | awk '{print $1}'):6653"
log ""
log "⏹️ Stop: sudo pkill -f launcher_v3.py"
log ""
