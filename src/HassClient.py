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
import sys


class BaseHassTile(object):
    def __init__(self, hass, deck, entity_id, state_tiles, hass_action):
        self.hass = hass
        self.deck = deck
        self.entity_id = entity_id
        self.state_tiles = state_tiles
        self.hass_action = hass_action
        self.old_state = None

    def get_state(self):
        return self.hass.get_state(self.entity_id)

    async def get_image(self, force=True):
        state = await self.get_state()
        if state == self.old_state and not force:
            return None

        self.old_state = state

        state_tile = self.state_tiles.get(state, self.state_tiles[None])

        image_format = self.deck.key_image_format()
        image_dimensions = (image_format['width'], image_format['height'])

        image = ImageTile(dimensions=image_dimensions)
        image.color = state_tile.get('color')
        image.label = state_tile.get('label')
        image.overlay = state_tile.get('overlay')
        image.value = state if state_tile.get('value') is True else state_tile.get('value')

        return image

    async def button_state_changed(self, state):
        if state is not True:
            return

        action = self.hass_action

        if action == 'force_toggle':
            # If force toggled, we explicitly set the new state to ensure all
            # targets end up on the desired state (vs inverting their current
            # state)
            action = 'turn_off' if await self.get_state() == 'on' else 'turn_on'

        if action is not None:
            await self.hass.set_state(domain='homeassistant', service=action, entity_id=self.entity_id)


class ValueHassTile(BaseHassTile):
    def __init__(self, hass, deck, entity_id, name):
        state_tiles = {
            None: {'label': name, 'value': True},
        }
        super().__init__(hass, deck, entity_id, state_tiles, hass_action=None)


class LightHassTile(BaseHassTile):
    def __init__(self, hass, deck, entity_id, name, force_toggle=True):
        state_tiles = {
            'on': {'label': name, 'overlay': 'Assets/light_on.png'},
            None: {'label': name, 'overlay': 'Assets/light_off.png'},
        }
        hass_action = 'force_toggle' if force_toggle else 'toggle'
        super().__init__(hass, deck, entity_id, state_tiles, hass_action=hass_action)


class AutomationHassTile(BaseHassTile):
    def __init__(self, hass, deck, entity_id, name):
        state_tiles = {
            'on': {'label': name, 'overlay': 'Assets/automation_on.png'},
            None: {'label': name, 'overlay': 'Assets/automation_off.png'},
        }
        super().__init__(hass, deck, entity_id, state_tiles, hass_action='toggle')


class DeckPageManager(object):
    def __init__(self, deck, pages):
        image_format = deck.key_image_format()
        image_dimensions = (image_format['width'], image_format['height'])

        self.deck = deck
        self.key_layout = self.deck.key_layout()
        self.pages = pages
        self.current_page = None
        self.empty_tile_image = ImageTile(dimensions=image_dimensions)

    async def set_deck_page(self, name):
        self.current_page = self.pages.get(name, self.pages['home'])
        await self.update_page(force_redraw=True)

    async def update_page(self, force_redraw=False):
        rows, cols = self.key_layout

        image_format = self.deck.key_image_format()
        image_dimensions = (image_format['width'], image_format['height'])

        for y in range(rows):
            for x in range(cols):
                button_index = (y * cols) + x
                tile = self.current_page.get((x, y))

                if tile is not None:
                    button_image = await tile.get_image(force=force_redraw)
                elif force_redraw:
                    button_image = self.empty_tile_image
                else:
                    button_image = None

                if button_image is not None:
                    self.deck.set_key_image(key=button_index, image=[b for b in button_image])

    async def button_state_changed(self, key, state):
        rows, cols = self.key_layout

        button_pos = (key % cols, key // cols)
        tile = self.current_page.get(button_pos)
        if tile is not None:
            await tile.button_state_changed(state)


async def main(loop):
    deck = DeviceManager().enumerate()[0]
    hass = HomeAssistantWS('192.168.1.104')

    deck_pages = {
        'home': {
            (0, 0): LightHassTile(hass, deck, 'group.study_lights', 'Study'),
            (0, 1): LightHassTile(hass, deck, 'light.mr_ed', 'Mr Ed'),
            (1, 1): LightHassTile(hass, deck, 'light.desk_lamp', 'Desk Lamp'),
            (2, 1): LightHassTile(hass, deck, 'light.study_bias', 'Bias Light'),
            (3, 1): AutomationHassTile(hass, deck, 'group.study_automations', 'Auto Dim'),
            (2, 2): ValueHassTile(hass, deck, 'sensor.living_room_temperature', 'Lvng Rm\nTemp'),
            (3, 2): ValueHassTile(hass, deck, 'sensor.bedroom_temperature', 'Bedroom\nTemp'),
            (4, 2): ValueHassTile(hass, deck, 'sensor.study_temperature', 'Study\nTemp'),
        }
    }
    deck_page_manager = DeckPageManager(deck, deck_pages)

    async def hass_state_changed(data):
        await deck_page_manager.update_page(force_redraw=False)

    async def steamdeck_key_state_changed(deck, key, state):
        await deck_page_manager.button_state_changed(key, state)

    await hass.connect()

    deck.open()
    deck.set_brightness(20)
    deck.set_key_callback_async(steamdeck_key_state_changed)

    await deck_page_manager.set_deck_page(None)
    await hass.subscribe_to_event('state_changed', hass_state_changed)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    if "--debug" in sys.argv:
        print("Debug enabled", flush=True)
        import warnings
        loop.set_debug(True)
        loop.slow_callback_duration = 0.2
        warnings.simplefilter('always', ResourceWarning)

    loop.run_until_complete(main(loop))
    loop.run_forever()
