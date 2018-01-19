#   Python StreamDeck HomeAssistant Client
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

from PIL import Image, ImageDraw, ImageFont


class ImageTile(object):
    def __init__(self, dimensions=(1, 1)):
        self._pixels = None
        self._overlay_image = None

        self.dimensions = dimensions
        self.color = (0, 0, 0)
        self.overlay = None
        self.label = None
        self.value = None

    @property
    def dimensions(self):
        return self._dimensions

    @property
    def color(self):
        return self._color

    @property
    def overlay(self):
        return self._overlay

    @property
    def label(self, text):
        return self._label

    @property
    def value(self):
        return self._value

    @dimensions.setter
    def dimensions(self, size):
        self._dimensions = size
        self._overlay_image = None
        self._pixels = None

    @color.setter
    def color(self, value):
        self._color = value
        self._pixels = None

    @overlay.setter
    def overlay(self, overlay):
        self._overlay = overlay
        self._overlay_image = None
        self._pixels = None

    @label.setter
    def label(self, text):
        self._label = text
        self._pixels = None

    @value.setter
    def value(self, value):
        self._value = value
        self._pixels = None

    def _get_image(self):
        image = Image.new("RGB", self._dimensions, self._color)
        self._draw_overlay(image)
        self._draw_label(image)
        self._draw_value(image)

        return image

    def _draw_overlay(self, image):
        if self._overlay is None:
            return

        if self._overlay_image is None:
            self._overlay_image = Image.open(self._overlay).convert("RGBA")
            self._overlay_image.thumbnail(self._dimensions, Image.BICUBIC)

        base_w, base_h = image.size
        overlay_w, overlay_h = self._overlay_image.size
        overlay_x = int((base_w - overlay_w) / 2)
        overlay_h = base_h - overlay_h

        image.paste(self._overlay_image, (overlay_x, overlay_h), self._overlay_image)

    def _draw_label(self, image):
        if self._label is None:
            return

        fnt = ImageFont.truetype('Fonts/Roboto-Bold.ttf', 12)
        d = ImageDraw.Draw(image)

        w, h = d.textsize(self._label, font=fnt)

        pos = ((image.width - w) / 2, 2)
        d.text(pos, self._label, font=fnt, fill=(255, 255, 255, 128))

    def _draw_value(self, image):
        if self._value is None:
            return

        fnt = ImageFont.truetype('Fonts/Roboto-Light.ttf', 18)
        d = ImageDraw.Draw(image)

        w, h = d.textsize(self._value, font=fnt)

        pos = ((image.width - w) / 2, image.height - h - 2)
        d.text(pos, self._value, font=fnt, fill=(255, 255, 255, 128))

    def __getitem__(self, key):
        if self._pixels is None:
            def _pixels():
                image = self._get_image()

                image_pixels = image.transpose(Image.FLIP_LEFT_RIGHT).getdata()
                for color in image_pixels:
                    yield color[2]
                    yield color[1]
                    yield color[0]

            self._pixels = [b for b in _pixels()]

        return self._pixels[key]
