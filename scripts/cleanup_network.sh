#!/bin/bash

echo "Cleaning up virtual network..."

# Delete network namespaces
sudo ip netns delete host1 2>/dev/null
sudo ip netns delete host2 2>/dev/null

# Delete Open vSwitch bridge
sudo ovs-vsctl del-br br0 2>/dev/null

echo "Cleanup complete!"
