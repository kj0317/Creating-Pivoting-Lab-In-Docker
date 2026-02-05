#!/bin/bash

# Start SSH daemon in the background
/usr/sbin/sshd

# Start the vulnerable web application in the foreground
# (keeps the container running)
echo "[*] Starting NetDiag web service on port 5000..."
python3 /opt/webapp/app.py
