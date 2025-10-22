#!/bin/bash

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Initializing Open vSwitch..."

# Stop OVS services and kill any remaining processes
log "Stopping OVS services..."
sudo service openvswitch-switch stop
sudo killall ovsdb-server ovs-vswitchd 2>/dev/null || true
sleep 2

# Clean up old files including lock files
log "Cleaning up old OVS files..."
sudo rm -rf /var/run/openvswitch/*
sudo rm -rf /etc/openvswitch/conf.db*
sudo rm -rf /etc/openvswitch/.conf.db*
sudo rm -rf /var/log/openvswitch/*

# Create necessary directories with proper permissions
log "Creating directories..."
sudo mkdir -p /var/run/openvswitch
sudo mkdir -p /etc/openvswitch
sudo chmod 755 /var/run/openvswitch
sudo chmod 755 /etc/openvswitch

# Initialize OVS database
log "Initializing OVS database..."
sudo ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
sudo chmod 640 /etc/openvswitch/conf.db

# Start OVS database service
log "Starting OVS database service..."
sudo ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
                  --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
                  --pidfile=/var/run/openvswitch/ovsdb-server.pid \
                  --detach --log-file

# Wait a moment for the database to be ready
sleep 2

# Start OVS daemon
log "Starting OVS daemon..."
sudo ovs-vswitchd --pidfile=/var/run/openvswitch/ovs-vswitchd.pid \
                  --detach --log-file

# Restart the service to ensure everything is properly initialized
log "Restarting OVS service..."
sudo service openvswitch-switch restart
sleep 2

# Wait for OVS to be ready
log "Waiting for OVS to be ready..."
for i in {1..30}; do
    if sudo ovs-vsctl show >/dev/null 2>&1; then
        log "✅ OVS is ready!"
        exit 0
    fi
    sleep 1
    echo -n "."
done

log "❌ Failed to initialize OVS"
exit 1