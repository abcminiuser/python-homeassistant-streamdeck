#!/usr/bin/env python

#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#


from StreamDeck.StreamDeck import DeviceManager
from HomeAssistantWS.RemoteWS import HomeAssistantWS
from ImageTile.Tile import ImageTile

import asyncio
import copy
import sys
import queue
import threading

class BaseTile(object):
    def __init__(self, deck, state_tiles=None):
        image_format = deck.key_image_format()
        image_dimensions = (image_format['width'], image_format['height'])

        self.deck = deck
        self.state_tiles = state_tiles if state_tiles is not None else {}
        self.image_tile = ImageTile(dimensions=image_dimensions)

    async def _get_state(self):
        return None

    async def get_image(self, force=True):
        state = await self._get_state()
        state_tile = self.state_tiles.get(state, self.state_tiles.get(None, {}))

        image_tile = copy.deepcopy(self.image_tile)
        image_tile.color = state_tile.get('color')
        image_tile.label = state_tile.get('label')
        image_tile.overlay = state_tile.get('overlay')
        image_tile.value = state_tile.get('value')
        return image_tile

    async def button_state_changed(self, state):
        pass


class HassTile(BaseTile):
    def __init__(self, deck, state_tiles, hass, entity_id, hass_action):
        super().__init__(deck, state_tiles)
        self.hass = hass
        self.entity_id = entity_id
        self.hass_action = hass_action
        self.old_state = None

    async def _get_state(self):
        entity_state = await self.hass.get_state(self.entity_id)
        return entity_state.get('state')

    async def get_image(self, force=True):
        state = await self._get_state()
        if state == self.old_state and not force:
            return None

        self.old_state = state

        image_tile = await super().get_image()
        if image_tile.value is True:
            image_tile.value = state

        return image_tile

    async def button_state_changed(self, state):
        if state is not True:
            return

        if self.hass_action is not None:
            await self.hass.set_state(domain='homeassistant', service=self.hass_action, entity_id=self.entity_id)


class ValueHassTile(HassTile):
    def __init__(self, deck, hass, entity_id, name):
        state_tiles = {
            None: {'label': name, 'value': True},
        }
        super().__init__(deck, state_tiles, hass, entity_id, hass_action=None)


class LightHassTile(HassTile):
    def __init__(self, deck, hass, entity_id, name):
        state_tiles = {
            'on': {'label': name, 'overlay': 'Assets/light_on.png'},
            None: {'label': name, 'overlay': 'Assets/light_off.png'},
        }
        super().__init__(deck, state_tiles, hass, entity_id, hass_action='toggle')


class AutomationHassTile(HassTile):
    def __init__(self, deck, hass, entity_id, name):
        state_tiles = {
            'on': {'label': name, 'overlay': 'Assets/automation_on.png'},
            None: {'label': name, 'overlay': 'Assets/automation_off.png'},
        }
        super().__init__(deck, state_tiles, hass, entity_id, hass_action='toggle')


class DeckPageManager(object):
    def __init__(self, deck, pages):
        self.deck = deck
        self.key_layout = deck.key_layout()
        self.pages = pages
        self.current_page = None
        self.empty_tile = BaseTile(deck)
        self.current_page = pages.get('home')
        self.deck_image_update_queue = queue.Queue()
        self.deck_image_update_thread = threading.Thread(target=self._deck_image_update_worker)

        self.deck_image_update_thread.daemon = True
        self.deck_image_update_thread.start()

    def _deck_image_update_worker(self):
        while True:
            key, image = self.deck_image_update_queue.get()
            self.deck.set_key_image(key=key, image=[b for b in image])
            self.deck_image_update_queue.task_done()

    def _schedule_key_image_update(self, key, image):
        self.deck_image_update_queue.put((key, image))

    async def set_deck_page(self, name):
        self.current_page = self.pages.get(name, self.pages['home'])
        await self.update_page(force_redraw=True)

    async def update_page(self, force_redraw=False):
        rows, cols = self.key_layout

        for y in range(rows):
            for x in range(cols):
                tile = self.current_page.get((x, y), self.empty_tile)
                if tile is None:
                    continue

                button_image = await tile.get_image(force=force_redraw)
                if button_image is not None:
                    button_index = (y * cols) + x
                    self._schedule_key_image_update(key=button_index, image=button_image)

    async def button_state_changed(self, key, state):
        rows, cols = self.key_layout

        x, y = (key % cols, key // cols)
        tile = self.current_page.get((x, y))
        if tile is not None:
            await tile.button_state_changed(state)


async def main(loop):
    deck = DeviceManager().enumerate()[0]
    hass = HomeAssistantWS('192.168.1.104')

    deck_pages = {
        'home': {
            (0, 0): LightHassTile(deck, hass,'group.study_lights', 'Study'),
            (0, 1): LightHassTile(deck, hass, 'light.mr_ed', 'Mr Ed'),
            (1, 1): LightHassTile(deck, hass, 'light.desk_lamp', 'Desk Lamp'),
            (2, 1): LightHassTile(deck, hass, 'light.study_bias', 'Bias Light'),
            (3, 1): AutomationHassTile(deck, hass, 'group.study_automations', 'Auto Dim'),
            (2, 2): ValueHassTile(deck, hass, 'sensor.living_room_temperature', 'Lvng Rm\nTemp'),
            (3, 2): ValueHassTile(deck, hass, 'sensor.bedroom_temperature', 'Bedroom\nTemp'),
            (4, 2): ValueHassTile(deck, hass, 'sensor.study_temperature', 'Study\nTemp'),
        }
    }
    deck_page_manager = DeckPageManager(deck, deck_pages)

    async def hass_state_changed(data):
        await deck_page_manager.update_page(force_redraw=False)

    async def steamdeck_key_state_changed(deck, key, state):
        await deck_page_manager.button_state_changed(key, state)

    await hass.connect()

    deck.open()
    deck.reset()
    deck.set_brightness(20)
    deck.set_key_callback_async(steamdeck_key_state_changed)

    await deck_page_manager.set_deck_page(None)
    await hass.subscribe_to_event('state_changed', hass_state_changed)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    if "--debug" in sys.argv:
        print("Debug enabled", flush=True)
        loop.set_debug(True)
        loop.slow_callback_duration = 0.15

    loop.run_until_complete(main(loop))
    loop.run_forever()
