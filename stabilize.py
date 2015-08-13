import time

class Lights:
	time_of_last_intensity_reset = time.time()
	music_min_intensity                = -1.0
	music_max_intensity                = -1.0  # this is an arbitrary max. I never really see values above 15.0


# Reset the light intensity range every so many seconds
# that way a really loud song won't mess with the values
# of a really soft song
def stabilize_light_intensities():
	# Get the time since the last reset
	time_current = time.time()
	time_difference = time_current - Lights.time_of_last_intensity_reset 

	# reset the intensity values every 10 seconds
	if time_difference > 10.0:
		Lights.music_min_intensity                = -1.0
		Lights.music_max_intensity                = -1.0
		Lights.time_of_last_intensity_reset = time.time()

# Dynamically update the possible light intensity range
def check_if_val_within_intensity_ranges(val):
	# -inf happens when processing the song. Just make it the min
	if val == float("-inf"):
		val = Lights.music_min_intensity
	# Check if min value has been reset
	if Lights.music_min_intensity  == -1.0:
		Lights.music_min_intensity = val
		Lights.music_max_intensity = val + 1.0

	# If the value is less than the current min, 
	# then the new current min is the value
	if val < Lights.music_min_intensity:
		Lights.music_min_intensity = val

	# Same logic as min reversed for the max value
	elif val > Lights.music_max_intensity:
		Lights.music_max_intensity = val

	# Uncomment to check how those ranges are doing
	# print(Lights.music_min_intensity)
	# print(Lights.music_max_intensity)
	return val, Lights