# Audio Setup
# Setup the raspberry pi's audio for Valhalla's sound system and Wolfson Audio card
# Author: djvolz	8/19/15

import os
import alsaaudio as aa
from music import calculate_column_frequency


class Audio:
	# DECODER CONSTANTS
	POSSIBLE_COLUMNS = 3
	COLUMNS          = 2
	SAMPLE_RATE      = 44100
	NUM_CHANNELS     = 2
	PERIOD_SIZE      = 2000 # Use a multiple of 8 (2000 seems to be the max before errors on wolfson audio card)
	FREQUENCY_LIMITS = calculate_column_frequency(200, 10000, COLUMNS)

def set_audio(aux_in=False, lr_swap=False):
	#HPOUT2 is the emotiva/klipsch (left)
	#HPOUT1 is the pioneer (right)
	#IN3 is the aux in
	#AIF2RX2 is the SPDIF in (if setup correctly)
	if aux_in:
		print('setting audio to aux_in')
		os.system("amixer -q -Dhw:sndrpiwsp cset name='SPDIF In Switch' off;") # amixer -q -Dhw:sndrpiwsp cset name='TX Playback Switch' off;  amixer -q -Dhw:sndrpiwsp cset name='RX Playback Switch' on; amixer -q -Dhw:sndrpiwsp cset name='AIF Playback Switch' on;
		if lr_swap:
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' IN3R") #lr
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' IN3R")
		else:
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' IN3L") #both left
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' IN3R; amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' IN3R") #both right

		os.system("amixer -q -Dhw:sndrpiwsp cset 'name=AIF1TX1 Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset 'name=AIF1TX2 Input 1' IN3R") #set recording input
	else:
		print('setting audio to spdif')
		os.system("amixer -q -Dhw:sndrpiwsp cset name='SPDIF In Switch' on;") # amixer -q -Dhw:sndrpiwsp cset name='TX Playback Switch' off;  amixer -q -Dhw:sndrpiwsp cset name='RX Playback Switch' on; amixer -q -Dhw:sndrpiwsp cset name='AIF Playback Switch' on;
		if lr_swap:
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' AIF2RX2") #lr
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' AIF2RX2")
		else:
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' AIF2RX1") #both left
			os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' AIF2RX2; amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' AIF2RX2") #both right
		os.system("amixer -q -Dhw:sndrpiwsp cset 'name=AIF1TX1 Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset 'name=AIF1TX2 Input 1' AIF2RX2") #set recording input

def init_audio(aux_in=False,lr_swap=False):
	"""Initialize the audio settings for Valhalla. Can use either aux line in (aux) or computer (SPDIF, which is AIF2RX)"""
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2 Digital Switch' on")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1 Digital Switch' on")
	os.system("amixer -q -Dhw:sndrpiwsp cset 'name=HPOUT2 Digital Volume' 160")
	os.system("amixer -q -Dhw:sndrpiwsp cset 'name=HPOUT1 Digital Volume' 150")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 2' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 2' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 2' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 2' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX1 Input 1' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX2 Input 1' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX1 Input 2' None")
	os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX2 Input 2' None")
	set_audio(aux_in,lr_swap)
	'''
	if aux:
		os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' IN3R") #lr
		os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' IN3R")
		#set capture device to IN3
		os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX1 Input 1' IN3L; amixer -q -Dhw:sndrpiwsp cset name='AIF1TX2 Input 1' IN3R;")
	else:
		os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT2L Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset name='HPOUT2R Input 1' AIF2RX2") #lr
		os.system("amixer -q -Dhw:sndrpiwsp cset name='HPOUT1L Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset name='HPOUT1R Input 1' AIF2RX2")
		#set capture device to AIF2RX
		os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX1 Input 1' AIF2RX1; amixer -q -Dhw:sndrpiwsp cset name='AIF1TX2 Input 1' AIF2RX2;")
	'''
	os.system("amixer -q -Dhw:sndrpiwsp cset name='AIF1TX1 Input 1 Volume' 40; amixer -q -Dhw:sndrpiwsp cset name='AIF1TX2 Input 1 Volume' 40") #set capture volume

def get_audio_input():
	# import code
	# code.interact(local=locals()) #http://stackoverflow.com/questions/2158097/drop-into-python-interpreter-while-executing-function
	input = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NORMAL, 'sndrpiwsp')
	input.setchannels(Audio.NUM_CHANNELS)
	input.setformat(aa.PCM_FORMAT_S16_LE)
	input.setrate(Audio.SAMPLE_RATE)
	input.setperiodsize(Audio.PERIOD_SIZE)
	return input

def update_frequency_limits_with_columns(columns):
	Audio.COLUMNS = columns
	Audio.FREQUENCY_LIMITS = calculate_column_frequency(200, 10000, columns)

