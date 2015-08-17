# Valhalla Dual Color Client (DCC)
# Read MIDI controller sliders and send 16 byte UDP packets to the Valhalla Dual Color Server to update LEDs.

import os, sys
import pygame
import pygame.midi
import pygame.fastevent
import array
import ctypes
import math
from os import popen
from array import array
from pygame.locals import *
import socket
import struct

from pyudev import Context, Monitor
import pyudev
import thread

from pygame import mixer # Load the required library

import stabilize
import audio_setup
import korg_midi_reader as korg
from library.music import calculate_levels, read_musicfile_in_chunks


#try:
#	from pyudev.glib import MonitorObserver
#except:
#	from pyudev.glib import GUDevMonitorObserver as MonitorObserver

#todo: use pyudev to detect disconnect of the midi controller so we can reconnect.


#WARNING! You must download the korg driver and configuration software and set the LED control to "external" for the set lighting to work!!!

# NANOKontrol Magic Values:
# 0x00 - 0x07: sliders
# 0x10 - 0x17: knobs
# 0x20 - 0x27: S buttons
# 0x30 - 0x37: M buttons
# 0x40 - 0x47: R buttons

#TODO: third color needs to be scaled

#TODO: fix find nanokontrol and fix setting IP and Port above...
#TODO: add sound recording and sending to a different port #this looks like a good starting point: http://people.csail.mit.edu/hubert/pyaudio/docs/ #http://stackoverflow.com/questions/18406570/python-record-audio-on-detected-sound	#http://stackoverflow.com/questions/892199/detect-record-audio-in-python/892293#892293 #http://stackoverflow.com/questions/1797631/recognising-tone-of-the-audio #https://docs.python.org/2/library/audioop.html #https://wiki.python.org/moin/PythonInMusic #http://www.codeproject.com/Articles/32172/FFT-Guitar-Tuner #http://stackoverflow.com/questions/19079429/using-pyaudio-libraries-in-python-linux (select input)
#TODO: add multiple "strips" or "domains"?
#TODO: fix button up and button down mode trigger!



class Constants:
	# NETWORK CONSTANTS
	SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	LED_IP			 = "10.0.1.13" #"192.168.137.22"
	LED_PORT		 = 5252
	# LED CONSTANTS
	MIN_INTENSITY	 = 0.0
	MAX_INTENSITY	 = 127.0

class MIDI:
	mode  = 0
	rgb = [x[:] for x in [[0]*3]*3] #I really hate python sometimes...
	buttons = {'scale': 	 		   False,
			   'music_mode_intensity': False,
			   'music_mode_offset':    False,
			   'pulse': 			   False,
			   'rotate': 	 		   False,
			   'sway':				   False,
			   'red':				   False,
			   'green':				   False,
			   'blue':				   False
			   }

	def __init__(self):
		audio_setup.init_audio()
		self.midi_reader = korg.KorgMidiReader()

	def read_events(self):
		self.read_buttons()
		self.read_settings()
		self.read_rgb()
		self.read_scale()
		return self.midi_reader.read_events()

	def read_rgb(self):
		# translate the slider data into rgb values for packet
		self.rgb[0]    = [int(item) for item in self.midi_reader.sliders[2:5]]
		self.rgb[1]    = [int(item) for item in self.midi_reader.sliders[5:8]]
		
		# check the first three knobs for third color if the button is enabled
		if self.buttons['third_color']:
			for i in range(3):
				self.rgb[2][i] = self.midi_reader.knobs[i]
		# if button isn't pressed, no third color. knobs[0-2] go unused
		else:
			self.rgb[2] = [0]*3




	def read_settings(self):
		self.settings = {'red':     self.midi_reader.knobs[0],
						 'green':     self.midi_reader.knobs[1],
						 'blue':     self.midi_reader.knobs[2],
						 'UNUSED3':     self.midi_reader.knobs[3],
						 'offset':      self.midi_reader.knobs[4],
						 'sway_speed':  self.midi_reader.knobs[5],
						 'minimum':     self.midi_reader.knobs[6],
						 'pulse_speed': self.midi_reader.knobs[7],

						 'length':      self.midi_reader.sliders[0],
						 'gradient':    self.midi_reader.sliders[1],
						 }
	def read_buttons(self):
		self.buttons = {'scale': 	 		    self.midi_reader.buttons[5][0],
						'music_mode_intensity': self.midi_reader.buttons[5][1],
						'music_mode_offset':    self.midi_reader.buttons[5][2],
						'pulse': 			    self.midi_reader.buttons[7][0],
						'rotate': 	 		    self.midi_reader.buttons[7][1],
						'sway':				    self.midi_reader.buttons[7][2],
						'third_color':			self.midi_reader.buttons[6][0],
						}

		audio_setup.update_frequency_limits_with_columns(3 if self.buttons['third_color'] else 2)
		self.mode = self.get_mode()

	#define MODE_STATIC		0
	#define MODE_PULSING	1
	#define MODE_ROTATING	2
	#define MODE_SWAYING	4
	#define MODE_THIRDCOLOR 8  //three colors or two colors...
	def get_mode(self):
		return abs( (self.buttons['pulse']) + (self.buttons['rotate'] << 1) + (self.buttons['sway'] << 2)) + abs(self.buttons['third_color']  << 3)   #why is this negative!??!

	def read_scale(self):
		if self.buttons['scale']:
			self.scale = 4
		else:
			self.scale = 1






