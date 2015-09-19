import socket

# NETWORK CONSTANTS
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
LED_IP        = "192.168.137.22"
LED_PORT      = 5252
# LED CONSTANTS
MIN_INTENSITY = 0.0
MAX_INTENSITY = 127.0
MAX_OFFSET    = 254    #maybe this should be packet max?  I believe the the beaglebone scales this up by another 4, but it needs to fit in one byte for the packet.
MAX_LENGTH      = 254
MIDI_MAX      = 127.0
DIMMER 		  = 4      #How much to dim the lights in dim mode
