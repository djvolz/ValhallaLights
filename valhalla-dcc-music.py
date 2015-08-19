# Valhalla Dual Color Client (DCC)
# Read MIDI controller sliders and send 16 byte UDP packets to the Valhalla Dual Color Server to update LEDs.
# Interpret music coming in through Wolfson audio card on Raspberry Pi
# Convert the music to values that can be displayed by WS2812B LED strips
# Author: djvolz	8/19/15
# Author: clay		5/19/15

import os, sys
# import pygame
# import pygame.midi
# import pygame.fastevent
import array
import ctypes
import math
from os import popen
from array import array
# from pygame.locals import *
import socket
import struct
import time
import numpy as np
import logging

#from pyudev import Context, Monitor
#import pyudev
#import thread

# from pygame import mixer # Load the required library

import stabilize
import audio_setup
import korg_midi_reader as korg
#import korg_dummy as korg
from library.music import calculate_levels, read_musicfile_in_chunks, alternate_calculate_levels
import alsaaudio as aa


#try:
#	from pyudev.glib import MonitorObserver
#except:
#	from pyudev.glib import GUDevMonitorObserver as MonitorObserver

#todo: use pyudev to detect disconnect of the midi controller so we can reconnect.


#TODO (clay): fix find nanokontrol and fix setting IP and Port above...
#TODO (clay): add multiple "strips" or "domains"?
#TODO (clay): fix button up and button down mode trigger



class Constants:
	# NETWORK CONSTANTS
	SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	LED_IP        = "10.0.1.13" #"192.168.137.22"
	LED_PORT      = 5252
	# LED CONSTANTS
	MIN_INTENSITY = 0.0
	MAX_INTENSITY = 127.0
	MIDI_MAX      = 127.0
	SCALE 		  = 4

# Translate MIDI knobs and buttons into useable/clearer values
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
		#audio_setup.init_audio()
		self.midi_reader = korg.KorgMidiReader()

	def read_events(self):
		changed = self.midi_reader.read_events()
		self.read_buttons()
		self.read_settings()
		self.read_rgb()
		self.read_scale()
		return changed

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
						 'volume':     self.midi_reader.knobs[3],
						 'offset':      self.midi_reader.knobs[4],
						 'sway_speed':  self.midi_reader.knobs[5],
						 'minimum':     self.midi_reader.knobs[6],
						 'pulse_speed': self.midi_reader.knobs[7],

						 'length':      self.midi_reader.sliders[0],
						 'gradient':    self.midi_reader.sliders[1],
						 }
	def read_buttons(self):
		self.buttons = {
						'alternate_calculation':self.midi_reader.buttons[0][0],
						'intensity_preset':		self.midi_reader.buttons[0][1],
						'offset_preset':		self.midi_reader.buttons[0][2],
						
						'scale': 	 		    self.midi_reader.buttons[5][0],
						'music_mode_intensity': self.midi_reader.buttons[5][1],
						'music_mode_offset':    self.midi_reader.buttons[5][2],
						
						'third_color':			self.midi_reader.buttons[6][0],

						'pulse': 			    self.midi_reader.buttons[7][0],
						'rotate': 	 		    self.midi_reader.buttons[7][1],
						'sway':				    self.midi_reader.buttons[7][2]
						}

		# adjust to 3 frequency bins if third color added
		audio_setup.update_frequency_limits_with_columns(3 if self.buttons['third_color'] else 2)

		# update the new mode in case one of the mode buttons was pressed
		self.mode = self.get_mode()

		# check for the preset buttons
		if self.buttons['intensity_preset']:
			self.init_intensity_preset()
		elif self.buttons['offset_preset']:
			self.init_offset_preset()




	#define MODE_STATIC		0
	#define MODE_PULSING	1
	#define MODE_ROTATING	2
	#define MODE_SWAYING	4
	#define MODE_THIRDCOLOR 8  //three colors or two colors...
	def get_mode(self):
		return abs( (self.buttons['pulse']) + (self.buttons['rotate'] << 1) + (self.buttons['sway'] << 2)) + abs(self.buttons['third_color']  << 3)   #why is this negative!??!

	def read_scale(self):
		if self.buttons['scale']:
			self.scale = Constants.SCALE
		else:
			self.scale = 1

	# This function has to be hardcoded because we're emulating
	# a user changing to these initial settings 
	# (convenience mode for music preset)
	def init_intensity_preset(self):
		# initial settings
		self.midi_reader.sliders[0]    = 64 #length
		self.midi_reader.sliders[1]    = 0  #gradient
		self.midi_reader.knobs[4]      = Constants.MAX_INTENSITY #offset
		self.midi_reader.knobs[6]      = 0 # minimum

	# This function has to be hardcoded because we're emulating
	# a user changing to these initial settings 
	# (convenience mode for music preset)
	def init_offset_preset(self):
		# initial settings
		self.midi_reader.sliders[0]    = 96 #length
		self.midi_reader.sliders[1]    = 0  #gradient
		self.midi_reader.knobs[4]      = Constants.MAX_INTENSITY #offset
		self.midi_reader.knobs[6]      = Constants.MAX_INTENSITY - 10 # minimum





