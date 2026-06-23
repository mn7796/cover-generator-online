from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
ITERATIONS_DIR = OUTPUT_DIR / "iterations"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1440

# Put your own font files in assets/fonts and set these paths if needed.
# The defaults prefer common macOS Chinese-capable fonts.
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    str(FONTS_DIR / "PingFang.ttc"),
    str(FONTS_DIR / "NotoSansCJK-Regular.ttc"),
]

BOLD_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    str(FONTS_DIR / "PingFang.ttc"),
    str(FONTS_DIR / "NotoSansCJK-Bold.ttc"),
]

DEFAULT_TEXT = {
    "id": "demo",
    "top_label": "Sunday Reset Vlog",
    "red_tag": "适合口语小白拆开练",
    "main_title": "全英vlog",
    "main_subtitle": "逐句跟读",
    "feature_text": "听一句｜跟一句｜精听｜听写",
    "bottom_title": "Getting My Life Together",
    "bottom_subtitle": "Productive Sunday Reset ☁️",
    "bottom_tag": "Clean With Me & Meal Prep",
}

COLORS = {
    "cream": "#FFF2D7",
    "cream_deep": "#F5DFAF",
    "black": "#111111",
    "white": "#FFFFFF",
    "yellow": "#FFD64D",
    "red": "#E53935",
    "soft_red": "#F04B42",
    "shadow": "#000000",
    "brown": "#6B4B2A",
    "muted": "#7C6B5D",
}
