#!/bin/bash
echo "=========================================="
echo "Setting up Virtual SDN Network"
echo "=========================================="

# Clean up existing setup
echo "Cleaning up old configuration..."
ovs-vsctl del-br br0 2>/dev/null || true
ip netns delete host1 2>/dev/null || true
ip netns delete host2 2>/dev/null || true
ip link delete veth1 2>/dev/null || true
ip link delete veth2 2>/dev/null || true

# Create Open vSwitch bridge
echo "Creating OVS bridge..."
ovs-vsctl add-br br0
ovs-vsctl set bridge br0 protocols=OpenFlow13

# Set controller (port 6655)
echo "Connecting to controller on port 6655..."
ovs-vsctl set-controller br0 tcp:127.0.0.1:6655

# Create network namespaces
echo "Creating network namespaces..."
ip netns add host1
ip netns add host2

# Create veth pairs
echo "Creating virtual interfaces..."
ip link add veth1 type veth peer name veth1-br
ip link add veth2 type veth peer name veth2-br

# Move veth ends to namespaces
ip link set veth1 netns host1
ip link set veth2 netns host2

# Attach to bridge
ovs-vsctl add-port br0 veth1-br
ovs-vsctl add-port br0 veth2-br

# Configure interfaces in namespaces
echo "Configuring network interfaces..."
ip netns exec host1 ip addr add 10.0.0.1/24 dev veth1
ip netns exec host1 ip link set veth1 up
ip netns exec host1 ip link set lo up

ip netns exec host2 ip addr add 10.0.0.2/24 dev veth2
ip netns exec host2 ip link set veth2 up
ip netns exec host2 ip link set lo up

# Bring up bridge ports
ip link set veth1-br up
ip link set veth2-br up
ip link set br0 up

echo ""
echo "=========================================="
echo "✅ Network Setup Complete"
echo "=========================================="
echo ""
ovs-vsctl show
echo ""
echo "Network namespaces:"
ip netns list
echo ""
echo "Test with: sudo ip netns exec host1 ping 10.0.0.2"
