#!/bin/bash
# Set VNC password from VNC_PASS env var (allows override via docker-compose)
mkdir -p /root/.vnc
x11vnc -storepasswd "${VNC_PASS:-pass}" /root/.vnc/passwd

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
