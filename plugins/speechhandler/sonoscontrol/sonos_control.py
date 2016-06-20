# -*- coding: utf-8 -*-

# built in modules
import datetime, logging, os

# 3rd party modules
import yaml

# jasper modules
from jasper import app_utils
from jasper import plugin
from intent_analysis import IntentAnalysis
from sonos_client import SonosNetwork

# import dictionary
path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)
dictionary = yaml.load(open(os.path.join(dir_path, 'dictionary.yaml'), 'r'))

class SonosPlugin(plugin.SpeechHandlerPlugin):

    def get_phrases(self):
        return []

    def get_priority(self):
        return 100

    def handle(self, text, mic):
        """
        Controls Sonos speakers on the local network.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        """
        self._logger = logging.getLogger(__name__)

        # make sure there are Sonos speakers to control...
        sn = SonosNetwork()
        if not sn.speakers_exist():
            msg = 'No Sonos to control. Exiting.'
            self._logger.warning(msg)
            mic.say(msg)
            return

        # add the Sonos group names to the dictionary
        dictionary['sonos_group'] = {}
        for group_name in sn.get_group_names():
            dictionary['sonos_group'][group_name.lower()] = [group_name.lower()]

        #the IA class returns the intent
        ia = IntentAnalysis(text, self.profile, dictionary)

        # the SonosPlugin class takes the intent, and converts it to commands
        # the SonosPlugin executes the commands using the SonosControl plugin
        # the SonosControl plugin is an interface to SoCo - it pass through some
        for intent in ia.possible_intents:
            actions = intent.get_chunk_meaning_values(meaning_type='action')
            if len(actions) > 1:
                msg = 'This intent has too many actions: %s' % actions
                self._logger.warning(msg)
                mic.say(msg)
                break

            action = actions[0]
            if action == 'play':
                pass

            elif action == 'pause':
                pass

            elif action == 'set':
                # get the target Sonos group
                sonos_groups = intent.get_chunk_meaning_values(meaning_type='sonos_group')
                if len(sonos_groups) == 0:
                    # look for a default group in the profile
                    try:
                        sonos_groups = [self.profile['sonos_control']['default_group']]
                    except:
                        msg = 'This intent has no target Sonos group'
                        self._logger.warning(msg)
                        mic.say(msg)
                        break

                # need to know what we're setting the thing to
                targets = intent.get_chunk_meaning_values(meaning_type='target')
                if len(targets) > 1:
                    msg = 'This intent has too many target values: %s' % targets
                    self._logger.warning(msg)
                    mic.say(msg)
                    break

                target = targets[0]
                if target in ['on', 'off']:
                    # assume we're turning speakers on or off, which means play or pause
                    for group in sonos_groups:
                        sn[group].set_power(target)

            else:
                msg = 'Unhandled action: %s' % action
                self._logger.warning(msg)
                mic.say(msg)
                break



        mic.say("done!")


    def is_valid(self, text):
        """
        Returns True if input is related to the time.

        Arguments:
        text -- user-input, typically transcribed speech
        """
        #self._logger.debug("is_valid defaulting to True")
        return True
