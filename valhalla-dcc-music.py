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

#TODO: fix find nanokontrol and fix setting IP and Port above...
#TODO: cleanup the way the sliders are packed...
#TODO: add sound recording and sending to a different port #this looks like a good starting point: http://people.csail.mit.edu/hubert/pyaudio/docs/ #http://stackoverflow.com/questions/18406570/python-record-audio-on-detected-sound  #http://stackoverflow.com/questions/892199/detect-record-audio-in-python/892293#892293 #http://stackoverflow.com/questions/1797631/recognising-tone-of-the-audio #https://docs.python.org/2/library/audioop.html #https://wiki.python.org/moin/PythonInMusic #http://www.codeproject.com/Articles/32172/FFT-Guitar-Tuner #http://stackoverflow.com/questions/19079429/using-pyaudio-libraries-in-python-linux (select input)
#TODO: add multiple "strips" or "domains"?
#TODO: fix button up and button down mode trigger!


class Constants:
	# NETWORK CONSTANTS
	SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	LED_IP           = "10.0.1.13"  #"192.168.137.22"
	LED_PORT         = 5252
	# LED CONSTANTS
	MIN_INTENSITY    = 0.0
	MAX_INTENSITY	 = 255.0
	
class MIDI:
	scale = 1 
	mode  = 0 
	knobs = [0]*8 #initialize knobs 
	rgb   = [x[:] for x in [[0]*3]*3] #I really hate python sometimes...

class Settings:
	midi_in		= None
	midi_out 	= None
	intensity   = 0; #average intensity of first two colors (to set intensity of third light).
	aux_in      = False
	lr_swap     = False
	buttons     = [False]*3
	thirdcolors = [False]*3
	volume 		= 30





