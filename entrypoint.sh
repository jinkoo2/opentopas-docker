#!/bin/bash
# Set VNC password from VNC_PASS env var (allows override via docker-compose)
mkdir -p /root/.vnc
x11vnc -storepasswd "${VNC_PASS:-pass}" /root/.vnc/passwd

# Ensure workspace is writable by all users (host bind mount is owned by root)
mkdir -p /root/workspace
chmod 777 /root/workspace

# Write code-server config with password from CODE_SERVER_PASS env var
mkdir -p /root/.config/code-server
cat > /root/.config/code-server/config.yaml <<EOF
bind-addr: 0.0.0.0:8080
auth: password
password: ${CODE_SERVER_PASS:-changeme}
cert: false
EOF

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
