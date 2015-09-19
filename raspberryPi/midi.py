# Midi Translator
# Translate MIDI knobs and buttons into useable/clearer values
# Author: djvolz	8/19/15

import constants as Constants
import audio_setup
import korg_midi_reader as korg
#import korg_dummy as korg

class MIDI:
	mode  = 0
	rgb = [[0]*3 for x in range(3)] #[x[:] for x in [[0]*3]*3] #I really hate python sometimes...
	buttons = {
				'lr_swap': 				False,
				'aux_in': 				False,
				'dimmer': 	 		   	False,
				'music_mode_intensity': False,
				'music_mode_offset':    False,
				'pulse': 			   	False,
				'rotate': 	 		   	False,
				'sway':				   	False,
				'red':				   	False,
				'green':				False,
				'blue':				   	False,
				'third_color':				False,
			   }
			   
	#if we make this a dict or something, we can automatically generate the buttons_en... #actually, we should probably just index the dictionary buttons with these tuples.
	aux_in               =  (0, 0)
	lr_swap              =  (0, 1)
	reset                =  (0, 2)
	dimmer				 =  (5, 0)
	music_mode_intensity = 	(5, 1)
	music_mode_offset    =  (5, 2)
	red                  =	(6, 0)
	green                =	(6, 1)
	blue                 =	(6, 2)	
	#third_color          =	(6, 0)
	pulse                = 	(7, 0)
	rotate               = 	(7, 1)
	sway                 =	(7, 2)
	rainbow_preset       =  (4, 0)
	intensity_preset     =  (4, 1)
	offset_preset        =  (4, 2)
	
	
	# Mutually exclusive modes
	excl = [[sway, rotate, music_mode_offset],[pulse, music_mode_intensity],[rainbow_preset,intensity_preset,offset_preset]]
	# Only enable buttons that are being used
	buttons_en = [[True, True, True],
				  [False, False, False],
				  [False, False, False],
				  [False, False, False],
				  [True, True, True],
				  [True, True, True],
				  [True, True, True],
				  [True,True,True]] #only enable some buttons

	volume = 60 #initial volume #perhaps we should set all of the initial values?

	def __init__(self):
		self.midi_reader = korg.KorgMidiReader(self.buttons_en,self.excl)

	def read_events(self):
		changed = self.midi_reader.read_events()
		#print('reading events')
		self.read_buttons()
		#print('reading settings')
		self.read_settings()
		#print('reading rgb')
		self.read_rgb()
		#print(changed)
		#self.read_scale()
		return changed

	def read_rgb(self):
		# translate the slider data into rgb values for packet
		self.rgb[0]    = [int(item) for item in self.midi_reader.sliders[2:5]]
		self.rgb[1]    = [int(item) for item in self.midi_reader.sliders[5:8]]
		
		# check the first three knobs for third color if the button is enabled
		#if self.buttons['third_color']:
			#for i in range(3):
			#	self.rgb[2][i] = self.midi_reader.knobs[i]
		# if button isn't pressed, no third color. knobs[0-2] go unused
		
		#buttons control third knobs
		thirdcolors = [self.buttons['red'], self.buttons['green'], self.buttons['blue']]
		if any(thirdcolors): 
			#self.buttons['third_color'] = True
			intensity = (sum(self.rgb[0]) + sum(self.rgb[1])) / 2
			numlit = sum(thirdcolors)
			if numlit:
				for i in range(3):
					self.rgb[2][i] = thirdcolors[i]*intensity/numlit #split intensity across the number of colors (rgb) enabled.
					self.rgb[2][i] = 255 if self.rgb[2][i] > 255 else self.rgb[2][i]  # if one of the first two colors is full intensity white, we can't match the intensity.
		else:
			#self.buttons['third_color'] = False  #not necessary if being controlled by knobs
			self.rgb[2] = [0]*3



