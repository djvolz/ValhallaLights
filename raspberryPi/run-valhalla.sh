#!/bin/bash

while true; do
	python /home/pi/valhalla/ValhallaLights/raspberryPi/valhalla-dcc-music.py
done

#put this in your crontab as root (sudo crontab -e)
#@reboot /home/argos/valhalla/ValhallaLights/raspberryPi/run-valhalla.sh