class LEDMusicController:

	def __init__(self):
		audio_setup.init_audio()
		self.midi = MIDI()


	# Analyze the audio input and turn it into light (aka magic)
	def analyze_line_in(self):
		input = audio_setup.get_audio_input()
		while True:
			self.control_midi()
			if self.midi.buttons['music_mode_intensity'] or self.midi.buttons['music_mode_offset'] :
				size, chunk = input.read()
				if size > 0:
					# Make the chunk even length if it isn't already
					L = (len(chunk)/2 * 2)
					chunk = chunk[:L]

					# Calculate the levels
					data = calculate_levels(chunk, audio_setup.Constants.SAMPLE_RATE, audio_setup.Constants.FREQUENCY_LIMITS)

					# Interpret the data
					self.convert_data_to_packet(data)
			else:
				# waste time so that we don't eat too much CPU
				pygame.time.wait(1)



	# Turn a local audio file into light (aka magic)
	def analyze_audio_file_local(self, path):
		print "path = " + path

		for chunk, sample_rate in read_musicfile_in_chunks(path, play_audio=False):
			data = calculate_levels(chunk, sample_rate, audio_setup.Constants.FREQUENCY_LIMITS)
			self.convert_data_to_packet(data)
			self.control_midi()


	def create_packet(self):
		# Packet structure (received by beaglebone)
		#  0: mode
		#  1: length
		#  2: gradient
		#  3: offset
		#  4: sway_speed
		#  5: minimum
		#  6: pulse_speed
		#  7: b
		#  8: r
		#  9: g
		# 10: b
		# 11: r
		# 12: g
		# 13: b
		# 14: r
		# 15: g

		# mode
		packet = [int(self.midi.mode)]

		# settings
		packet.extend([int(self.midi.settings['length'])])
		packet.extend([int(self.midi.settings['gradient'])])
		packet.extend([int(self.midi.settings['offset'])])
		packet.extend([int(self.midi.settings['sway_speed'])])
		packet.extend([int(self.midi.settings['minimum'])])
		packet.extend([int(self.midi.settings['pulse_speed'])])

		# rgb, rgb, rgb
		packet.extend([int(item/self.midi.scale) for sublist in self.midi.rgb for item in sublist])
		return packet


	# Stuff the packet and send it out over the network.
	def update_lights(self):
		try:
			packet = self.create_packet()
			Constants.SOCK.sendto(struct.pack('B' * len(packet),*packet),(Constants.LED_IP, Constants.LED_PORT))
		except Exception as e:
			print("Exception in update_lights")
			print(e)


	def control_midi(self):
		if self.midi.read_events():
			# update the lights with the new settings
			self.update_lights()

	def convert_data_to_packet(self, matrix):
		# Dynamically update the possible light intensity range
		stabilize.stabilize_light_intensities()

		converted_matrix = [0] * len(matrix)

		for col in range(len(matrix)):
			# check the current possible intensity min and max
			val, lights_range = stabilize.check_if_val_within_range(matrix[col])

			# Map the light values to be within the range of the MIDI light intensities
			converted_matrix[col] = stabilize.scale(val, (lights_range.min_intensity, lights_range.max_intensity), (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY))

		# Music Mode INTENSITY
		if self.midi.buttons['music_mode_intensity']:
			rgb = [x[:] for x in [[0]*3]*3]

			# Scale the MIDI value to be within the slider ranges
			for i in range(len(converted_matrix)):
				for j in range(len(self.midi.rgb[i])):
					rgb[i][j] = stabilize.scale(converted_matrix[i], (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY), (int(self.midi.settings['minimum']/Constants.MAX_INTENSITY * self.midi.rgb[i][j]), self.midi.rgb[i][j]))
					#print("knob %d %d" % (self.midi.midi_reader.knobs[6], int(self.midi.midi_reader.knobs[6]/254. * self.midi.midi_reader.rgb[i][j])))

			# update lights with new intensities
			self.midi.rgb = rgb
			self.update_lights()

		# Music Mode OFFSET
		if self.midi.buttons['music_mode_offset']:
			# map between minimum and offset
			offset = stabilize.scale(converted_matrix[0], (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY), (int(self.midi.settings['minimum']/Constants.MAX_INTENSITY * self.midi.settings['offset']), self.midi.settings['offset']))
			self.midi.settings['offset'] = offset

			# update lights with new offset
			self.update_lights()




	#ugly... volume is 0-Constants.MAX_INTENSITY, balance is 0-254
	def set_volume(self, volume, balance):
		#currently the balance is stored in knobs of 1... we can just keep it there... (note its scaled up to 254)
		#we want it where if it's centered (with some hysteresis) then both volumes are at 100%, then they fade from there.
		if balance > 120:
			volumel = 22 * volume/Constants.MAX_INTENSITY
		else:
			volumel = 22 * balance/Constants.MAX_INTENSITY * volume/Constants.MAX_INTENSITY

		if balance < 134:
			volumer = 33 * volume/Constants.MAX_INTENSITY
		else:
			volumer = 33 * (1-(254-balance)/Constants.MAX_INTENSITY) * volume/Constants.MAX_INTENSITY

		print([volumel, volumer])
		#would this be any faster?
		#os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1 Volume' " + str(volumer) + "; amixer -Dhw:0 cset name='HPOUT1R Input 1 Volume' " + str(volumer))
			

	def MainLoop(self):
		# Play local file if song path is given as argument
		if len(sys.argv) > 1:
			# # initial settings
			# self.midi.settings['length']              = 10
			# self.midi.settings['gradient']            = 0
			# self.midi.settings['offset'  ]            = Constants.MAX_INTENSITY
			# self.midi.settings['minimum' ]            = 0
			# self.midi.rgb[0][0]                    = Constants.MAX_INTENSITY
			# self.midi.rgb[1][2]                    = Constants.MAX_INTENSITY
			# self.midi.buttons['music_mode_offset'] = True
			path = sys.argv[1]
			self.analyze_audio_file_local(path)

		self.analyze_line_in()


if __name__ == '__main__':
	
	lmc = LEDMusicController()
	#thread.start_new_thread(monitor_thread, (am,)) #... what? this breaks it, no matter what the thread is...
	try:
		lmc.MainLoop()
	except (KeyboardInterrupt, SystemExit):  #these aren't caught with exceptions...
		print("except (KeyboardInterrupt, SystemExit):")
		os._exit(0)
	except Exception as e:
		print("EXCEPTION:")
		print(e)
		os._exit(0) #kill process immediately so it can be respawned by the service.
