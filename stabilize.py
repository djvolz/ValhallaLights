import time

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
	if time_difference > 1.0:
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
