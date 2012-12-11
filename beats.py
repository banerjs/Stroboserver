#!/usr/bin/env python2.7
import wave
import sys
import struct
import itertools
import numpy as np

from numpy import pi

ENERGY_THRESHOLD = 1.5
NUM_INSTANT_FRAMES = 1024

class Music:
    def __init__(self, nchannels=1, framerate=44100, nframes=0, subbands=NUM_INSTANT_FRAMES/32):
        self.nchannels = nchannels
        self.framerate = framerate
        self.nframes = nframes
        self.subbands = subbands
        self.ninstantframes = NUM_INSTANT_FRAMES  # Set this is a global default
        self.lchannel = None
        self.rchannel = None

        # Calculate the number of energy samples required for an avg (navgcalc)
        sampletime = 1.0/float(framerate)
        self.instantime = self.ninstantframes*sampletime # Time considered as an instant
        self.navgcalc = int(1/self.instantime)

        # Calculate the size of each subband
        self.subbandsize = self.ninstantframes/self.subbands

def read_wave(file_name):
    w = wave.open(file_name, 'r')
    (nchannels, sampwidth, framerate, nframes, comptype, compname) = w.getparams()

    print w.getparams()

    frames = w.readframes(nframes*nchannels)
    out = struct.unpack_from('%dh' % nframes*nchannels, frames)

    if nchannels == 2:
        left = np.array(out[0::2])
        right = np.array(out[1::2])
    else:
        left = np.array(out)
        right = left

    music = Music(nchannels, framerate, nframes)
    music.lchannel = left
    music.rchannel = right

    return music

def get_subband_energies(music):
    counter = 0
    ic = 0
    energies = np.zeros([music.nframes/music.ninstantframes+1, music.subbands])
    sound = music.lchannel + 1j*music.rchannel
    while ic < music.nframes:
        FFT = abs(np.fft.fft(sound[ic:ic+music.ninstantframes], music.ninstantframes))
        for i in xrange(music.subbands):
            energies[counter,i] = np.dot(FFT[i*music.subbandsize:(i+1)*music.subbandsize],
                                         FFT[i*music.subbandsize:(i+1)*music.subbandsize])
        ic = ic + music.ninstantframes
        counter = counter + 1
    return energies

def get_global_beats(music):
    global ENERGY_THRESHOLD

    # Define the variables for the algorithm
    energy_history = np.zeros([music.navgcalc, 1])
    ic = 0 # Counter for the number of instants considered
    max_counter = music.nframes/music.ninstantframes
    beats = np.zeros([max_counter, 1])

    # Initialize the variables for the algorithm
    for i in range(music.navgcalc):
        energy_history[i] = np.dot(music.lchannel[ic:(ic+music.ninstantframes)],
                                   music.lchannel[ic:(ic+music.ninstantframes)]) + \
                            np.dot(music.rchannel[ic:(ic+music.ninstantframes)],
                                   music.rchannel[ic:(ic+music.ninstantframes)])
        ic = ic + music.ninstantframes

    # Discover and record the beats
    counter = 0
    while ic < music.nframes:
        inst_energy = energy_history[0]
        avg_energy = 1.0/float(music.navgcalc) * np.sum(energy_history)
        beats[counter] = inst_energy/avg_energy if inst_energy > avg_energy else 0

        counter = counter + 1
        energy_history = np.roll(energy_history, -1)
        energy_history[-1] = np.dot(music.lchannel[ic:(ic+music.ninstantframes)],
                                    music.lchannel[ic:(ic+music.ninstantframes)]) + \
                             np.dot(music.rchannel[ic:(ic+music.ninstantframes)],
                                    music.rchannel[ic:(ic+music.ninstantframes)])
        ic = ic + music.ninstantframes

    music.beats = beats
    return music

def get_subband_beats(music, energies):
    beats = np.zeros(energies.shape)
    for counter in xrange(energies.shape[0]):
        buff = energies[counter:counter+music.navgcalc,:]
        avg = (1.0/buff.shape[0])*np.sum(buff,0)
        for i in xrange(energies.shape[1]):
            beats[counter,i] = energies[counter,i]/avg[i] if energies[counter,i] > avg[i] else 0

    music.beats = beats
    return music

def get_beat_frequencies(music, use_minute=True): # Options to selectively use frequency; and option for minutes
    if use_minute:
        minute = int(60/music.instantime)
    else:
        minute = music.beats.shape[0]

    FFT = abs(np.fft.fft(music.beats[0:2*minute,:]))

    return FFT

def get_subchannel_beat(music, FFT):
    index = np.argmax(FFT[0:FFT.shape[0]/2,:],0)
    magnitude = FFT[index, range(FFT.shape[1])]
    freq = np.fft.fftfreq(FFT.shape[0],music.instantime)[index]
    data = dict(itertools.izip(range(FFT.shape[0]),itertools.izip(freq,magnitude)))
    return data

if __name__ == '__main__':
    np.set_printoptions(threshold='nan')
    music = read_wave(sys.argv[1])
#    music = get_global_beats(music)
    energies = get_subband_energies(music)
    music = get_subband_beats(music,energies)
    FFT = get_beat_frequencies(music)
    print get_subchannel_beat(music, FFT)

    t = np.arange(0,(float(music.nframes)/music.ninstantframes)*music.instantime, music.instantime)
    freq = np.fft.fftfreq(FFT.shape[0],music.instantime)

#     for i in xrange(0,32,2):
#         pylab.subplot(4,4,i/2)
#         pylab.plot(freq,FFT[:,i],'x')
#     pylab.draw()

#     pylab.figure()
#     for i in xrange(0,32,2):
#         pylab.subplot(4,4,i/2)
#         pylab.plot(t,music.beats[:,i])

#     acc = lambda t: 10*np.sin(2*pi*2.0*t) + 5*np.sin(2*pi*8.0*t) + 2*np.random.random(len(t))
#     music.beats = acc(t)
#     pylab.show()
