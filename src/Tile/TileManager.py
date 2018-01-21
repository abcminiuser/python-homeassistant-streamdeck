#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

from .Tile import BaseTile

import queue
import threading


class TileManager(object):
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
            self.deck.set_key_image(key=key, image=image)
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
