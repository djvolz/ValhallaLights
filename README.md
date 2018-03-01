# ValhallaLights


Light Controls for Valhalla (HQ of Rice University)

---

Lights are deployed on a Raspberry Pi with a Wolfson audio card.

##### TODO:
- Describe which wires get plugged into beagle bone GPIO (ground and like port 8, I think)
- Video of lights working at the bar
- Usage instructions
- Run table of contents generator on this file

#### Hardware in our Setup:
- Raspberry Pi
- Wolfson Audio Card for Raspberry Pi
- BeagleBone
- LED Strips WS2812B
- Korg nanoKONTROL2 USB Midi controller
- Ethernet Cable to connect Raspberry Pi and BeagleBone

#### Explanation for our Unconventional Setup:

The setup uses a Raspberry Pi and a BeagleBone because we need the Wolfson audio card for the music control in the bar, and the BeagleBone can control the lights forever even if we decide to change out the Pi later in the future.

TL;DR:  
   
   - Raspberry Pi is the brains of the operation
   
   - BeagleBone is an overpowered lightswitch 

#### Raspberry Pi Install Instructions:

1. Install the Wolfson audio kernel
    - https://github.com/CirrusLogic/rpi-linux/wiki/Building-the-code#install-the-kernel-modules-and-dtb-file-on-the-raspberry-pi


2. On your Pi, install these things:
```sh
    $ sudo apt-get install python-udev
    $ sudo apt-get install python-alsaaudio
    $ sudo apt-get install python-mutagen
    $ sudo apt-get install lame
```



#### BeagleBone Install Instructions:



valhalla-dcc.py, which runs on the Pi

valhalla-dces.c  which runs on the beaglebone (built by the Makefile)


I had to hack some stuff to make it work with our pinouts and strip lengths, but hopefully shouldn't affect anything you do.

You should know the LEDscape website, but it's here:

https://github.com/Yona-Appletree/LEDscape


Unfortunately I don't recall all the dependencies, but for the beaglebone I basically installed LEDscape to /opt/LEDscape (you may check their instructions for dependencies and such, particularly the dtb crap).  My current install is based on git revision 1c3bc60, so you should be able to do something like:

```sh
$ apt-get install build-essential ... whatever else
$ cd /opt/
$ git clone https://github.com/Yona-Appletree/LEDscape.git LEDscape
$ cd LEDscape
$ git reset --hard 1c3bc60
```
- ... copy over my Makefile and valhalla-dces.c
- add #define LEDSCAPE_NUM_STRIPS 8  and #define LEDSCAPE_NUM_PIXELS 1009 to ledscape.h  (or really to 288 or so)
- Change prus to support 8 strips, rather than 48. Line 174 of pru/templates/ replace 48 with 8.  (you don't really need to do this, just set the num_pixels above to something less than ~600)
- make

You can use netcat to emulate commands from the Pi, e.g.:

echo -ne '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' | nc -p 5252 localhost


