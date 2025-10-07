#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

SDN_DIR="$HOME/sdn-router"

cat > /etc/systemd/system/sdn-router.service << EOF
[Unit]
Description=Virtual SDN Router Controller
After=network.target openvswitch-switch.service
Requires=openvswitch-switch.service

[Service]
Type=simple
User=root
WorkingDirectory=$SDN_DIR/controller
Environment="PATH=$SDN_DIR/venv/bin:/usr/bin"
ExecStartPre=$SDN_DIR/scripts/setup_network.sh
ExecStart=$SDN_DIR/venv/bin/python3 $SDN_DIR/controller/launcher.py
ExecStop=$SDN_DIR/scripts/cleanup_network.sh
Restart=on-failure
RestartSec=10
StandardOutput=append:$SDN_DIR/logs/controller.log
StandardError=append:$SDN_DIR/logs/controller.log

[Install]
WantedBy=multi-user.target
EOF

# Web service
cat > /etc/systemd/system/sdn-web.service << EOF
[Unit]
Description=SDN Router Web Interface
After=sdn-router.service

[Service]
Type=simple
User=root
WorkingDirectory=$SDN_DIR/web
ExecStart=/usr/bin/python3 -m http.server 8000
Restart=on-failure
StandardOutput=append:$SDN_DIR/logs/web.log
StandardError=append:$SDN_DIR/logs/web.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo "✅ Systemd services installed"
echo ""
echo "Enable and start with:"
echo "  sudo systemctl enable sdn-router sdn-web"
echo "  sudo systemctl start sdn-router sdn-web"
echo ""
echo "Check status:"
echo "  sudo systemctl status sdn-router"
echo "  sudo systemctl status sdn-web"
