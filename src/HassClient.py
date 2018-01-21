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

import asyncio
import sys


async def main(loop):
    deck = DeviceManager().enumerate()[0]
    hass = HomeAssistantWS('192.168.1.104')

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

    await hass.connect()

    deck.open()
    deck.reset()
    deck.set_brightness(20)
    deck.set_key_callback_async(steamdeck_key_state_changed)

    await tile_manager.set_deck_page(None)
    await hass.subscribe_to_event('state_changed', hass_state_changed)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    if '--debug' in sys.argv:
        print('Debug enabled', flush=True)
        loop.set_debug(True)
        loop.slow_callback_duration = 0.15

    loop.run_until_complete(main(loop))
    loop.run_forever()
