from __future__ import annotations

from dataclasses import dataclass


CANVAS_SIZE = (1080, 1440)
REFERENCE_PATH = "assets/reference/template.png"


@dataclass(frozen=True)
class Shadow:
    offset: tuple[int, int]
    blur: int
    alpha: int


COLORS = {
    "cream": "#FFF3DA",
    "cream_card": "#FFF1D3",
    "black": "#101010",
    "white": "#FFFFFF",
    "yellow": "#FFD84C",
    "red": "#E8322B",
    "muted": "#7A6657",
    "dash": "#C9B69D",
}

# Coordinates are tuned from assets/reference/template.png, normalized to 1080x1440.
LAYOUT = {
    "outer_radius": 34,
    "image_boxes": [
        (0, 0, 1080, 430),
        (0, 430, 1080, 914),
        (0, 914, 1080, 1440),
    ],
    "separators": [
        (0, 429, 1080, 432),
        (0, 913, 1080, 916),
    ],
    "top_label": {
        "box": (24, 31, 450, 109),
        "padding_x": 32,
        "radius": 36,
        "font_size": 43,
        "min_font_size": 28,
        "max_text_width": 365,
        "shadow": Shadow(offset=(0, 5), blur=9, alpha=42),
    },
    "red_tag": {
        "box": (24, 130, 450, 196),
        "padding_x": 78,
        "play_center": (70, 163),
        "play_size": 30,
        "radius": 30,
        "font_size": 36,
        "min_font_size": 24,
        "max_text_width": 310,
        "shadow": Shadow(offset=(0, 5), blur=8, alpha=70),
    },
    "title_block": {
        "box": (24, 608, 500, 914),
        "radius": 24,
        "padding_x": 28,
        "title_y": (634, 742),
        "subtitle_y": (746, 886),
        "font_size": 92,
        "min_font_size": 56,
        "max_text_width": 426,
        "shadow": Shadow(offset=(0, 8), blur=16, alpha=85),
    },
    "feature_strip": {
        "box": (24, 916, 558, 982),
        "radius": 24,
        "font_size": 36,
        "min_font_size": 23,
        "max_text_width": 470,
        "shadow": Shadow(offset=(0, 5), blur=8, alpha=42),
    },
    "bottom_card": {
        "box": (50, 1294, 708, 1428),
        "radius": 27,
        "shadow": Shadow(offset=(0, 8), blur=18, alpha=55),
        "star_center": (112, 1350),
        "star_outer": 26,
        "star_inner": 11,
        "text_x": 142,
        "content_right": 586,
        "title_y": 1311,
        "subtitle_y": 1362,
        "tag_y": 1396,
        "tag_height": 27,
        "title_font_size": 34,
        "title_min_font_size": 22,
        "subtitle_font_size": 25,
        "subtitle_min_font_size": 18,
        "tag_font_size": 21,
        "tag_min_font_size": 15,
        "tag_max_width": 320,
        "dash_x": 600,
        "dash_y": (1320, 1412),
        "heart_center": (660, 1360),
        "heart_size": 72,
    },
    "play_button": {
        "center": (974, 1358),
        "radius": 66,
        "triangle_size": 54,
        "triangle_offset_x": 5,
        "shadow": Shadow(offset=(0, 8), blur=16, alpha=45),
    },
}


AI_REFERENCE_PROMPT = """
Use the first input image as the only visual layout template. Match its composition,
spacing, rounded rectangles, shadow strength, typography scale, colors, bottom card,
and bottom-right play button placement. Do not redesign the layout.
""".strip()
