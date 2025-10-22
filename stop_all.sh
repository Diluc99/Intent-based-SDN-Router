#!/bin/bash

  # Exit on any error
  set -e

  # Define project directory (configurable via env var or default to user's home)
  USER_HOME=$(eval echo ~$SUDO_USER)
  PROJECT_DIR="${PROJECT_DIR:-$USER_HOME/sdn-router}"
  LOG_FILE="$PROJECT_DIR/logs/stop_all.log"
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  # Function to log messages
  log() {
      echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
  }

  # Check for root privileges
  if [[ $EUID -ne 0 ]]; then
      echo "Error: Please run with sudo: sudo ./stop_all.sh"
      exit 1
  fi

  # Create logs directory if missing
  mkdir -p "$PROJECT_DIR/logs"
  chown $SUDO_USER:$SUDO_USER "$PROJECT_DIR/logs"
  log "Starting cleanup process..."

  # Stop controller process
  log "Stopping controller (launcher_v3.py)..."
  pkill -f "launcher_v3.py" 2>/dev/null && log "✅ Controller stopped" || log "No controller process found"

  # Stop web server
  log "Stopping web server (http.server 8001)..."
  pkill -f "http.server 8001" 2>/dev/null && log "✅ Web server stopped" || log "No web server process found"

  # Clean up OVS bridge
  log "Removing OVS bridge (br0)..."
  ovs-vsctl --if-exists del-br br0 2>/dev/null && log "✅ OVS bridge br0 deleted" || log "No OVS bridge br0 found"

  # Clean up network namespaces
  log "Removing network namespaces (host1, host2)..."
  ip netns delete host1 2>/dev/null && log "✅ Namespace host1 deleted" || log "No namespace host1 found"
  ip netns delete host2 2>/dev/null && log "✅ Namespace host2 deleted" || log "No namespace host2 found"

  # Clean up virtual interfaces
  log "Removing virtual interfaces (veth1, veth2)..."
  ip link delete veth1 2>/dev/null && log "✅ Interface veth1 deleted" || log "No interface veth1 found"
  ip link delete veth2 2>/dev/null && log "✅ Interface veth2 deleted" || log "No interface veth2 found"

  log ""
  log "=========================================="
  log "✅ Cleanup complete"
  log "=========================================="
  log "Logs available at: $LOG_FILE"
