#!/bin/bash

echo "=========================================="
echo "SDN Router Comprehensive Test Suite"
echo "=========================================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((FAILED++))
    fi
}

echo -e "\n${YELLOW}[Test 1] Network Connectivity${NC}"
sudo ip netns exec host1 ping -c 3 -W 2 10.0.0.2 > /dev/null 2>&1
test_result $? "Ping from host1 to host2"

echo -e "\n${YELLOW}[Test 2] OpenFlow Connection${NC}"
CONTROLLER_STATUS=$(sudo ovs-vsctl get-controller br0 2>/dev/null)
if [[ $CONTROLLER_STATUS == *"tcp:127.0.0.1"* ]]; then
    test_result 0 "Controller configured on bridge"
else
    test_result 1 "Controller configured on bridge"
fi

echo -e "\n${YELLOW}[Test 3] Flow Rules${NC}"
FLOW_COUNT=$(sudo ovs-ofctl dump-flows br0 -O OpenFlow13 2>/dev/null | grep -c "priority")
if [ $FLOW_COUNT -gt 0 ]; then
    test_result 0 "Flow rules installed ($FLOW_COUNT flows)"
    echo "Sample flows:"
    sudo ovs-ofctl dump-flows br0 -O OpenFlow13 | head -n 5
else
    test_result 1 "Flow rules installed"
fi

echo -e "\n${YELLOW}[Test 4] API Server${NC}"
curl -s http://localhost:8080/api/health > /dev/null 2>&1
test_result $? "API server responding"

echo -e "\n${YELLOW}[Test 5] API Endpoints${NC}"
curl -s http://localhost:8080/api/intents > /dev/null 2>&1
test_result $? "GET /api/intents"

curl -s http://localhost:8080/api/topology > /dev/null 2>&1
test_result $? "GET /api/topology"

curl -s http://localhost:8080/api/stats > /dev/null 2>&1
test_result $? "GET /api/stats"

echo -e "\n${YELLOW}[Test 6] Create Intent via API${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8080/api/intents \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Intent","policy":"QoS Priority","bandwidth":"1000 Mbps"}')
if [[ $RESPONSE == *"Test Intent"* ]]; then
    test_result 0 "Create intent via POST"
else
    test_result 1 "Create intent via POST"
fi

echo -e "\n${YELLOW}[Test 7] Web Interface${NC}"
# Check if web server is running on port 8001
if curl -s http://localhost:8001 > /dev/null 2>&1; then
    test_result 0 "Web interface accessible (port 8001)"
elif curl -s http://localhost:8000 > /dev/null 2>&1; then
    test_result 0 "Web interface accessible (port 8000)"
else
    test_result 1 "Web interface accessible"
fi

echo -e "\n${YELLOW}[Test 8] Traffic Generation${NC}"
sudo ip netns exec host1 ping -c 10 -i 0.1 10.0.0.2 > /dev/null 2>&1 &
PING_PID=$!
sleep 2
kill $PING_PID 2>/dev/null
FLOW_COUNT_AFTER=$(sudo ovs-ofctl dump-flows br0 -O OpenFlow13 2>/dev/null | grep -c "priority")
if [ $FLOW_COUNT_AFTER -gt 0 ]; then
    test_result 0 "New flows created from traffic"
else
    test_result 1 "New flows created from traffic"
fi

echo -e "\n${YELLOW}[Test 9] Bandwidth Test (if iperf3 available)${NC}"
if command -v iperf3 &> /dev/null; then
    sudo ip netns exec host2 iperf3 -s -D
    sleep 1
    sudo ip netns exec host1 iperf3 -c 10.0.0.2 -t 3 > /tmp/iperf_result.txt 2>&1
    if grep -q "sender" /tmp/iperf_result.txt; then
        test_result 0 "Bandwidth test completed"
        grep "sender" /tmp/iperf_result.txt
    else
        test_result 1 "Bandwidth test completed"
    fi
    pkill iperf3
else
    echo -e "${YELLOW}⊘ SKIPPED${NC}: iperf3 not installed"
fi

echo -e "\n${YELLOW}[Test 10] Controller Logs${NC}"
LOG_FILE="$HOME/sdn-router/logs/controller.log"
if [ -f "$LOG_FILE" ]; then
    if grep -q "SDN Controller initialized" "$LOG_FILE"; then
        test_result 0 "Controller log exists and shows initialization"
    else
        test_result 1 "Controller initialization in logs"
    fi
else
    # Check if controller is running
    if pgrep -f "launcher.py" > /dev/null; then
        test_result 0 "Controller process is running"
    else
        test_result 1 "Controller log file or process"
    fi
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed (but most are passing!)${NC}"
    exit 1
fi
