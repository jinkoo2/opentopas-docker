#!/bin/bash
# Set VNC password from VNC_PASS env var (allows override via docker-compose)
mkdir -p /root/.vnc
x11vnc -storepasswd "${VNC_PASS:-pass}" /root/.vnc/passwd

# Ensure workspace is writable by all users (host bind mount is owned by root)
mkdir -p /root/workspace
chmod 777 /root/workspace

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
