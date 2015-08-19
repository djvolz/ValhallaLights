# Stabilize
# Stabilization functions for FFT'ed music data. 
# (Filter out noise and scale values to values that can be displayed as light)
# Author: djvolz	8/19/15

import time
import numpy as np
import audio_setup
import logging


class Lights:
	time_of_last_intensity_reset = time.time()
	min_intensity                = -1.0
	max_intensity                = -1.0  # this is an arbitrary max. I never really see values above 15.0


# Reset the light intensity range every so many seconds
# that way a really loud song won't mess with the values
# of a really soft song
def stabilize_light_intensities():
	# Get the time since the last reset
	time_current = time.time()
	time_difference = time_current - Lights.time_of_last_intensity_reset 

	# reset the intensity values every set number of seconds
	if time_difference > 10.0:
		# print("LIGHT MIN AND MAX RESET")
		Lights.min_intensity                = -1.0   
		Lights.max_intensity                = -1.0
		# Lights.min_intensity                = Lights.min_intensity + 0.5   
		# Lights.max_intensity                = Lights.max_intensity - 0.5
		
		# prevent the min from growing larger than the max
		if Lights.min_intensity > Lights.max_intensity:
			print("Lights.intensities crossover!")
			Lights.min_intensity = Lights.max_intensity
			Lights.max_intensity = Lights.min_intensity + 0.1

		# set the new time last reset value to be current time
		Lights.time_of_last_intensity_reset = time.time()

# Dynamically update the possible light intensity range
def check_if_val_within_range(val):
	# -inf happens when processing the song. Just make it the min
	if val == float("-inf"):
		val = Lights.min_intensity

	# Check if min value has been reset
	# This is acutally usually taken care of by the 
	# stabilize_light_intensities() function, but this is a safety net
	if Lights.min_intensity  == -1.0:
		Lights.min_intensity = val
		Lights.max_intensity = val + 1.0

	# If the value is less than the current min, 
	# then the new current min is the value
	if val < Lights.min_intensity:
		Lights.min_intensity = val

	# Same logic as min reversed for the max value
	elif val > Lights.max_intensity:
		Lights.max_intensity = val

	# Uncomment to check how those ranges are doing
	# print("[%f, %f]" % (Lights.min_intensity, Lights.max_intensity))
	return val, Lights

# Scale the given value from the scale of src to the scale of dst.
def scale(val, src, dst):
	return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

# Keep track of the last N samples to compute a running std / mean
#
# TODO: Look into using this algorithm to compute this on a per sample basis:
# http://www.johndcook.com/blog/standard_deviation/   
def compute_running_average(data, mean, std, recent_samples, num_samples):             
	if num_samples >= audio_setup.Audio.MAX_SAMPLES:
		no_connection_ct = 0
		for i in range(0, audio_setup.Audio.COLUMNS):
			mean[i] = np.mean([item for item in recent_samples[:, i] if item > 0])
			std[i] = np.std([item for item in recent_samples[:, i] if item > 0])
			
			# Count how many channels are below 10, 
			# if more than 1/2, assume noise (no connection)
			if mean[i] < 10.0:
				no_connection_ct += 1
				
		# If more than 1/2 of the channels appear to be not connected, turn all off
		if no_connection_ct > audio_setup.Audio.COLUMNS / 2:
			logging.debug("no input detected, turning all lights off")
			mean = [20 for _ in range(audio_setup.Audio.COLUMNS)]
		else:
			logging.debug("std: " + str(std) + ", mean: " + str(mean))
		num_samples = 0
	else:
		for i in range(0, audio_setup.Audio.COLUMNS):
			recent_samples[num_samples][i] = data[i]
		num_samples += 1

	return mean, std, recent_samples, num_samples