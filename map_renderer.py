from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import logging
import arabic_reshaper
from bidi.algorithm import get_display
from telegram import Update
from telegram.ext import ContextTypes
from config import STRAITS, MAP_HEIGHT, MAP_WIDTH
from database import get_all_provinces

logger = logging.getLogger(__name__)

FONT_PATH       = "assets/fonts/Cairo.ttf"
FONT_FALLBACK   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

COUNTRY_COLORS = {
    "ألمانيا":          (220,  40,  40),
    "فرنسا":            ( 30,  90, 200),
    "روسيا":            ( 70, 160, 220),
    "بريطانيا":         (160, 100,  40),
    "إسبانيا":          (230, 120,  20),
    "إيطاليا":          ( 30, 160,  30),
    "تركيا":            (200,   0,   0),
    "الدولة العثمانية": (200,   0,   0),
    "بولندا":           (220,  20,  60),
    "السويد":           (  0, 110, 220),
    "النرويج":          (190,   0,  60),
    "الدنمارك":         (175,   0,   0),
    "البرتغال":         (  0, 160,   0),
    "فنلندا":           (  0, 160, 210),
    "النمسا":           (190,  50,  50),
    "رومانيا":          (  0, 190,   0),
    "أيسلندا":          (100, 160, 220),
}

def _ar(text: str) -> str:
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        try:
            return ImageFont.truetype(FONT_FALLBACK, size)
        except Exception:
            return ImageFont.load_default()

def get_country_color(name: str):
    return COUNTRY_COLORS.get(name, (160, 160, 160))

def _draw_text_shadowed(draw, pos, text, font, fill, shadow=(0, 0, 0), offset=2):
    x, y = pos
    draw.text((x + offset, y + offset), text, font=font, fill=(*shadow, 160))
    draw.text((x, y), text, font=font, fill=fill)

def _draw_glow_circle(img_rgba, x, y, radius, color, alpha=180):
    glow_layer = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for r in range(radius + 6, radius - 1, -1):
        a = int(alpha * (1 - (r - radius) / 7))
        gd.ellipse([x - r, y - r, x + r, y + r], fill=(*color, max(0, a)))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=3))
    img_rgba.alpha_composite(glow_layer)

def _draw_city_dot(img_rgba, draw, x, y, color, state, progress=0):
    if state == "merged":
        _draw_glow_circle(img_rgba, x, y, 9, color, alpha=200)
        draw.ellipse([x-9, y-9, x+9, y+9], fill=(*color, 240), outline=(255,255,255,220), width=2)
        draw.ellipse([x-4, y-4, x+4, y+4], fill=(255,255,255,200))
    elif state == "occupied":
        _draw_glow_circle(img_rgba, x, y, 11, (255, 60, 60), alpha=180)
        draw.ellipse([x-11, y-11, x+11, y+11], fill=(*color, 200), outline=(255, 60, 60, 255), width=3)
        pct_font = _font(9)
        pct_text = _ar(f"{int(progress)}%")
        draw.text((x - 8, y - 5), pct_text, font=pct_font, fill=(255, 255, 255, 255))
    else:
        _draw_glow_circle(img_rgba, x, y, 7, color, alpha=160)
        draw.ellipse([x-7, y-7, x+7, y+7], fill=(*color, 220), outline=(255,255,255,180), width=1)

def _draw_rounded_rect(draw, box, radius, fill, outline=None, outline_width=1):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=outline_width)

