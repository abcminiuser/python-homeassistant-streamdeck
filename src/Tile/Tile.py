#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

from .TileImage import TileImage

import copy


class BaseTile(object):
    def __init__(self, deck, state_tiles=None):
        image_format = deck.key_image_format()
        image_dimensions = (image_format['width'], image_format['height'])

        self.deck = deck
        self.state_tiles = state_tiles if state_tiles is not None else {}
        self.image_tile = TileImage(dimensions=image_dimensions)

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
