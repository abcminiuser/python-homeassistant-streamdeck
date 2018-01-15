from PIL import Image, ImageFilter, ImageDraw, ImageFont


class BaseTile(object):
    def __init__(self, base_image, label=None, value=None):
        self.base_image = base_image
        self.image      = base_image
        self.label      = label
        self.value      = value
        self.pixels     = None

    def _pixels(self):
        for y in range(0, self.image.height):
            for x in range(0, self.image.width):
                colour = self.image.getpixel((self.image.width - x - 1, y))
                yield colour[2]
                yield colour[1]
                yield colour[0]

    def _draw_label(self):
        if self.label is None:
            return

        fnt = ImageFont.truetype('Fonts/Roboto-Bold.ttf', 12)
        d = ImageDraw.Draw(self.image)

        w, h = d.textsize(self.label, font=fnt)
        d.text(((self.image.width - w) / 2, 2), self.label, font=fnt, fill=(255,255,255,128))

    def _draw_value(self):
        if self.value is None:
            return

        fnt = ImageFont.truetype('Fonts/Roboto-Light.ttf', 18)
        d = ImageDraw.Draw(self.image)

        w, h = d.textsize(self.value, font=fnt)
        d.text(((self.image.width - w) / 2, self.image.height - h - 2), self.value, font=fnt, fill=(255,255,255,128))

    def set_label(self, text):
        self.label = text
        self.pixels = None

    def set_value(self, text):
        self.value = text
        self.pixels = None

    def __getitem__(self, key):
        if self.pixels is None:
            self.image = self.base_image.copy()
            self._draw_label()
            self._draw_value()
            self.pixels = [b for b in self._pixels()]

        return self.pixels[key]


class ColorTile(BaseTile):
    def __init__(self, dimensions, color, label=None, value=None):
        base_image = Image.new("RGB", dimensions, color)
        super().__init__(base_image, label, value)


class ImageTile(BaseTile):
    def __init__(self, dimensions, filename, label=None, value=None):
        base_image = Image.new("RGB", dimensions, (0, 0, 0))

        overlay_image = Image.open(filename).convert("RGBA")
        overlay_image.thumbnail(dimensions, Image.BICUBIC)

        base_w, base_h = base_image.size
        overlay_w, overlay_h = overlay_image.size
        overlay_x = int((base_w - overlay_w) / 2)
        overlay_h = base_h - overlay_h
        base_image.paste(overlay_image, (overlay_x, overlay_h), overlay_image)

        super().__init__(base_image, label, value)
