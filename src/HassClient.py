#!/usr/bin/env python3

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

            with open(filename, 'r', encoding='utf-8') as config_file:
                self.config = yaml.safe_load(config_file)
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

            value = location or default

        return value


async def main(loop, config):
    conf_deck_brightness = config.get('streamdeck/brightness', 20)
    conf_hass_host = config.get('home_assistant/host', 'localhost')
    conf_hass_port = config.get('home_assistant/port', 8123)
    conf_hass_pw = config.get('home_assistant/api_password')

    decks = DeviceManager().enumerate()
    if len(decks) == 0:
        logging.error("No StreamDeck found.")
        return False

    deck = decks[0]
    hass = HomeAssistantWS(host=conf_hass_host, port=conf_hass_port)

    tiles = dict()
    pages = dict()

    tile_classes = getattr(__import__("Tile"), "Tile")

    conf_tiles = config.get('tiles')
    for conf_tile in conf_tiles:
        conf_tile_type = conf_tile.get('type')
        conf_tile_class = conf_tile.get('class')
        conf_tile_action = conf_tile.get('action')
        conf_tile_states = conf_tile.get('states')

        tile_states = dict()
        for conf_tile_state in conf_tile_states:
            state = conf_tile_state.get('state')
            tile_states[state] = conf_tile_state

        tiles[conf_tile_type] = {
            'class': getattr(tile_classes, conf_tile_class),
            'states': tile_states,
            'action': conf_tile_action,
        }

    conf_screens = config.get('screens')
    for conf_screen in conf_screens:
        conf_screen_name = conf_screen.get('name')
        conf_screen_tiles = conf_screen.get('tiles')

        page_tiles = dict()
        for conf_screen_tile in conf_screen_tiles:
            conf_screen_tile_pos = conf_screen_tile.get('position')
            conf_screen_tile_type = conf_screen_tile.get('type')
            conf_screen_tile_name = conf_screen_tile.get('name')
            conf_screen_tile_entity_name = conf_screen_tile.get('entity_name')

            conf_screen_tile_class = tiles[conf_screen_tile_type]['class']
            conf_screen_tile_states = tiles[conf_screen_tile_type]['states']
            conf_screen_tile_action = tiles[conf_screen_tile_type]['action']

            x, y = conf_screen_tile_pos
            page_tiles[(x, y)] = conf_screen_tile_class(deck, conf_screen_tile_states, conf_screen_tile_name, hass, conf_screen_tile_entity_name, conf_screen_tile_action)

        pages[conf_screen_name] = page_tiles

    tile_manager = TileManager(deck, pages)

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

    return True


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()

    config = Config('config.yaml')
    if config.get('debug'):
        logging.info('Debug enabled')
        loop.set_debug(True)
        loop.slow_callback_duration = 0.15

    init_ok = loop.run_until_complete(main(loop, config))
    if init_ok:
        loop.run_forever()
