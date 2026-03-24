docker run -d \
  --name ubuntu-desktop \
  -p 6080:80 \
  -e USER=root \
  -e PASSWORD=pass \
  --shm-size="2g" \
  dorowu/ubuntu-desktop-lxde-vnc