__author__ = 'Matt Barr'

# build in modules
import logging

# third party modules
import soco

class SonosNetwork():
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._zones = [Sonos(zone) for zone in list(soco.discover())]

    def speakers_exist(self):
        if len(self._zones) > 0:
            return True
        return False

    def get_group_names(self):
        result = [sonos.player_name for sonos in self._zones if sonos.is_coordinator]
        return result

    def __getitem__(self, item):
        if isinstance(item, basestring):
            result = [sonos for sonos in self._zones if sonos.player_name.lower() == item]
            if not result:
                self._logger.warning('__getitem__ says player_name not found.')
                return None
            return result[0]
        elif isinstance(item, int):
            if item >= len(self._zones):
                self._logger.warning('__getitem__ says sonos index not found.')
                return None
            return self._zones[item]
        else:
            self._logger.warning('__getitem__ says you need to provide a string or an integer.')
            return None

class Sonos():
    def __init__(self, zone):
        self._soco = zone
        self.player_name = self._soco.player_name
        self.is_coordinator = self._soco.is_coordinator

    def set_power(self, state):
        if state == 'on':
            self._soco.play()
        elif state == 'off':
            self._soco.pause()
        else:
            self._logger.error('Unrecognized state for set_power: %s.' % state)
            return None


#  self.sonos = list(soco.discover())[0].group.coordinator

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    print soco.discover()
    sn = SonosNetwork()
    print sn.get_group_names()