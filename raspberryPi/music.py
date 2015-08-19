import logging

import alsaaudio as aa

from numpy import sum as npsum
from numpy import abs as npabs
from numpy import log10, log2, frombuffer, empty, hanning, fft, delete, int16, zeros

import urllib2

from decoder import decoder


CHUNK_SIZE = 2048

def read_music_from_url(url="http://mp3.streampower.be/radio1-high.mp3", chunk_size=CHUNK_SIZE, play_audio=False):

    #f=file('via_url.mp3', 'w')

    url=urllib2.urlopen(url)

    sample_rate = 44100 #musicfile.getframerate()
    num_channels = 2 #musicfile.getnchannels()

    if play_audio:
        output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
        output.setchannels(num_channels)
        output.setrate(sample_rate)
        output.setformat(aa.PCM_FORMAT_S16_LE)
        output.setperiodsize(CHUNK_SIZE)

    while True:
        #f.write(url.read(CHUNK_SIZE))
        chunk = url.read(CHUNK_SIZE)
        if len(chunk) == 0:
            break
        if play_audio:
            output.write(chunk)

        yield chunk, sample_rate


def read_musicfile_in_chunks(path, chunk_size=CHUNK_SIZE, play_audio=True):
    """ Read the music file at the given path, in chunks of the given size. """

    musicfile = decoder.open(path)
    sample_rate = musicfile.getframerate()
    num_channels = musicfile.getnchannels()

    if play_audio:
        output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL, 'sndrpiwsp')
        output.setchannels(num_channels)
        output.setrate(sample_rate)
        output.setformat(aa.PCM_FORMAT_S16_LE)
        output.setperiodsize(chunk_size)

    # fixme: we could do the writing to audio in a thread ... ?

    while True:
        chunk = musicfile.readframes(chunk_size)
        if len(chunk) == 0:
            break
        if play_audio:
            output.write(chunk)

        yield chunk, sample_rate


def calculate_column_frequency(min_frequency, max_frequency, columns):
    """Split the given frequency range in 'column' number of ranges.

    The function splits up the given range into smaller ranges, which have
    equal number of octaves.

    """

    logging.debug('Calculating frequencies for %d columns.', columns)
    octaves = log2(max_frequency / min_frequency)
    logging.debug('Octaves in selected frequency range ... %s', octaves)
    octaves_per_column = octaves / columns

    frequency_limits = [
        min_frequency * 2**(octaves_per_column*n) for n in range(columns+1)
    ]

    return zip(frequency_limits[:-1], frequency_limits[1:])


def piff(val, sample_rate, chunk_size):
    """Return the power array index corresponding to a particular frequency."""

    return int(chunk_size * val / sample_rate)