#
	def read_settings(self):
		self.settings = {
						 #'red':     self.midi_reader.knobs[0],
						 #'green':     self.midi_reader.knobs[1],
						 #'blue':     self.midi_reader.knobs[2],
						 #'volume':     self.midi_reader.knobs[3],
						 'volume':     self.midi_reader.sliders[0],
						 'balance':     self.midi_reader.knobs[0],
						 'offset':      self.midi_reader.knobs[4],
						 'sway_speed':  self.midi_reader.knobs[5],
						 'minimum':     self.midi_reader.knobs[6],
						 'pulse_speed': self.midi_reader.knobs[7],

						 'length':      self.midi_reader.knobs[2],
						 'gradient':    self.midi_reader.knobs[3],
						 #'length':      self.midi_reader.sliders[0],
						 #'gradient':    self.midi_reader.sliders[1],
						 }
	def read_buttons(self):
		#print(self.aux_in, self.intensity_preset, self.offset_preset, self.rainbow_preset,self.dimmer,self.music_mode_intensity,self.music_mode_offset) #,self.third_color)
		#print(self.red,self.green,self.blue,self.lr_swap,self.pulse,self.rotate,self.sway,self.reset)
		buttons = {
					'aux_in':				self.midi_reader.buttons[self.aux_in[0]][self.aux_in[1]],
					'intensity_preset':		self.midi_reader.buttons[self.intensity_preset[0]][self.intensity_preset[1]],
					'offset_preset':		self.midi_reader.buttons[self.offset_preset[0]][self.offset_preset[1]],
					'rainbow_preset':		self.midi_reader.buttons[self.rainbow_preset[0]][self.rainbow_preset[1]],
					'dimmer': 	 		    self.midi_reader.buttons[self.dimmer[0]][self.dimmer[1]],
					'music_mode_intensity': self.midi_reader.buttons[self.music_mode_intensity[0]][self.music_mode_intensity[1]],
					'music_mode_offset':    self.midi_reader.buttons[self.music_mode_offset[0]][self.music_mode_offset[1]],
					#'third_color':			self.midi_reader.buttons[self.third_color[0]][self.third_color[1]],
					#'third_color':                 False, #ugh, this has to be here, otherwise things complain.
					'red': 	                self.midi_reader.buttons[self.red[0]][self.red[1]],
					'green': 	            self.midi_reader.buttons[self.green[0]][self.green[1]],
					'blue':		            self.midi_reader.buttons[self.blue[0]][self.blue[1]],
					'lr_swap':				self.midi_reader.buttons[self.lr_swap[0]][self.lr_swap[1]],
					# 'pulse': 			    self.midi_reader.buttons[7][0],
					# 'rotate': 	 		    self.midi_reader.buttons[7][1],
					# 'sway':				    self.midi_reader.buttons[7][2]
					'pulse': 	            self.midi_reader.buttons[self.pulse[0]][self.pulse[1]],
					'rotate': 	            self.midi_reader.buttons[self.rotate[0]][self.rotate[1]],
					'sway':                 self.midi_reader.buttons[self.sway[0]][self.sway[1]],
					'reset':                self.midi_reader.buttons[self.reset[0]][self.reset[1]],
					}
		if buttons['reset']:
			for i in range(len(self.midi_reader.buttons)):
				for j in range(len(self.midi_reader.buttons[i])):
					self.midi_reader.buttons[i][j] = False
			self.midi_reader._all_off()
				
		if buttons['aux_in'] != self.buttons['aux_in'] or buttons['lr_swap'] != self.buttons['lr_swap']:
				audio_setup.set_audio(buttons['aux_in'], buttons['lr_swap'])
		
		self.buttons = buttons
		
		self.dimmer_setting = Constants.DIMMER if self.buttons['dimmer'] else 1
		
		# adjust to 3 frequency bins if third color added
		self.buttons['third_color'] = any([self.buttons['red'], self.buttons['green'], self.buttons['blue']]) # ugh, move this (but we need it on the next line...).
		
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

		
	#def read_scale(self):
	#	if self.buttons['scale']:
	#		self.scale = Constants.SCALE
	#	else:
	#		self.scale = 1

	# This function has to be hardcoded because we're emulating
	# a user changing to these initial settings 
	# (convenience mode for music preset)
	def init_intensity_preset(self):
		# initial settings
		self.midi_reader.sliders[0]    = Constants.MIDI_MAX #length
		self.midi_reader.knobs[4]      = Constants.MIDI_MAX #offset
		self.midi_reader.knobs[6]      = Constants.MIDI_MAX - 10 # minimum

	# This function has to be hardcoded because we're emulating
	# a user changing to these initial settings 
	# (convenience mode for music preset)
	def init_offset_preset(self):
		# initial settings
		self.midi_reader.sliders[0]    = Constants.MIDI_MAX #length
		self.midi_reader.knobs[4]      = Constants.MIDI_MAX #offset
		self.midi_reader.knobs[6]      = Constants.MIDI_MAX - 10 # minimum


	# This function has to be hardcoded because we're emulating
	# a user changing to these initial settings 
	# (convenience mode for music preset)
	def init_rainbow_preset(self):
		# initial settings
		self.midi_reader.sliders[0]                                        = Constants.MIDI_MAX #length
		self.midi_reader.knobs[4]                                          = Constants.MIDI_MAX #offset
		self.midi_reader.knobs[3]                                          = Constants.MIDI_MAX #gradient
		#self.midi_reader.buttons[self.third_color[0]][self.third_color[1]] = True 					 #third_color
		self.midi_reader.buttons[self.red[0]][self.red[1]]                 = True
		self.midi_reader.sliders[2]                                        = Constants.MIDI_MAX #red
		self.midi_reader.sliders[7]                                        = Constants.MIDI_MAX #blue
		self.midi_reader.knobs[1]                                          = Constants.MIDI_MAX #green



