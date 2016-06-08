# -*- coding: utf-8-*-
"""
    The Mic class handles all interactions with the microphone and speaker.
"""
import logging
import tempfile
import wave
import audioop
import pyaudio
import alteration
import jasperpath

import requests
from array import array
import struct
import math
import json

class Mic:

    speechRec = None
    speechRec_persona = None

    def __init__(self, speaker, passive_stt_engine, active_stt_engine):
        """
        Initiates the pocketsphinx instance.

        Arguments:
        speaker -- handles platform-independent audio output
        passive_stt_engine -- performs STT while Jasper is in passive listen
                              mode
        acive_stt_engine -- performs STT while Jasper is in active listen mode
        """
        self._logger = logging.getLogger(__name__)
        self.speaker = speaker
        self.passive_stt_engine = passive_stt_engine
        self.active_stt_engine = active_stt_engine
        self._logger.info("Initializing PyAudio. ALSA/Jack error messages " +
                          "that pop up during this process are normal and " +
                          "can usually be safely ignored.")
        self._audio = pyaudio.PyAudio()
        self._logger.info("Initialization of PyAudio completed.")

    def __del__(self):
        self._audio.terminate()

    def getScore(self, data):
        rms = audioop.rms(data, 2)
        score = rms / 3
        return score

    def fetchThreshold(self):

        # TODO: Consolidate variables from the next three functions
        THRESHOLD_MULTIPLIER = 1.8
        RATE = 16000
        CHUNK = 1024

        # number of seconds to allow to establish threshold
        THRESHOLD_TIME = 1

        # prepare recording stream
        stream = self._audio.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)

        # stores the audio data
        frames = []

        # stores the lastN score values
        lastN = [i for i in range(20)]

        # calculate the long run average, and thereby the proper threshold
        for i in range(0, RATE / CHUNK * THRESHOLD_TIME):

            data = stream.read(CHUNK)
            frames.append(data)

            # save this data point as a score
            lastN.pop(0)
            lastN.append(self.getScore(data))
            average = sum(lastN) / len(lastN)

        stream.stop_stream()
        stream.close()

        # this will be the benchmark to cause a disturbance over!
        THRESHOLD = average * THRESHOLD_MULTIPLIER

        return THRESHOLD

    # TODO: Mic shouldn't be processing audio - should be Conversation that has "passiveListen"
    def passiveListen(self, PERSONA):
        """
        Listens for PERSONA in everyday sound. Times out after LISTEN_TIME, so
        needs to be restarted.
        """

        THRESHOLD_MULTIPLIER = 1.8
        RATE = 16000
        CHUNK = 1024

        # number of seconds to allow to establish threshold
        THRESHOLD_TIME = 1

        # number of seconds to listen before forcing restart
        LISTEN_TIME = 10

        # prepare recording stream
        stream = self._audio.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)

        # stores the audio data
        frames = []

        # stores the lastN score values
        lastN = [i for i in range(30)]

        # calculate the long run average, and thereby the proper threshold
        for i in range(0, RATE / CHUNK * THRESHOLD_TIME):

            data = stream.read(CHUNK)
            frames.append(data)

            # save this data point as a score
            lastN.pop(0)
            lastN.append(self.getScore(data))
            average = sum(lastN) / len(lastN)

        # this will be the benchmark to cause a disturbance over!
        THRESHOLD = average * THRESHOLD_MULTIPLIER

        # save some memory for sound data
        frames = []

        # flag raised when sound disturbance detected
        didDetect = False

        # start passively listening for disturbance above threshold
        for i in range(0, RATE / CHUNK * LISTEN_TIME):

            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)

            if score > THRESHOLD:
                didDetect = True
                break

        # no use continuing if no flag raised
        if not didDetect:
            print "No disturbance detected"
            stream.stop_stream()
            stream.close()
            return (None, None)

        # cutoff any recording before this disturbance was detected
        frames = frames[-20:]

        # otherwise, let's keep recording for few seconds and save the file
        DELAY_MULTIPLIER = 1
        for i in range(0, RATE / CHUNK * DELAY_MULTIPLIER):

            data = stream.read(CHUNK)
            frames.append(data)

        # save the audio data
        stream.stop_stream()
        stream.close()

        with tempfile.NamedTemporaryFile(mode='w+b') as f:
            wav_fp = wave.open(f, 'wb')
            wav_fp.setnchannels(1)
            wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wav_fp.setframerate(RATE)
            wav_fp.writeframes(''.join(frames))
            wav_fp.close()
            f.seek(0)
            # check if PERSONA was said
            self._logger.debug("Starting Passive STT transcription")
            transcribed = self.passive_stt_engine.transcribe(f)
            self._logger.debug("Finished Passive STT transcription")

        if any(PERSONA in phrase for phrase in transcribed):
            return (THRESHOLD, PERSONA)

        return (False, transcribed)

    # TODO: Mic shouldn't be processing audio - should be Conversation that has "activeListen"
    def activeListen(self, THRESHOLD=None, LISTEN=True, MUSIC=False):
        """
            Records the command and returns the transcribed speech
        """
        if 'engine_mode' in self.active_stt_engine.get_config() and \
            self.active_stt_engine.get_config()['engine_mode'] == 'stream':
            options = self.activeListenToAllOptionsWithStreaming(THRESHOLD, LISTEN, MUSIC)
        else:
            options = self.activeListenToAllOptions(THRESHOLD, LISTEN, MUSIC)
        if options:
            return options

    # TODO: Mic shouldn't be processing audio - should be Conversation that has "activeListen"
    def activeListenToAllOptions(self, THRESHOLD=None, LISTEN=True,
                                 MUSIC=False):
        """
            Records until a second of silence or times out after 12 seconds

            Returns a list of the matching options or None
        """
        self._logger.info("Starting Active Listening with Streaming")

        RATE = 16000
        CHUNK = 1024
        LISTEN_TIME = 12

        # check if no threshold provided
        if THRESHOLD is None:
            THRESHOLD = self.fetchThreshold()

        self.speaker.play(jasperpath.data('audio', 'beep_hi.wav'))

        # prepare recording stream
        stream = self._audio.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)

        frames = []
        # increasing the range # results in longer pause after command
        # generation
        lastN = [THRESHOLD * 1.2 for i in range(30)]

        for i in range(0, RATE / CHUNK * LISTEN_TIME):

            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)

            lastN.pop(0)
            lastN.append(score)

            average = sum(lastN) / float(len(lastN))

            # TODO: 0.8 should not be a MAGIC NUMBER!
            if average < THRESHOLD * 0.8:
                break

        self.speaker.play(jasperpath.data('audio', 'beep_lo.wav'))

        # save the audio data
        stream.stop_stream()
        stream.close()

        with tempfile.SpooledTemporaryFile(mode='w+b') as f:
            wav_fp = wave.open(f, 'wb')
            wav_fp.setnchannels(1)
            wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wav_fp.setframerate(RATE)
            wav_fp.writeframes(''.join(frames))
            wav_fp.close()
            f.seek(0)
            return self.active_stt_engine.transcribe(f)

    # TODO: Mic shouldn't be processing audio - should be Conversation that has "activeListen"
    def activeListenToAllOptionsWithStreaming(self, THRESHOLD=None, LISTEN=True,
                                 MUSIC=False):
        """

        Args:
            THRESHOLD:
            LISTEN:
            MUSIC:

        Returns:

        """
        self._logger.info("Starting Active Listening with Streaming")

        print THRESHOLD
        self.THRESHOLD = .01
        #if THRESHOLD is None:
        #self.THRESHOLD = self.fetchThreshold()

        self.CHUNK_SIZE = 8192
        self.FORMAT = pyaudio.paInt16
        self.RATE = 8000
        self.SHORT_NORMALIZE = (1.0 / 32768.0)
        self.access_key = 'D44WWDTJUDTXDNVOBJGWKOUNWMWA76IF'  # Your wit.ai key should go here.

        p = pyaudio.PyAudio()

        self.speaker.play(jasperpath.data('audio', 'beep_hi.wav'))
        stream = p.open(format=self.FORMAT, channels=1, rate=self.RATE,
                        input=True, output=True,
                        frames_per_buffer=self.CHUNK_SIZE)

        foo = requests.post(self.active_stt_engine.url, headers=self.active_stt_engine.headers, data=self.gen(p, stream))

        self.speaker.play(jasperpath.data('audio', 'beep_lo.wav'))

        stream.stop_stream()
        stream.close()
        p.terminate()

        result = json.loads(foo.text)

        if '_text' in result:
            return [result['_text']]

        return None

    # TODO: replace with code in other mic
    # Returns if the RMS of block is less than the threshold
    def is_silent(self, block):
        count = len(block) / 2
        form = "%dh" % (count)
        shorts = struct.unpack(form, block)
        sum_squares = 0.0

        for sample in shorts:
            n = sample * self.SHORT_NORMALIZE
            sum_squares += n * n

        rms_value = math.sqrt(sum_squares / count)
        return rms_value, rms_value <= self.THRESHOLD

    # TODO: replace with code in other mic
    # Returns as many (up to returnNum) blocks as it can.
    def returnUpTo(self, iterator, values, returnNum):
        if iterator + returnNum < len(values):
            return (iterator + returnNum,
                    "".join(values[iterator:iterator + returnNum]))

        else:
            temp = len(values) - iterator
            return (iterator + temp + 1, "".join(values[iterator:iterator + temp]))

    # TODO: replace with code in other mic
    # Python generator- yields roughly 512k to generator.
    def gen(self, p, stream):
        num_silent = 0
        snd_started = False
        start_pack = 0
        counter = 0
        print "Microphone on!"
        i = 0
        data = []

        while 1:
            rms_data = stream.read(self.CHUNK_SIZE)
            snd_data = array('i', rms_data)
            for d in snd_data:
                data.append(struct.pack('<i', d))

            rms, silent = self.is_silent(rms_data)

            if silent and snd_started:
                num_silent += 1
                print "NUM_SILENT: %s" % str(num_silent)

            elif not silent and not snd_started:
                i = len(data) - self.CHUNK_SIZE * 2  # Set the counter back a few seconds
                if i < 0:  # so we can hear the start of speech.
                    i = 0
                snd_started = True
                print "TRIGGER at " + str(rms) + " rms."

            elif not silent and snd_started and not i >= len(data):
                i, temp = self.returnUpTo(i, data, 1024)
                yield temp
                num_silent = 0

            if snd_started and num_silent > 1:
                print "Stop Trigger"
                break

            if counter > 75:  # Slightly less than 10 seconds.
                print "Timeout, Stop Trigger"
                break

            if snd_started:
                counter = counter + 1

        # Yield the rest of the data.
        print "Pre-streamed " + str(i) + " of " + str(len(data)) + "."
        while (i < len(data)):
            i, temp = self.returnUpTo(i, data, 512)
            yield temp
        print "Swapping to thinking."

    def say(self, phrase,
            OPTIONS=" -vdefault+m3 -p 40 -s 160 --stdout > say.wav"):
        # alter phrase before speaking
        phrase = alteration.clean(phrase)
        self.speaker.say(phrase)