#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
"""FFT methods for computing / analyzing frequency response of audio.

This is simply a wrapper around FFT support in numpy.

Initial FFT code inspired from the code posted here:
http://www.raspberrypi.org/phpBB3/viewtopic.php?t=35838&p=454041

Optimizations from work by Scott Driscoll:
http://www.instructables.com/id/Raspberry-Pi-Spectrum-Analyzer-with-RGB-LED-Strip-/

Third party dependencies:

numpy: for FFT calculation - http://www.numpy.org/
"""
def calculate_levels(data, chunk_size, sample_rate, frequency_limits, num_bins, input_channels=2):
    """Calculate frequency response for each channel defined in frequency_limits

    :param data: decoder.frames(), audio data for fft calculations
    :type data: decoder.frames

    :param chunk_size: chunk size of audio data
    :type chunk_size: int

    :param sample_rate: audio file sample rate
    :type sample_rate: int

    :param frequency_limits: list of frequency_limits
    :type frequency_limits: list

    :param num_bins: length of gpio to process
    :type num_bins: int

    :param input_channels: number of audio input channels to process for (default=2)
    :type input_channels: int

    :return:
    :rtype: numpy.array
    """

    # create a numpy array, taking just the left channel if stereo
    data_stereo = frombuffer(data, dtype=int16)
    if input_channels == 2:

        # data has 2 bytes per channel
        data = empty(len(data) / (2 * input_channels))

        # pull out the even values, just using left channel
        data[:] = data_stereo[::2]
    elif input_channels == 1:
        data = data_stereo

    # if you take an FFT of a chunk of audio, the edges will look like
    # super high frequency cutoffs. Applying a window tapers the edges
    # of each end of the chunk down to zero.
    data = data * hanning(len(data))

    # Apply FFT - real data
    fourier = fft.rfft(data)

    # Remove last element in array to make it the same size as chunk_size
    fourier = delete(fourier, len(fourier) - 1)

    # Calculate the power spectrum
    power = npabs(fourier) ** 2

    matrix = zeros(num_bins, dtype='float64')

    for pin in range(num_bins):
        # take the log10 of the resulting sum to approximate how human ears 
        # perceive sound levels
        
        # Get the power array index corresponding to a particular frequency.
        idx1 = int(chunk_size * frequency_limits[pin][0] / sample_rate)
        idx2 = int(chunk_size * frequency_limits[pin][1] / sample_rate)
        
        # if index1 is the same as index2 the value is an invalid value
        # we can fix this by incrementing index2 by 1, This is a temporary fix
        # for RuntimeWarning: invalid value encountered in double_scalars
        # generated while calculating the standard deviation.  This warning
        # results in some channels not lighting up during playback.
        if idx1 == idx2:
            idx2 += 1
        
        npsums = npsum(power[idx1:idx2:1])
        
        # if the sum is 0 lets not take log10, just use 0
        # eliminates RuntimeWarning: divide by zero encountered in log10, does not insert -inf
        if npsums == 0:
            matrix[pin] = 0
        else:
            matrix[pin] = log10(npsums)

    return matrix

# I left this in as an entirely different method, so I can just command-f in the future
# and remove all of the "alternate_..." functionality
import numpy as np
def alternate_calculate_levels(data, sample_rate, frequency_limits, channels=2, bits=16):
    """Calculate frequency response for each channel

    Initial FFT code inspired from the code posted here:
    http://www.raspberrypi.org/phpBB3/viewtopic.php?t=35838&p=454041

    Optimizations from work by Scott Driscoll:
    http://www.instructables.com/id/Raspberry-Pi-Spectrum-Analyzer-with-RGB-LED-Strip-/

    """

    # create a numpy array. This won't work with a mono file, stereo only.
    data_stereo = np.frombuffer(data, dtype=getattr(np, 'int%s' % bits, np.int16))
    data = data_stereo[::channels]  # pull out the left channel

    # if you take an FFT of a chunk of audio, the edges will look like
    # super high frequency cutoffs. Applying a window tapers the edges
    # of each end of the chunk down to zero.
    window = np.hanning(len(data))
    data = data * window

    # Apply FFT - real data
    # We drop the last element in array to make it the same size as CHUNK_SIZE
    fourier = np.fft.rfft(data)[:-1]

    # Calculate the power spectrum
    power = np.abs(fourier) ** 2

    # Filter out noise?
    power2 = power * (power > (np.max(power) + np.min(power))/2.0)

    columns = len(frequency_limits)
    chunk_size = len(power)

    matrix = []
    matrix2 = []

    for i in range(columns):
        left_index = piff(frequency_limits[i][0], sample_rate, chunk_size)
        right_index = piff(frequency_limits[i][1], sample_rate, chunk_size)
        if left_index == right_index:
            right_index += 1
            cheat_factor = 0.5
        else:
            cheat_factor = 1

        # take the log10 of the resulting sum to approximate how human ears
        # perceive sound levels

        matrix.append(
            np.log10(np.sum(power[left_index:right_index])) * cheat_factor
        )
        matrix2.append(
            np.log10(np.sum(power2[left_index:right_index])) * cheat_factor
        )

    return matrix2


if __name__ == '__main__':

    frequency_limits =  calculate_column_frequency(400, 12000, 8)

    for chunk, sample_rate in read_musicfile_in_chunks('sample.mp3', play_audio=True):
        # data = calculate_levels(chunk, sample_rate, frequency_limits)
        pass