class LEDMusicController:

	def __init__(self):
		audio_setup.init_audio()

		#self.input needs to be initialized before pygame
		self.input = audio_setup.get_audio_input()

		self.midi = MIDI()


	# Analyze the audio input and turn it into light (aka magic)
	# (Sound -> Numbers -> Other Numbers -> Network Packet -> Light.  Basically as easy as 1, 2, pi. lol I'll stop now)
	#
	#		Note about joke comment above, don't bother reading if you're actually frantically trying to finish
	# 		your own lighting project.
	# 						I used to have the actual pi symbol in here, but python says: 
	#						SyntaxError: Non-ASCII character '\xcf' in file valhalla-dcc-music.py on line
	def analyze_line_in(self):
		# Start with these as our initial guesses - will calculate a rolling mean / std 
		# as we get input data.
		mean = [12.0 for _ in range(audio_setup.Audio.POSSIBLE_COLUMNS)]
		std = [0.5 for _ in range(audio_setup.Audio.POSSIBLE_COLUMNS)]
		recent_samples = np.empty((stabilize.Lights.MAX_SAMPLES, audio_setup.Audio.POSSIBLE_COLUMNS))
		num_samples = 0

		while True:
			changed = self.midi.read_events()
			if self.midi.buttons['music_mode_intensity'] or self.midi.buttons['music_mode_offset'] :
				
				# Read the audio stream and make it blow chunks (aka get a chunk of data and the length of that data)
				size, chunk = self.input.read()
				if size > 0:
					# I left this in as an entirely different method, so I can just command-f in the future
					# and remove all of the "alternate_..." functionality
					if self.midi.buttons['alternate_calculation']:
						# Make the chunk even length if it isn't already
						L = (len(chunk)/2 * 2)
						chunk = chunk[:L]

						# I like this one, but the values range significantly more because of power2
						data = alternate_calculate_levels(chunk, audio_setup.Audio.SAMPLE_RATE, audio_setup.Audio.FREQUENCY_LIMITS)
						converted_data = self.alternate_convert_data(data)


					# This is NORMAL music mode (aka boring, aka works fine, aka looks less like a seizure) 
					else:
						try:
							# Calculate the levels
							data = calculate_levels(chunk, 
													audio_setup.Audio.PERIOD_SIZE, 
													audio_setup.Audio.SAMPLE_RATE, 
													audio_setup.Audio.FREQUENCY_LIMITS,
													audio_setup.Audio.COLUMNS,
													audio_setup.Audio.NUM_CHANNELS)
							if not np.isfinite(np.sum(data)):
								# Bad data --- skip it
								continue
						except ValueError as e:
							# TODO: This is most likely occuring due to extra time in calculating
							# mean/std every 250 samples which causes more to be read than expected the
							# next time around.  Would be good to update mean/std in separate thread to
							# avoid this --- but for now, skip it when we run into this error is good 
							# enough ;)
							logging.debug("skipping update: " + str(e))
							continue

						# Interpret the data 
						converted_data = self.convert_data(data, mean, std)
					
					# Turn the music data into light (Computer Scientist Alchemy)
					self.convert_matrix_to_packet(converted_data)
					
					# This needs to happen regardless of selected mode so that the values
					# reflect the recently played music
					mean, std, recent_samples, num_samples = stabilize.compute_running_average(data, mean, std, recent_samples, num_samples)
			
			# If not in music mode, and the MIDI controller changed, update the lights
			elif changed:
				self.update_lights()

			# Nothing happened. Nap time.
			else:
				# waste time so that we don't eat too much CPU
				time.sleep(.005)
				#pygame.time.wait(1)


	

	# Turn a local audio file into light (aka magic)
	def analyze_audio_file_local(self, path):
		print "path = " + path

		for chunk, sample_rate in read_musicfile_in_chunks(path, play_audio=True):
			data = alternate_calculate_levels(chunk, sample_rate, audio_setup.Audio.FREQUENCY_LIMITS)
			self.convert_data_to_packet(data)
			changed = self.midi.read_events()
			if changed:
				self.update_lights()

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

		# rgb, rgb, rgb (not making a joke here, there are three different RGBs)
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

	# I left this in as an entirely different method, so I can just command-f in the future
	# and remove all of the "alternate_..." functionality
	# Denoise and map the matrix data to values that can be shown by the LEDs 
	def alternate_convert_data(self, matrix):
		# Dynamically update the possible light intensity range
		stabilize.stabilize_light_intensities()

		converted_matrix = [0] * len(matrix)

		for col in range(len(matrix)):
			# check the current possible intensity min and max
			val, lights_range = stabilize.check_if_val_within_range(matrix[col])

			# Map the light values to be within the range of the MIDI light intensities
			converted_matrix[col] = stabilize.scale(val, (lights_range.min_intensity, lights_range.max_intensity), (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY))

		return converted_matrix

	# Denoise and map the matrix data to values that can be shown by the LEDs 
	def convert_data(self, matrix, mean, std):
		converted_matrix = [0] * len(matrix)
			
		for col in range(len(matrix)):
			# Calculate output pwm, where off is at some portion of the std below
			# the mean and full on is at some portion of the std above the mean.
			val = matrix[col] - mean[col] + 0.5 * std[col]
			val = val / (1.25 * std[col])
			if val > 1.0:
				val = 1.0
			if val < 0:
				val = 0

			# Map the light values to be within the range of the MIDI light intensities
			converted_matrix[col] = stabilize.scale(val, (0.0, 1.0), (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY))

		return converted_matrix


	def convert_matrix_to_packet(self, matrix):
		# Music Mode INTENSITY
		if self.midi.buttons['music_mode_intensity']:
			rgb = [x[:] for x in [[0]*3]*3]

			# Scale the MIDI value to be within the slider ranges
			for i in range(len(matrix)):
				for j in range(len(self.midi.rgb[i])):
					rgb[i][j] = stabilize.scale(matrix[i], (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY), (int(self.midi.settings['minimum']/Constants.MAX_INTENSITY * self.midi.rgb[i][j]), self.midi.rgb[i][j]))
					#print("knob %d %d" % (self.midi.midi_reader.knobs[6], int(self.midi.midi_reader.knobs[6]/254. * self.midi.midi_reader.rgb[i][j])))

			# update lights with new intensities
			self.midi.rgb = rgb
			self.update_lights()

		# Music Mode OFFSET
		if self.midi.buttons['music_mode_offset']:
			# map between minimum and offset
			offset = stabilize.scale(matrix[0], (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY), (int(self.midi.settings['minimum']/Constants.MAX_INTENSITY * self.midi.settings['offset']), self.midi.settings['offset']))
			self.midi.settings['offset'] = offset

			# update lights with new offset
			self.update_lights()




	#ugly... volume is 0-Constants.MAX_INTENSITY, balance is 0-254
	# author: clay, hence the lack of comments, lol. (We'll see if he actually reads these comments and notices this)
	def update_volume(self):
		#currently the balance is stored in knobs of 1... we can just keep it there... (note its scaled up to 254)
		#we want it where if it's centered (with some hysteresis) then both volumes are at 100%, then they fade from there.
		balance = 127
		volume = self.midi.settings['volume']

		if balance > 120:
			volumel = 22 * volume/Constants.MIDI_MAX
		else:
			volumel = 22 * balance/Constants.MIDI_MAX * volume/Constants.MIDI_MAX

		if balance < 134:
			volumer = 33 * volume/Constants.MIDI_MAX
		else:
			volumer = 33 * (1-(254-balance)/Constants.MIDI_MAX) * volume/Constants.MIDI_MAX
		
		volumer = int(volumer)
		volumel = int(volumel)

		#aa.Mixer('HPOUT2 Digital').setvolume(volumel)
		#aa.Mixer('HPOUT1 Digital').setvolume(volumer)
		#aa.Mixer('HPOUT2L Input 1').setvolume(volumel)
		#aa.Mixer('HPOUT2R Input 1').setvolume(volumel)
		#aa.Mixer('HPOUT1L Input 1').setvolume(volumer)
		#aa.Mixer('HPOUT1R Input 1').setvolume(volumer)
		# print([volumel, volumer])
		#would this be any faster?
		# os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1 Volume' " + str(volumer) + "; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1 Volume' " + str(volumer))
			

	def run(self):
		# Play local file if song path is given as argument
		if len(sys.argv) > 1:
			path = sys.argv[1]
			self.analyze_audio_file_local(path)

		# Jump straight into analyzing the audio in ports
		self.analyze_line_in()


if __name__ == '__main__':
	
	lmc = LEDMusicController()
	#thread.start_new_thread(monitor_thread, (am,)) #... what? this breaks it, no matter what the thread is...
	try:
		# DO PROGRAM THAT WE WROTE, MAKE VALHALLA PRETTY
		lmc.run()
	except (KeyboardInterrupt, SystemExit):  #these aren't caught with exceptions...
		print("except (KeyboardInterrupt, SystemExit):")
		os._exit(0)
	except Exception as e:
		print("EXCEPTION:")
		print(e)
		os._exit(0) #kill process immediately so it can be respawned by the service.
