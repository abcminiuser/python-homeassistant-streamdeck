#!/usr/bin/env python

#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

from StreamDeck.StreamDeck import DeviceManager
from HomeAssistantWS.RemoteWS import HomeAssistantWS
from Tile.TileManager import TileManager
from Tile.Tile import *

import logging
import asyncio
import yaml


class Config(object):
    def __init__(self, filename):
        try:
            logging.info('Reading config file "{}"...'.format(filename))

            with open(filename, 'r') as config_file:
                self.config = yaml.load(config_file)
        except IOError as e:
            logging.error('Failed to read config file "{}"!'.format(filename))

            self.config = []

    def get(self, path, default=None):
        value = None

        location = self.config
        for fragment in path.split('/'):
            location = location.get(fragment, None)
            if location is None:
                return default

            value = location if location is not None else default

        return value


async def main(loop, config):
    conf_deck_brightness = config.get('streamdeck/brightness', 20)
    conf_hass_host = config.get('home_assistant/host', 'localhost')
    conf_hass_port = config.get('home_assistant/port', 8123)
    conf_hass_pw = config.get('home_assistant/api_password')

    deck = DeviceManager().enumerate()[0]
    hass = HomeAssistantWS(host=conf_hass_host, port=conf_hass_port)

    # TODO: Replace with layout and tile definitions from config file
    deck_pages = {
        'home': {
            (0, 0): LightHassTile(deck, hass, 'group.study_lights', 'Study'),
            (0, 1): LightHassTile(deck, hass, 'light.mr_ed', 'Mr Ed'),
            (1, 1): LightHassTile(deck, hass, 'light.desk_lamp', 'Desk Lamp'),
            (2, 1): LightHassTile(deck, hass, 'light.study_bias', 'Bias Light'),
            (3, 1): AutomationHassTile(deck, hass, 'group.study_automations', 'Auto Dim'),
            (2, 2): ValueHassTile(deck, hass, 'sensor.living_room_temperature', 'Lvng Rm\nTemp'),
            (3, 2): ValueHassTile(deck, hass, 'sensor.bedroom_temperature', 'Bedroom\nTemp'),
            (4, 2): ValueHassTile(deck, hass, 'sensor.study_temperature', 'Study\nTemp'),
        }
    }

    tile_manager = TileManager(deck, deck_pages)

    async def hass_state_changed(data):
        await tile_manager.update_page(force_redraw=False)

    async def steamdeck_key_state_changed(deck, key, state):
        await tile_manager.button_state_changed(key, state)

    logging.info("Connecting to {}:{}...".format(conf_hass_host, conf_hass_port))
    await hass.connect(api_password=conf_hass_pw)

    deck.open()
    deck.reset()
    deck.set_brightness(conf_deck_brightness)
    deck.set_key_callback_async(steamdeck_key_state_changed)

    await tile_manager.set_deck_page(None)
    await hass.subscribe_to_event('state_changed', hass_state_changed)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()

    config = Config('config.yaml')
    if config.get('debug'):
        logging.info('Debug enabled')
        loop.set_debug(True)
        loop.slow_callback_duration = 0.15

    loop.run_until_complete(main(loop, config))
    loop.run_forever()