class AMK:
	
	def __init__(self):
		pygame.init()
		pygame.midi.init()

	# both display all attached midi devices, and look for ones matching nanoKONTROL2
	def findNanoKontrol(self, quiet=False):
		if not quiet:
			print("ID: Device Info")
			print("---------------")
		in_id = None
		out_id = None
		for i in range( pygame.midi.get_count() ):
			(interf, name, input, output, opened) = pygame.midi.get_device_info(i)

			in_out = ""
			if input:
				in_out = "(input)"
			if output:
				in_out = "(output)"

			if name.find("nanoKONTROL2") >= 0 and input:
				in_id = i
			elif name.find("nanoKONTROL2") >= 0 and output:
				out_id = i

			if not quiet:
				print ("%2i: interface :%s:, name :%s:, opened :%s:  %s" % (i, interf, name, opened, in_out) )

		return (in_id, out_id)

	# turn a LED on or off
	def light(self, btn, on):
		if on:
			out = 127
		else:
			out = 0
		self.midi_out.write_short(176, btn, out)
		
	def all_off(self):
		for i in [0x20, 0x30, 0x40]:
			for j in range(8):
				self.light(i+j, False)


	def setup(self):
		self.set_midi_device()
		self.all_off()  #make sure nothing is lit.
		audio_setup.init_audio()


	def set_midi_device(self):		
		# attempt to autodetect nanokontrol
		(in_device_id, out_device_id) = self.findNanoKontrol()
		
		# if none of the above, use system default IDs
		if in_device_id is None:
			in_device_id = self.in_device_id = pygame.midi.get_default_input_id()
		if out_device_id is None:
			out_device_id = self.out_device_id = pygame.midi.get_default_output_id()
		
		if (in_device_id is not None) and (out_device_id is not None):
			print("Using input  id: %s" % in_device_id)
			print("Using output id: %s" % out_device_id)
			
			print("Setting MIDI device to in: %d out: %d." % (in_device_id, out_device_id) )
			Settings.midi_in = self.midi_in = pygame.midi.Input( in_device_id )		
			Settings.midi_out = self.midi_out = pygame.midi.Output(out_device_id, 0)
		
			
		
	# Analyze the audio input and turn it into light (aka magic)
	def analyze_line_in(self):
		input = audio_setup.get_audio_input()
		while True:
			size, chunk = input.read()
			if size > 0:
				# Make the chunk even length if it isn't already
				L = (len(chunk)/2 * 2)
				chunk = chunk[:L]
				
				# Calculate the levels
				data = calculate_levels(chunk, audio_setup.Constants.SAMPLE_RATE, audio_setup.Constants.FREQUENCY_LIMITS)
				
				# Interpret the data
				self.convert_music_data_to_packet(data)
				self.control_midi()



	# Turn a local audio file into light (aka magic)
	def analyze_audio_file_local(self):
		path = 'music/sample.mp3'
		print "path = " + path

		for chunk, sample_rate in read_musicfile_in_chunks(path, play_audio=True):
			data = calculate_levels(chunk, sample_rate, audio_setup.Constants.FREQUENCY_LIMITS)
			self.convert_music_data_to_packet(data)
			self.control_midi()

	
	
	# Stuff the packet and send it out over the network.
	def update_lights(self, rgb):
		try:
			t = [int(MIDI.mode)]
			t.extend([int(item) for item in MIDI.knobs[2:8]])
			t.extend([int(item/MIDI.scale) for sublist in rgb for item in sublist])
			Constants.SOCK.sendto(struct.pack('B' * len(t),*t),(Constants.LED_IP, Constants.LED_PORT))						
		except Exception as e:
			print(e)
		

	def convert_music_data_to_packet(self, matrix):
		# Dynamically update the possible light intensity range
		stabilize.stabilize_light_intensities()

		intensity_matrix = [0] * len(matrix)

		for col in range(len(matrix)):
			# check the current possible intensity min and max
			val, lights_range = stabilize.check_if_val_within_intensity_ranges(matrix[col])

			# Map the light values to be within the range of the Packet light intensities
			intensity_matrix[col] = self.scale(val, (lights_range.music_min_intensity, lights_range.music_max_intensity), (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY))
		
		rgb = [x[:] for x in [[0]*3]*3]

		# Scale the Packet value to be within the slider ranges
		for i in range(len(intensity_matrix)):
			for j in range(len(MIDI.rgb[i])):
				rgb[i][j] = self.scale(intensity_matrix[i], (Constants.MIN_INTENSITY, Constants.MAX_INTENSITY), (0.0, MIDI.rgb[i][j]))
				
		# update the lights from the matrix
		self.update_lights(rgb)

	# Scale the given value from the scale of src to the scale of dst.
	def scale(self, val, src, dst):
		return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]


	#ugly... volume is 0-127, balance is 0-254
	def set_volume(self, volume, balance):
		#currently the balance is stored in knobs of 1... we can just keep it there... (note its scaled up to 254)
		#we want it where if it's centered (with some hysteresis) then both volumes are at 100%, then they fade from there.
		if balance > 120:
			volumel = 22 * volume/127
		else:
			volumel = 22 * balance/127 * volume/127
			
		if balance < 134:
			volumer = 33 * volume/127
		else:
			volumer = 33 * (1-(254-balance)/127) * volume/127
		
		print([volumel, volumer])
		#would this be any faster?
		#os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1 Volume' " + str(volumer) + "; amixer -Dhw:0 cset name='HPOUT1R Input 1 Volume' " + str(volumer))



	# TODO: this really needs to be broken up
	def control_midi(self):				
		# Look for midi events
		if Settings.midi_in.poll():
			midi_events = Settings.midi_in.read(100)
			midi_evs = pygame.midi.midis2events(midi_events, Settings.midi_in.device_id)
			changed = False
			
			for me in midi_evs:

				if me.data1 == 0x00: # and me.data1 <= 0x01: #slider 0
					Settings.volume = me.data2
					self.set_volume(Settings.volume, MIDI.knobs[0])
					
					
				#process slider event
				if me.data1 >= 0x00 and me.data1 <= 0x07 and me.data1 >= 0x02:
					#sliders[me.data1] = me.data2 * 2
					MIDI.rgb[int((me.data1-2)/3)][(me.data1-2)%3] = me.data2 * 2  #sliders 2-4 are MIDI.rgb[1] sliders 5-7 are MIDI.rgb[2]
					Settings.intensity = (sum(MIDI.rgb[0]) + sum(MIDI.rgb[1]) ) / 2 #/ 6 #average Settings.intensity of lighting, used for calculating Settings.intensity of third color.
					changed = True
					#so really we should update the Settings.intensity of the third color here... but it's actually kind of a nice way to be able to adjust it.
				
				#knob event
				if me.data1 >= 0x10 and me.data1 <= 0x17:						
					MIDI.knobs[me.data1 - 0x10] = me.data2 * 2
					if me.data1 - 0x10 >= 2:
						changed = True
					elif me.data1 == 0x10:
						self.set_volume(Settings.volume, MIDI.knobs[0])
									  
				if me.data1 >= 0x20 and me.data1 <= 0x47 and me.data2 == 127:  #these are actually triggered on both button up and button down, so you have to check for the 127 (which is on button down, I believe)
					idx = (me.data1 >> 4) - 2;
					if (me.data1 & 0x07 == 7):
						#idx = (me.data1 >> 4) - 2;
						Settings.buttons[idx] = ~Settings.buttons[idx];
						self.light(me.data1, Settings.buttons[idx])
						if Settings.buttons[idx]:
							if idx == 1:  #can't rotate and sway at the same time...
								Settings.buttons[2] = False
								self.light(0x37, Settings.buttons[1])
								self.light(0x47, Settings.buttons[2])
							elif idx == 2:
								Settings.buttons[1] = False
								self.light(0x37, Settings.buttons[1])
								self.light(0x47, Settings.buttons[2])
						changed = True
					#elif me.data1 == 0x26 and me.data2 == 127:
					elif (me.data1 & 0x06 == 6): #6th button row.  We use these to build third color.
						#Settings.buttons[3] = ~Settings.buttons[3]
						Settings.thirdcolors[idx] = ~Settings.thirdcolors[idx]
						self.light(me.data1, Settings.thirdcolors[idx])
						numlit = sum(Settings.thirdcolors)
						if numlit:
							for i in range(3):
								MIDI.rgb[2][i] = Settings.thirdcolors[i]*Settings.intensity/numlit #split Settings.intensity across the number of colors (MIDI.rgb) enabled.
								if MIDI.rgb[2][i] > 255:  # if one of the first two colors is full Settings.intensity white, we can't match the Settings.intensity.
									MIDI.rgb[2][i] = 255
						changed = True
					elif (me.data1 & 0x05 == 5 and idx == 0):
						if MIDI.scale == 4:
							MIDI.scale = 1
							self.light(me.data1, False)
						else:
							MIDI.scale = 4
							self.light(me.data1, True)
						changed = True
					elif (me.data1 & 0x07 == 0x00): #first row of Settings.buttons
						print("button 0")
						#set the input
						if idx == 0:
							Settings.aux_in = ~Settings.aux_in
							self.light(me.data1, Settings.aux_in)
						#set the lr stuff.
						elif idx == 1:
							Settings.lr_swap = ~Settings.lr_swap
							self.light(me.data1, Settings.lr_swap)
							
						audio_setup.set_audio(Settings.aux_in, Settings.lr_swap)
							
						
					else:
						if (MIDI.mode > 0 or MIDI.scale != 1):
							changed = True
						MIDI.mode = 0
						MIDI.scale = 1
						Settings.buttons = [False]*3
						Settings.thirdcolors = [False]*3
						MIDI.rgb[2] = [0]*3;
						self.all_off()
						self.light(0x20, Settings.aux_in) #relight the audio keys if they need to be
						self.light(0x30, Settings.lr_swap)
					MIDI.mode = abs( (Settings.buttons[0]) + (Settings.buttons[1] << 1) + (Settings.buttons[2] << 2)) + abs( any(Settings.thirdcolors)  << 3)   #why is this negative!??!
					
				if changed: #me.data1 >= 2 and me.data1 <=7:
					self.update_lights(MIDI.rgb)
					# pass

	def MainLoop(self):
		self.analyze_audio_file_local()
		# self.analyze_line_in()

		# Once song finishes. Default to checking midi controller
		while True:
			# waste time so that we don't eat too much CPU
			pygame.time.wait(1)
			self.control_midi()

	
		
		

def test_mon():
	print("got usb event")
	
def monitor_thread(am):	   
	print("Starting USB Monitoring thread...")
	#monitor USB devices. reset the midi controller if anything is plugged in.
	context = Context()
	monitor = Monitor.from_netlink(context)

	monitor.filter_by(subsystem='usb')
	observer = MonitorObserver(monitor)

	observer.connect('device-event', test_mon) #am.set_midi_device)
	monitor.start()
	
	#glib.MainLoop().run() #this thread is idle unless there is a usb event.
							
if __name__ == '__main__':
	am = AMK()
	#thread.start_new_thread(monitor_thread, (am,)) #... what? this breaks it, no matter what the thread is...
	try:
		am.setup()
		am.MainLoop()
	except (KeyboardInterrupt, SystemExit):  #these aren't caught with exceptions...
		print("except (KeyboardInterrupt, SystemExit):")
		os._exit(0)
	except Exception as e:
		print("EXCEPTION:")
		print(e)
		os._exit(0) #kill process immediately so it can be respawned by the service.
