#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "Please run with sudo: sudo ./stop_complete.sh"
   exit 1
fi

echo "=========================================="
echo "Stopping Complete SDN Router System"
echo "=========================================="

USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_DIR="$USER_HOME/sdn-router"
LOG_DIR="$PROJECT_DIR/logs"

# Step 1: Stop Web Interface
echo ""
echo "[1/4] Stopping web interface..."
pkill -f "http.server 8001" 2>/dev/null
sleep 1
if pgrep -f "http.server 8001" > /dev/null; then
    echo "⚠️  Web interface still running — please check manually"
else
    echo "✅ Web interface stopped"
fi

# Step 2: Stop SDN Controller
echo ""
echo "[2/4] Stopping SDN Controller..."
pkill -f launcher.py 2>/dev/null
sleep 1
if pgrep -f launcher.py > /dev/null; then
    echo "⚠️  Controller still running — please check manually"
else
    echo "✅ Controller stopped"
fi

# Step 3: Teardown Virtual Network
echo ""
echo "[3/4] Tearing down virtual network..."
if [ -f "$PROJECT_DIR/scripts/teardown_network.sh" ]; then
    cd "$PROJECT_DIR/scripts"
    ./teardown_network.sh
    if [ $? -eq 0 ]; then
        echo "✅ Virtual network torn down"
    else
        echo "⚠️  Network teardown script failed"
    fi
else
    echo "ℹ️  No teardown script found — skipping"
fi

# Step 4: Summary and Cleanup
echo ""
echo "[4/4] Cleanup summary:"
echo "   Logs Directory: $LOG_DIR"
echo "   To view: tail -f $LOG_DIR/controller.log"
echo ""
echo "=========================================="
echo "🛑 SDN Router System Stopped Successfully"
echo "=========================================="
echo ""
echo "You can restart anytime using:"
echo "   sudo $PROJECT_DIR/start_complete.sh"
echo ""

