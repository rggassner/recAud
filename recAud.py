#!/usr/bin/python3
from array import array
from struct import pack
from sys import byteorder
import pyaudio, wave, copy, os, sys, time

OUTPUTDIR="output"
INPUT_DEVICE_INDEX = 2
CHANNELS = 1
SECONDS = 60
THRESHOLD = 200 #100 high sensibility - 500 low sensibility
CHUNK_SIZE = 1024
RATE = 48000 # 44100 4800
SILENT_CHUNKS = SECONDS * RATE / CHUNK_SIZE
FORMAT = pyaudio.paInt16
FRAME_MAX_VALUE = 2 ** 15 - 1
NORMALIZE_MINUS_ONE_dB = 10 ** (-1.0 / 20)

class suppress_stderr(object):
    def __enter__(self):
        self.errnull_file = open(os.devnull, 'w')
        self.old_stderr_fileno_undup    = sys.stderr.fileno()
        self.old_stderr_fileno = os.dup ( sys.stderr.fileno() )
        self.old_stderr = sys.stderr
        os.dup2 ( self.errnull_file.fileno(), self.old_stderr_fileno_undup )
        sys.stderr = self.errnull_file
        return self

    def __exit__(self, *_):
        sys.stderr = self.old_stderr
        os.dup2 ( self.old_stderr_fileno, self.old_stderr_fileno_undup )
        os.close ( self.old_stderr_fileno )
        self.errnull_file.close()

def is_silent(data_chunk):
    return max(data_chunk) < THRESHOLD

def normalize(data_all):
    normalize_factor = (float(NORMALIZE_MINUS_ONE_dB * FRAME_MAX_VALUE) / max(abs(i) for i in data_all))
    r = array('h')
    for i in data_all:
        r.append(int(i * normalize_factor))
    return r

def record():
    p = pyaudio.PyAudio()

    #info = p.get_host_api_info_by_index(0)
    #numdevices = info.get('deviceCount')
    #for i in range(0, numdevices):
    #    if (p.get_device_info_by_host_api_device_index(0,i).get('maxInputChannels')) > 0:
    #        print('Input device ID', i,' - ', p.get_device_info_by_host_api_device_index(0,i).get('name'))

    stream = p.open(format=FORMAT, channels=CHANNELS,input_device_index=INPUT_DEVICE_INDEX, rate=RATE, input=True, output=True, frames_per_buffer=CHUNK_SIZE)
    silent_chunks = 0
    audio_started = False
    data_all = array('h')
    while True:
        data_chunk = array('h', stream.read(CHUNK_SIZE,exception_on_overflow = False))
        if byteorder == 'big':
            data_chunk.byteswap()
        silent = is_silent(data_chunk)
        if audio_started:
            data_all.extend(data_chunk)
            if silent:
                silent_chunks += 1
                if silent_chunks > SILENT_CHUNKS:
                    break
            else: 
                silent_chunks = 0
        elif not silent:
            print("Recording {}".format(time.ctime()))
            audio_started = True              
    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()
    data_all = normalize(data_all)
    return sample_width, data_all

def record_to_file():
    sample_width, data = record()
    data = pack('<' + ('h' * len(data)), *data)
    wave_file = wave.open(OUTPUTDIR+"/"+str(time.time())+".wav", 'wb')
    wave_file.setnchannels(CHANNELS)
    wave_file.setsampwidth(sample_width)
    wave_file.setframerate(RATE)
    wave_file.writeframes(data)
    wave_file.close()
    print("Done {}".format(time.ctime()))

if __name__ == '__main__':
    with suppress_stderr():
        while True:
            record_to_file()
