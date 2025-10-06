#!/bin/bash

echo "Testing network connectivity..."

# Test ping between hosts
echo "Pinging from host1 to host2..."
sudo ip netns exec host1 ping -c 4 10.0.0.2

# Test with iperf3 (if installed)
if command -v iperf3 &> /dev/null; then
    echo "Running bandwidth test..."
    sudo ip netns exec host2 iperf3 -s &
    SERVER_PID=$!
    sleep 2
    sudo ip netns exec host1 iperf3 -c 10.0.0.2 -t 10
    kill $SERVER_PID
fi

# Check flows
echo "Checking OpenFlow flows..."
sudo ovs-ofctl dump-flows br0 -O OpenFlow13
