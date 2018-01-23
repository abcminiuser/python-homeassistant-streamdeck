#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

from .TileImage import TileImage

import copy


class BaseTile(object):
    def __init__(self, deck, state_tiles=None, name=None):
        image_format = deck.key_image_format()
        image_dimensions = (image_format['width'], image_format['height'])

        self.deck = deck
        self.state_tiles = state_tiles or {}
        self.name = name

        self.image_tile = TileImage(dimensions=image_dimensions)
        self.old_state = None

    @property
    async def state(self):
        return {'state' : None}

    async def get_image(self, force=True):
        state = await self.state
        if state == self.old_state and not force:
            return None
        self.old_state = state

        state_tile = self.state_tiles.get(state.get('state'), self.state_tiles.get(None, {}))

        format_dict = state
        format_dict['name'] = self.name

        image_tile = copy.deepcopy(self.image_tile)
        image_tile.color = state_tile.get('color')
        image_tile.overlay = state_tile.get('overlay')
        image_tile.label = state_tile.get('label', '').format_map(format_dict)
        image_tile.label_font = state_tile.get('label_font')
        image_tile.label_size = state_tile.get('label_size')
        image_tile.value = state_tile.get('value', '').format_map(format_dict)
        image_tile.value_font = state_tile.get('value_font')
        image_tile.value_size = state_tile.get('value_size')

        return image_tile

    async def button_state_changed(self, state):
        pass


class HassTile(BaseTile):
    def __init__(self, deck, state_tiles, name, hass, entity_id, hass_action):
        super().__init__(deck, state_tiles, name)
        self.hass = hass
        self.entity_id = entity_id
        self.hass_action = hass_action

    @property
    async def state(self):
        hass_state = await self.hass.get_state(self.entity_id)
        return hass_state

    async def button_state_changed(self, state):
        if state is not True:
            return

        if self.hass_action is not None:
            await self.hass.set_state(domain='homeassistant', service=self.hass_action, entity_id=self.entity_id)
