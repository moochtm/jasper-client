# -*- coding: utf-8 -*-
import unittest

from jasper import testutils
from . import sonos_control

# TODO: write sonos Plugin test cases (look at some of the other more complicated plugins, like the MPD one perhaps.

class TestSonosPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = testutils.get_plugin_instance(sonos_control.SonosPlugin)

    def test_is_valid_method(self):
        self.assertTrue(self.plugin.is_valid("Play something by Tower of Power"))
        self.assertFalse(self.plugin.is_valid("Turn on BBC Radio 4"))
        self.assertTrue(self.plugin.is_valid("Turn the volume down in the kitchen"))

    def test_handle_method(self):
        mic = testutils.TestMic()
        self.plugin.analyse("What time is it?", mic)
        self.assertEqual(len(mic.outputs), 1)
        self.assertIn("It is", mic.outputs[0])
