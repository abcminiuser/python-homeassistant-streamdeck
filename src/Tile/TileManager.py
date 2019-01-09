#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

from .Tile import BaseTile

from concurrent.futures import ThreadPoolExecutor


class TileManager(object):
    def __init__(self, deck, pages):
        self.deck = deck
        self.key_layout = deck.key_layout()
        self.pages = pages
        self.current_page = None
        self.empty_tile = BaseTile(deck)
        self.current_page = pages.get('home')

        if self.current_page is None:
            raise KeyError('Deck page configuration must have a default "home" page.')

        self._executor = ThreadPoolExecutor(max_workers=1)

    async def set_deck_page(self, name):
        self.current_page = self.pages.get(name, self.pages['home'])
        await self.update_page(force_redraw=True)

    async def update_page(self, force_redraw=False):
        rows, cols = self.key_layout

        for y in range(rows):
            for x in range(cols):
                tile = self.current_page.get((x, y), self.empty_tile)

                button_image = await tile.get_image(force=force_redraw)
                button_index = (y * cols) + x

                if button_image:
                    self._executor.submit(self.deck.set_key_image, key=button_index, image=button_image)

    async def button_state_changed(self, key, state):
        rows, cols = self.key_layout

        x, y = (key % cols, key // cols)
        tile = self.current_page.get((x, y))
        if tile is not None:
            await tile.button_state_changed(self, state)