async def render_province_map(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None) -> io.BytesIO:
    try:
        img = Image.open("assets/europe_map.png").convert("RGBA")
    except FileNotFoundError:
        logger.warning("Map image missing – creating blank canvas")
        img = Image.new("RGBA", (MAP_WIDTH, MAP_HEIGHT), (30, 45, 70, 255))

    W, H = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    img.alpha_composite(overlay)

    draw = ImageDraw.Draw(img, "RGBA")

    font_city   = _font(13)
    font_title  = _font(26)
    font_sub    = _font(14)
    font_legend = _font(13)
    font_strait = _font(12)

    provinces = await get_all_provinces()
    if not provinces:
        provinces = []

    for p in provinces:
        x = p.get("px", 0)
        y = p.get("py", 0)
        if not x or not y:
            continue

        owner_id  = p.get("owner_id", 0)
        progress  = p.get("occupation_progress", 0)
        is_merged = p.get("merged", 0)
        city_ar   = p.get("city_name", "؟")
        country   = p.get("country", "")

        if owner_id:
            color = get_country_color(p.get("owner_country", ""))
        else:
            color = get_country_color(country)

        if is_merged:
            state = "merged"
        elif 0 < progress < 100:
            state = "occupied"
        else:
            state = "normal"

        _draw_city_dot(img, draw, x, y, color, state, progress)

        label = _ar(city_ar)
        lx = x + 11
        ly = y - 8
        bbox = draw.textbbox((lx, ly), label, font=font_city)
        pad = 3
        draw.rounded_rectangle(
            [bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad],
            radius=4, fill=(0, 0, 0, 140)
        )
        _draw_text_shadowed(draw, (lx, ly), label, font_city,
                            fill=(255, 240, 200, 255), shadow=(0, 0, 0), offset=1)

    for strait_name, sinfo in STRAITS.items():
        sx = sinfo.get("x", 0)
        sy = sinfo.get("y", 0)
        if not sx or not sy:
            continue

        blocked = sinfo.get("blocked", False)
        sc = (220, 50, 50) if blocked else (50, 210, 130)

        _draw_glow_circle(img, sx, sy, 5, sc, alpha=200)
        draw.ellipse([sx-5, sy-5, sx+5, sy+5], fill=(*sc, 230), outline=(255,255,255,200), width=1)

        label = _ar(strait_name)
        lx = sx + 8
        ly = sy - 7
        bbox = draw.textbbox((lx, ly), label, font=font_strait)
        pad = 2
        draw.rounded_rectangle(
            [bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad],
            radius=3, fill=(10, 10, 40, 160)
        )
        _draw_text_shadowed(draw, (lx, ly), label, font_strait,
                            fill=(180, 230, 255, 255), shadow=(0,0,0), offset=1)

    title_text = _ar("عصر الأمم — خريطة أوروبا")
    tb = draw.textbbox((0, 0), title_text, font=font_title)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    pad_x, pad_y = 18, 10
    tx, ty = 10, 10
    draw.rounded_rectangle(
        [tx - pad_x, ty - pad_y, tx + tw + pad_x, ty + th + pad_y],
        radius=10,
        fill=(10, 15, 35, 200),
        outline=(255, 200, 50, 180),
        width=2
    )
    _draw_text_shadowed(draw, (tx, ty), title_text, font_title,
                        fill=(255, 215, 50, 255), shadow=(0,0,0), offset=2)

    legend_items = [
        ((50, 200, 120),  _ar("مدينة مستقلة")),
        ((255, 255, 255), _ar("مدينة مضمومة")),
        ((255, 60,  60),  _ar("تحت الاحتلال")),
        ((50, 210, 130),  _ar("مضيق مفتوح")),
        ((220, 50,  50),  _ar("مضيق مغلق")),
    ]

    leg_x = 10
    leg_y = H - 10 - (len(legend_items) * 24 + 20)
    leg_w = 200
    leg_h = len(legend_items) * 24 + 20

    draw.rounded_rectangle(
        [leg_x, leg_y, leg_x + leg_w, leg_y + leg_h],
        radius=10,
        fill=(10, 15, 35, 200),
        outline=(100, 140, 200, 150),
        width=1
    )

    for i, (color, label) in enumerate(legend_items):
        iy = leg_y + 12 + i * 24
        draw.ellipse([leg_x + 12, iy + 3, leg_x + 22, iy + 13],
                     fill=(*color, 230), outline=(255,255,255,150), width=1)
        draw.text((leg_x + 28, iy), label, font=font_legend, fill=(220, 225, 240, 255))

    output = io.BytesIO()
    img.convert("RGB").save(output, format="JPEG", quality=92)
    output.seek(0)
    return output


async def render_map(update=None, context=None):
    return await render_province_map(update, context)

async def render_country_map(country, update=None, context=None):
    return await render_province_map(update, context)

async def render_war_map(attacker, defender, update=None, context=None):
    return await render_province_map(update, context)
