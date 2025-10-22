#!/bin/bash

# This will add a topology viewer button to the header
sed -i 's|<button onclick="window.location.href.*Dashboard.*|<button onclick="window.location.href='"'"'topology.html'"'"'" class="bg-cyan-500 hover:bg-cyan-600 px-4 py-2 rounded">Network Topology</button>|' index.html

echo "Updated index.html with topology link"
