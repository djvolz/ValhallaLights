# Korg Midi Reader
# Korg nanoKONTROL2 midi controller
# Author: clay	8/19/15

import pygame
import pygame.midi
#import pygame.fastevent
#from pygame.locals import 

class KorgMidiReader:
	"""
	Select the first attached Korg NANOKontrol2 then update the current state of the controller whenever read_events() is callled.
	
	# NANOKontrol Magic Values:
	# 0x00 - 0x07: sliders
	# 0x10 - 0x17: knobs
	# 0x20 - 0x27: S buttons
	# 0x30 - 0x37: M buttons
	# 0x40 - 0x47: R buttons
	#WARNING! You must download the korg driver and configuration software and set the LED control to "external" for the set lighting to work!
	"""
	knobs      = [0]*8
	sliders    = [0]*8
	buttons    = [[False]*3 for x in range(8)]  #stupid python multi-dim array init
	# buttons_en = [[True, True, True],
	# 			  [False, False, False],
	# 			  [False, False, False],
	# 			  [False, False, False],
	# 			  [False, False, False],
	# 			  [True, True, True],
	# 			  [True, False, False],
	# 			  [True,True,True]] #only enable some buttons
	buttons    = [[False]*3 for x in range(8)]  #stupid python multi-dim array init
	
	# def __init__(self):
	def __init__(self, buttons_en=None, buttons_exclusive=None):
		#pygame.init()
		pygame.midi.init()
		self._set_midi_device()
		self._all_off()	#make sure nothing is lit.
		self.buttons_en = buttons_en if buttons_en is not None else [[True]*3 for x in range(8)] #enable all by default if a map isn't passed
		self.buttons_exclusive = buttons_exclusive if buttons_exclusive is not None else [] #list of lists of button indices (in tuples) that are exclusive, e.g. [[(2,3),(1,3)],[(7,1),(7,2),(7,3)]]
		
	# both display all attached midi devices, and look for ones matching nanoKONTROL2
	def _findNanoKontrol(self, quiet=False):
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
			elif output:
				in_out = "(output)"

			if name.find("nanoKONTROL2") >= 0 and input:
				in_id = i
			elif name.find("nanoKONTROL2") >= 0 and output:
				out_id = i

			if not quiet:
				print ("%2i: interface :%s:, name :%s:, opened :%s:  %s" % (i, interf, name, opened, in_out) )

		return (in_id, out_id)

	def _set_midi_device(self, quiet=False):
		# attempt to autodetect nanokontrol
		(in_device_id, out_device_id) = self._findNanoKontrol(quiet=quiet)

		# if none of the above, use system default IDs
		if in_device_id is None:
			in_device_id = self.in_device_id = pygame.midi.get_default_input_id()
		if out_device_id is None:
			out_device_id = self.out_device_id = pygame.midi.get_default_output_id()

		if (in_device_id is not None) and (out_device_id is not None):
			if not quiet:
				print("Setting MIDI device to in: %d out: %d." % (in_device_id, out_device_id) )
			self.midi_in = pygame.midi.Input( in_device_id )
			self.midi_out = pygame.midi.Output(out_device_id, 0)

	def _light(self, btn, on):
		"""Turn LED behind button btn on or off."""
		self.midi_out.write_short(176, btn, 127 if on else 0)

	def _all_off(self):
		"""Turn all the button LEDs off."""
		for i in range(3): #[0x20, 0x30, 0x40]:
			for j in range(8):
				self._light(((i+2)<<4)+j, False)
				self.buttons[j][i] = False
				
	def read_events(self):
		"""Read all events in the midi queue and update their states locally.  Toggle button states on key down; if a button state is true light it.  Returns true if there was an event."""
		midi_events = self.midi_in.read(100)
		midi_evs = pygame.midi.midis2events(midi_events, self.midi_in.device_id)
		for me in midi_evs:
			midi_col = me.data1 & 0xF

			#the media buttons on the left are bigger than this
			if midi_col <= 7:  

				#process slider event
				if me.data1 >= 0x00 and me.data1 <= 0x07: 
					self.sliders[midi_col] = me.data2

				#knob event
				elif me.data1 >= 0x10 and me.data1 <= 0x17: 
					self.knobs[midi_col] = me.data2	

				# button event down #these are actually triggered on both button up and button down, 
				# so you have to check for the 127 (which is on button down)		
				elif me.data1 >= 0x20 and me.data1 <= 0x47 and me.data2 == 127: 
					btn_row = (me.data1 >> 4) - 2

					# don't do anything if the button isn't enabled.
					if self.buttons_en[midi_col][btn_row]:
						self.buttons[midi_col][btn_row] = not self.buttons[midi_col][btn_row]
						self._light(me.data1, self.buttons[midi_col][btn_row])

						# update exclusive if this button went to True
						if self.buttons[midi_col][btn_row]: 
							for e in self.buttons_exclusive:
								if (midi_col,btn_row) in e:
									# print('exclusion found! %d,%d' % (midi_col,btn_row))
									for b in e:
										if b != (midi_col,btn_row):
											# print('turning %d,%d off' % (b[0],b[1]))
											self.buttons[b[0]][b[1]] = False
											self._light(((b[1]+2) << 4) + b[0], False)
		
		# Only return True if a MIDI event occurred					
		return False if len(midi_evs) == 0 else True



