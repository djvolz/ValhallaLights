import os
import alsaaudio as aa
from library.music import calculate_column_frequency


class Constants:
	# DECODER CONSTANTS
	COLUMNS          = 2
	SAMPLE_RATE      = 44100
	NUM_CHANNELS     = 2
	PERIOD_SIZE      = 2048
	FREQUENCY_LIMITS = calculate_column_frequency(200, 10000, COLUMNS)

def set_audio(aux_in, lr_swap):
	#HPOUT2 is the emotiva/klipsch (left)
	#HPOUT1 is the pioneer (right)
	#IN3 is the aux in
	#AIF2RX2 is the SPDIF in (if setup correctly)
	if aux_in:
		if lr_swap:
			os.system("amixer -Dhw:0 cset name='HPOUT2L Input 1' IN3L; amixer -Dhw:0 cset name='HPOUT2R Input 1' IN3R") #lr
			os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1' IN3L; amixer -Dhw:0 cset name='HPOUT1R Input 1' IN3R")
		else:
			os.system("amixer -Dhw:0 cset name='HPOUT2L Input 1' IN3L; amixer -Dhw:0 cset name='HPOUT2R Input 1' IN3L") #both left
			os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1' IN3R; amixer -Dhw:0 cset name='HPOUT1R Input 1' IN3R") #both right
	else:
		if lr_swap:
			os.system("amixer -Dhw:0 cset name='HPOUT2L Input 1' AIF2RX1; amixer -Dhw:0 cset name='HPOUT2R Input 1' AIF2RX2") #lr
			os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1' AIF2RX1; amixer -Dhw:0 cset name='HPOUT1R Input 1' AIF2RX2")
		else:
			os.system("amixer -Dhw:0 cset name='HPOUT2L Input 1' AIF2RX1; amixer -Dhw:0 cset name='HPOUT2R Input 1' AIF2RX1") #both left
			os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1' AIF2RX2; amixer -Dhw:0 cset name='HPOUT1R Input 1' AIF2RX2") #both right

def init_audio(aux=True):
	"""Initialize the audio settings for V alhalla. Can use either aux line in (aux) or computer (SPDIF, which is AIF2RX)"""
	os.system("amixer -Dhw:0 cset name='HPOUT2 Digital Switch' on")
	os.system("amixer -Dhw:0 cset name='SPDIF in Switch' on; amixer -Dhw:0 cset name='TX Playback Switch' off; amixer -Dhw:0 cset name='RX Playback Switch' on; amixer -Dhw:0 cset name='AIF Playback Switch' on;")
	if aux:
		os.system("amixer -Dhw:0 cset name='HPOUT2L Input 1' IN3L; amixer -Dhw:0 cset name='HPOUT2R Input 1' IN3R") #lr
		os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1' IN3L; amixer -Dhw:0 cset name='HPOUT1R Input 1' IN3R")
		#set capture device to IN3
		os.system("amixer -Dhw:0 cset name='AIF1TX1 Input 1' IN3L; amixer -Dhw:0 cset name='AIF1TX2 Input 1' IN3R;")
	else:
		os.system("amixer -Dhw:0 cset name='HPOUT2L Input 1' AIF2RX1; amixer -Dhw:0 cset name='HPOUT2R Input 1' AIF2RX2") #lr
		os.system("amixer -Dhw:0 cset name='HPOUT1L Input 1' AIF2RX1; amixer -Dhw:0 cset name='HPOUT1R Input 1' AIF2RX2")
		#set capture device to AIF2RX
		os.system("amixer -Dhw:0 cset name='AIF1TX1 Input 1' AIF2RX1; amixer -Dhw:0 cset name='AIF1TX2 Input 1' AIF2RX2;")
		os.system("amixer -Dhw:0 cset name='AIF1TX1 Input 1 Volume' 32; amixer -Dhw:0 cset name='AIF1TX2 Input 1 Volume' 32") #set capture volume

def get_audio_input():
	input = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NONBLOCK)
	input.setchannels(Constants.NUM_CHANNELS)
	input.setformat(aa.PCM_FORMAT_S16_BE)
	input.setrate(Constants.SAMPLE_RATE)
	input.setperiodsize(Constants.PERIOD_SIZE)
	return input

def update_frequency_limits_with_columns(columns):
	Constants.FREQUENCY_LIMITS = calculate_column_frequency(200, 10000, columns)

