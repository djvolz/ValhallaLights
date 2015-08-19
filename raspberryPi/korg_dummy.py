# Korg Dummy Midi Reader
# Fake a Korg nanoKONTROL2 midi controller if you don't have the hardware.
# Author: clay	8/19/15


class KorgMidiReader:
	"""
	Select the first attached Korg NANOKontrol2 then update the current state of the controller whenever read_events() is callled.
	
	# NANOKontrol Magic Values:
	# 0x00 - 0x07: sliders
	# 0x10 - 0x17: knobs
	# 0x20 - 0x27: S buttons
	# 0x30 - 0x37: M buttons
	# 0x40 - 0x47: R buttons
	"""
	knobs      = [60]*8
	sliders    = [60]*8
	buttons    = [[False]*3 for x in range(8)]  #stupid python multi-dim array init
	buttons_en = [[False, False, False],
				  [False, False, False],
				  [False, False, False],
				  [False, False, False],
				  [False, False, False],
				  [True, True, True],
				  [True, False, False],
				  [True,True,True]] #only enable some buttons
	
	def __init__(self):
		pass

		
	
	def read_events(self):
		return False




