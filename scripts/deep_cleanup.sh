#!/bin/bash

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting deep cleanup..."

# 1. Kill any running processes
log "Stopping running processes..."
pkill -f "launcher_v3.py" || true
pkill -f "python -m http.server" || true
pkill -f "api_server" || true

# 2. Clean up network namespaces
log "Cleaning up network namespaces..."
for ns in $(ip netns list | cut -d' ' -f1); do
    log "Removing namespace: $ns"
    ip netns del $ns
done

# 3. Clean up OVS configuration
log "Cleaning up OVS configuration..."
ovs-vsctl list-br | while read -r br; do
    log "Removing bridge: $br"
    ovs-vsctl del-br "$br"
done

# 4. Remove all veth pairs
log "Cleaning up virtual interfaces..."
for veth in $(ip link show | grep veth | cut -d: -f2 | cut -d@ -f1); do
    log "Removing interface: $veth"
    ip link delete "$veth" 2>/dev/null || true
done

# 5. Reset OVS system configuration
log "Resetting OVS system..."
systemctl stop openvswitch-switch
sleep 2
rm -rf /var/run/openvswitch/*
rm -rf /etc/openvswitch/conf.db
systemctl start openvswitch-switch
sleep 5  # Give OVS time to initialize
ovs-vsctl show || log "Waiting for OVS to initialize..."
for i in {1..5}; do
    if ovs-vsctl show >/dev/null 2>&1; then
        log "OVS initialized successfully"
        break
    fi
    sleep 2
done

# 6. Clear iptables
log "Clearing iptables rules..."
iptables -F
iptables -t nat -F

# 7. Reset sysctl values
log "Resetting sysctl values..."
sysctl net.ipv4.ip_forward=0

# 8. Clean up any stale sockets
log "Cleaning up stale sockets..."
rm -f /var/run/openvswitch/db.sock
rm -f /var/run/openvswitch/br0.mgmt

# 9. Verify cleanup
log "Verifying cleanup..."
ip netns list
ip link show | grep veth
ovs-vsctl show

log "Cleanup complete!"