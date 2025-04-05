import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import send_file


def generate_captcha_text(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(captcha_text):
    image = Image.new('RGB', (150, 50), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(30)

    draw.text((10, 5), captcha_text, font=font, fill=(0, 0, 0))
    buf = BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return buf
