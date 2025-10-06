#!/bin/bash

echo "Setting up virtual SDN network..."

# Create Open vSwitch bridge
sudo ovs-vsctl add-br br0
sudo ovs-vsctl set bridge br0 protocols=OpenFlow13

# Set controller
sudo ovs-vsctl set-controller br0 tcp:127.0.0.1:6653

# Create network namespaces for testing
sudo ip netns add host1
sudo ip netns add host2

# Create veth pairs
sudo ip link add veth1 type veth peer name veth1-br
sudo ip link add veth2 type veth peer name veth2-br

# Move veth ends to namespaces
sudo ip link set veth1 netns host1
sudo ip link set veth2 netns host2

# Attach veth pairs to bridge
sudo ovs-vsctl add-port br0 veth1-br
sudo ovs-vsctl add-port br0 veth2-br

# Configure interfaces in namespaces
sudo ip netns exec host1 ip addr add 10.0.0.1/24 dev veth1
sudo ip netns exec host1 ip link set veth1 up
sudo ip netns exec host1 ip link set lo up

sudo ip netns exec host2 ip addr add 10.0.0.2/24 dev veth2
sudo ip netns exec host2 ip link set veth2 up
sudo ip netns exec host2 ip link set lo up

# Bring up bridge ports
sudo ip link set veth1-br up
sudo ip link set veth2-br up
sudo ip link set br0 up

echo "Virtual network setup complete!"
echo "Test with: sudo ip netns exec host1 ping 10.0.0.2"
