import logging
import requests
from jasper import plugin

from ndev.core import NDEVCredentials, HEADER
from ndev.asr import ASR, ChunkedASRRequest

# There seems to be no way to get language setting of the defined app
# Last updated: April 06, 2016
SUPPORTED_LANG = (
    'de',
    'en',
    'es',
    'et',
    'fr',
    'it',
    'nl',
    'pl',
    'pt',
    'ru',
    'sv'
)
LANGUAGE = 'en_GB'


class NuanceSTTPlugin(plugin.STTPlugin):
    """
    Speech-To-Text implementation which relies on the Nuance API.

    This implementation requires Nuance credentials to be present in
    profile.yml. Please sign up at https://developer.nuance.com/ and copy
    your credential information, which can be found under My Account
    to your profile.yml:
        ...
        stt_engine: nuance
        nuance:
           appId: <YOUR APP ID>
           appKey: <YOUR APP KEY>
           asrUri: https://<YOUR ASR URI>
           ttsUri: https://<YOUR TTS URI>
    """

    def __init__(self, *args, **kwargs):
        """
        Create Plugin Instance
        """
        plugin.STTPlugin.__init__(self, *args, **kwargs)
        self._logger = logging.getLogger(__name__)
        try:
            self._app_id = self.profile['nuance']['appId']
        except KeyError:
            self._logger.error('You must provide a Nuance AppID in your profile.yml')
        try:
            self._app_key = self.profile['nuance']['appKey']
        except KeyError:
            self._logger.error('You must provide a Nuance AppKey in your profile.yml')
        try:
            self._asr_uri = self.profile['nuance']['asrUri']
        except KeyError:
            self._logger.error('You must provide a Nuance AppURI in your profile.yml')
        try:
            language = self.profile['language']
        except KeyError:
            language = 'en-US'
        if language.split('-')[0] not in SUPPORTED_LANG:
            raise ValueError('Language %s is not supported.',
                             language.split('-')[0])

    @property
    def token(self):
        """
        Return defined acess token.
        """
        return self._token

    @property
    def language(self):
        """
        Returns selected language
        """
        return self._language

    @property
    def headers(self):
        """
        Return headers
        """
        return self._headers

    def transcribe(self, fp):
        """
        transcribes given audio file by uploading to wit.ai and returning
        received text from json answer.
        """
        creds = NDEVCredentials(app_id=self._app_id, app_key=self._app_key, asr_url=self._asr_uri)
        # TODO: fix this being hard-wired to en_GB
        desired_asr_lang = ASR.get_language_input(LANGUAGE)
        filename = fp.name

        try:
            asr_req = ASR.make_request(creds=creds, desired_asr_lang=desired_asr_lang, filename=filename)

            if asr_req.response.was_successful():
                self._logger.info("%s" % asr_req.response.get_recognition_result())  # instead of looping through, pick head
            else:
                self._logger.info("%s" % asr_req.response.error_message)
        except Exception as e:
            print e
        else:
            text = asr_req.response.get_recognition_result()
            transcribed = [text.upper()]
            self._logger.info('Transcribed: %r', transcribed)
            return transcribed