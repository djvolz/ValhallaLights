# Midi Translator
# Translate MIDI knobs and buttons into useable/clearer values
# Author: djvolz	8/19/15

import constants as Constants
import audio_setup
import korg_midi_reader as korg
#import korg_dummy as korg

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
	music_mode_intensity = 	(5, 1)
	music_mode_offset    =  (5, 2)
	third_color          =	(6, 0)
	pulse                = 	(7, 0)
	rotate               = 	(7, 1)
	sway                 =	(7, 2)
	excl = [[sway, rotate, music_mode_offset],[pulse, music_mode_intensity]]

	def __init__(self):
		#audio_setup.init_audio()

		# self.midi_reader = korg.KorgMidiReader()

		# Only enable buttons that are being used
		buttons_en = [[True, True, True],
					  [False, False, False],
					  [False, False, False],
					  [False, False, False],
					  [False, False, False],
					  [True, True, True],
					  [True, False, False],
					  [True,True,True]] #only enable some buttons

		# Prevent certain buttons from interacting
		excl = [[(7,1),(7,2),(5,2)], #rotate, sway and music_mode_offset are exclusive
			   [(7,0),(5,1)]] #pulse and music_mode_intensity are exclusive

		self.midi_reader = korg.KorgMidiReader(buttons_en,excl)

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
						
						'third_color':			self.midi_reader.buttons[self.third_color[0]][self.third_color[1]],

						# 'pulse': 			    self.midi_reader.buttons[7][0],
						# 'rotate': 	 		    self.midi_reader.buttons[7][1],
						# 'sway':				    self.midi_reader.buttons[7][2]
						'pulse': 	self.midi_reader.buttons[self.pulse[0]][self.pulse[1]],
						'rotate': 	self.midi_reader.buttons[self.rotate[0]][self.rotate[1]],
						'sway':		self.midi_reader.buttons[self.sway[0]][self.sway[1]]
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
		self.midi_reader.buttons[0][1] = False
		self.midi_reader.sliders[0]    = 64 #length
		self.midi_reader.knobs[4]      = Constants.MAX_INTENSITY #offset
		self.midi_reader.knobs[6]      = 0 # minimum

	# This function has to be hardcoded because we're emulating
	# a user changing to these initial settings 
	# (convenience mode for music preset)
	def init_offset_preset(self):
		# initial settings
		self.midi_reader.sliders[0]    = 96 #length
		self.midi_reader.knobs[4]      = Constants.MAX_INTENSITY #offset
		self.midi_reader.knobs[6]      = Constants.MAX_INTENSITY - 10 # minimum



