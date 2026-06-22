from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import (
    BOLD_FONT_CANDIDATES,
    DEFAULT_TEXT,
    FONT_CANDIDATES,
    INPUT_DIR,
    OUTPUT_DIR,
)
from template_config import CANVAS_SIZE, COLORS, LAYOUT


CANVAS_WIDTH, CANVAS_HEIGHT = CANVAS_SIZE


@dataclass
class CoverText:
    id: str = DEFAULT_TEXT["id"]
    top_label: str = DEFAULT_TEXT["top_label"]
    red_tag: str = DEFAULT_TEXT["red_tag"]
    main_title: str = DEFAULT_TEXT["main_title"]
    main_subtitle: str = DEFAULT_TEXT["main_subtitle"]
    feature_text: str = DEFAULT_TEXT["feature_text"]
    bottom_title: str = DEFAULT_TEXT["bottom_title"]
    bottom_subtitle: str = DEFAULT_TEXT["bottom_subtitle"]
    bottom_tag: str = DEFAULT_TEXT["bottom_tag"]

    @classmethod
    def from_mapping(cls, data: Mapping[str, str]) -> "CoverText":
        values = {}
        for key, default in DEFAULT_TEXT.items():
            raw = data.get(key, "")
            values[key] = str(raw).strip() or default
        return cls(**values)


def ensure_dirs() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def _first_existing(paths: Iterable[str]) -> str | None:
    for path in paths:
        if Path(path).exists():
            return path
    return None


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = BOLD_FONT_CANDIDATES if bold else FONT_CANDIDATES
    font_path = _first_existing(candidates)
    if not font_path:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(font_path, size=size, index=0)
    except TypeError:
        return ImageFont.truetype(font_path, size=size)


def _hex(color: str) -> str:
    return COLORS.get(color, color)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    return draw.textbbox((0, 0), text, font=font)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = text_bbox(draw, text, font)
    return box[2] - box[0], box[3] - box[1]


def draw_centered_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill) -> None:
    x1, y1, x2, y2 = box
    w, h = text_size(draw, text, font)
    draw.text((x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2 - 2), text, font=font, fill=fill)


def draw_vcenter_text(draw: ImageDraw.ImageDraw, x: int, box_y: tuple[int, int], text: str, font, fill) -> None:
    _, h = text_size(draw, text, font)
    y = box_y[0] + (box_y[1] - box_y[0] - h) / 2 - 2
    draw.text((x, y), text, font=font, fill=fill)


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_size: int, min_size: int, bold: bool = False):
    for size in range(max_size, min_size - 1, -2):
        font = get_font(size, bold=bold)
        if text_size(draw, text, font)[0] <= max_width:
            return font
    return get_font(min_size, bold=bold)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 2) -> list[str]:
    text = str(text).strip()
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if text_size(draw, candidate, font)[0] <= max_width or not current:
            current = candidate
            continue
        lines.append(current)
        current = char
        if len(lines) == max_lines - 1:
            break
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


def fit_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    max_size: int,
    min_size: int,
    max_lines: int = 2,
    bold: bool = False,
):
    for size in range(max_size, min_size - 1, -2):
        font = get_font(size, bold=bold)
        lines = wrap_text(draw, text, font, max_width, max_lines)
        line_h = text_size(draw, "字Ag", font)[1] + int(size * 0.2)
        if len(lines) * line_h <= max_height and all(text_size(draw, line, font)[0] <= max_width for line in lines):
            return font, lines, line_h
    font = get_font(min_size, bold=bold)
    return font, wrap_text(draw, text, font, max_width, max_lines), text_size(draw, "字Ag", font)[1] + 4


def crop_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    src_w, src_h = image.size
    dst_w, dst_h = size
    scale = max(dst_w / src_w, dst_h / src_h)
    resized = image.resize((math.ceil(src_w * scale), math.ceil(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - dst_w) // 2)
    top = max(0, (resized.height - dst_h) // 2)
    return resized.crop((left, top, left + dst_w, top + dst_h))


def add_warm_vlog_grade(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    warm = Image.new("RGBA", image.size, (255, 214, 160, 20))
    image = Image.alpha_composite(image, warm)
    return image


def rounded_image(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width, image.height), radius=radius, fill=255)
    out = Image.new("RGBA", image.size)
    out.paste(image.convert("RGBA"), (0, 0), mask)
    return out


def add_shadow(base: Image.Image, box, radius: int, offset=(0, 8), blur=18, alpha=55) -> None:
    x1, y1, x2, y2 = box
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    draw.rounded_rectangle((x1 + offset[0], y1 + offset[1], x2 + offset[0], y2 + offset[1]), radius=radius, fill=(0, 0, 0, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(shadow)


def add_config_shadow(base: Image.Image, box, radius: int, shadow) -> None:
    add_shadow(base, box, radius, offset=shadow.offset, blur=shadow.blur, alpha=shadow.alpha)


def apply_outer_rounding(image: Image.Image, radius: int = 34) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width, image.height), radius=radius, fill=255)
    out = Image.new("RGBA", image.size, (255, 255, 255, 0))
    out.paste(image, (0, 0), mask)
    return out


def draw_play_triangle(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int, fill) -> None:
    cx, cy = center
    half_h = size // 2
    points = [(cx - size // 3, cy - half_h), (cx - size // 3, cy + half_h), (cx + size // 2, cy)]
    draw.polygon(points, fill=fill)


def draw_starburst(draw: ImageDraw.ImageDraw, center: tuple[int, int], outer: int, inner: int, fill) -> None:
    cx, cy = center
    points = []
    for i in range(16):
        angle = -math.pi / 2 + i * math.pi / 8
        radius = outer if i % 2 == 0 else inner
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=fill)


def draw_heart(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int, fill, width: int = 8) -> None:
    cx, cy = center
    points = []
    for i in range(80):
        t = i / 80 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((cx + x * size / 32, cy + y * size / 32))
    draw.line(points + [points[0]], fill=fill, width=width, joint="curve")


def draw_cover(image_paths: list[str | Path], text: CoverText | Mapping[str, str], output_path: str | Path | None = None) -> Image.Image:
    if len(image_paths) != 3:
        raise ValueError("需要正好 3 张图片：上图、中图、下图。")
    cover_text = text if isinstance(text, CoverText) else CoverText.from_mapping(text)

    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), _hex("cream"))
    draw = ImageDraw.Draw(canvas)

    image_boxes = LAYOUT["image_boxes"]

    for path, box in zip(image_paths, image_boxes):
        img = Image.open(path)
        cropped = crop_cover(img, (box[2] - box[0], box[3] - box[1]))
        canvas.alpha_composite(add_warm_vlog_grade(cropped), (box[0], box[1]))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for separator in LAYOUT["separators"]:
        od.rectangle(separator, fill=(255, 255, 255, 65))
    od.rounded_rectangle((1, 1, CANVAS_WIDTH - 2, CANVAS_HEIGHT - 2), radius=LAYOUT["outer_radius"], outline=(255, 255, 255, 115), width=3)
    canvas.alpha_composite(overlay)
    draw = ImageDraw.Draw(canvas)

    top_cfg = LAYOUT["top_label"]
    top_font = fit_font(draw, cover_text.top_label, top_cfg["max_text_width"], top_cfg["font_size"], top_cfg["min_font_size"], bold=True)
    top_w, _ = text_size(draw, cover_text.top_label, top_font)
    top_box_base = top_cfg["box"]
    top_box = (top_box_base[0], top_box_base[1], min(top_box_base[2], top_box_base[0] + top_w + top_cfg["padding_x"] * 2), top_box_base[3])
    add_config_shadow(canvas, top_box, top_cfg["radius"], top_cfg["shadow"])
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, top_box, top_cfg["radius"], _hex("cream"))
    draw_vcenter_text(draw, top_box[0] + top_cfg["padding_x"], (top_box[1], top_box[3]), cover_text.top_label, top_font, _hex("black"))

    red_cfg = LAYOUT["red_tag"]
    red_font = fit_font(draw, cover_text.red_tag, red_cfg["max_text_width"], red_cfg["font_size"], red_cfg["min_font_size"], bold=True)
    red_w, _ = text_size(draw, cover_text.red_tag, red_font)
    red_box_base = red_cfg["box"]
    red_box = (red_box_base[0], red_box_base[1], min(red_box_base[2], red_box_base[0] + red_w + red_cfg["padding_x"] + 26), red_box_base[3])
    add_config_shadow(canvas, red_box, red_cfg["radius"], red_cfg["shadow"])
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, red_box, red_cfg["radius"], _hex("red"))
    draw_play_triangle(draw, red_cfg["play_center"], red_cfg["play_size"], _hex("white"))
    draw_vcenter_text(draw, red_box[0] + red_cfg["padding_x"], (red_box[1], red_box[3]), cover_text.red_tag, red_font, _hex("white"))

    title_cfg = LAYOUT["title_block"]
    title_box = title_cfg["box"]
    add_config_shadow(canvas, title_box, title_cfg["radius"], title_cfg["shadow"])
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, title_box, title_cfg["radius"], _hex("black"))
    title_font = fit_font(draw, cover_text.main_title, title_cfg["max_text_width"], title_cfg["font_size"], title_cfg["min_font_size"], bold=True)
    subtitle_font = fit_font(draw, cover_text.main_subtitle, title_cfg["max_text_width"], title_cfg["font_size"], title_cfg["min_font_size"], bold=True)
    draw_vcenter_text(draw, title_box[0] + title_cfg["padding_x"], title_cfg["title_y"], cover_text.main_title, title_font, _hex("white"))
    draw_vcenter_text(draw, title_box[0] + title_cfg["padding_x"], title_cfg["subtitle_y"], cover_text.main_subtitle, subtitle_font, _hex("yellow"))

    feature_cfg = LAYOUT["feature_strip"]
    feature_font = fit_font(draw, cover_text.feature_text, feature_cfg["max_text_width"], feature_cfg["font_size"], feature_cfg["min_font_size"], bold=True)
    feature_w, _ = text_size(draw, cover_text.feature_text, feature_font)
    feature_base = feature_cfg["box"]
    feature_box = (feature_base[0], feature_base[1], min(feature_base[2], feature_base[0] + feature_w + 56), feature_base[3])
    add_config_shadow(canvas, feature_box, feature_cfg["radius"], feature_cfg["shadow"])
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, feature_box, feature_cfg["radius"], _hex("cream"))
    draw_centered_text(draw, feature_box, cover_text.feature_text, feature_font, _hex("black"))

    card_cfg = LAYOUT["bottom_card"]
    card_box = card_cfg["box"]
    add_config_shadow(canvas, card_box, card_cfg["radius"], card_cfg["shadow"])
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, card_box, card_cfg["radius"], _hex("cream_card"))
    draw_starburst(draw, card_cfg["star_center"], card_cfg["star_outer"], card_cfg["star_inner"], _hex("red"))

    left_x = card_cfg["text_x"]
    content_right = card_cfg["content_right"]
    bottom_title_font, title_lines, title_line_h = fit_wrapped_text(
        draw, cover_text.bottom_title, content_right - left_x, 42, card_cfg["title_font_size"], card_cfg["title_min_font_size"], max_lines=2, bold=True
    )
    y = card_cfg["title_y"]
    for line in title_lines:
        draw.text((left_x, y), line, font=bottom_title_font, fill=_hex("black"))
        y += title_line_h

    sub_font = fit_font(draw, cover_text.bottom_subtitle, content_right - left_x, card_cfg["subtitle_font_size"], card_cfg["subtitle_min_font_size"])
    draw.text((left_x, card_cfg["subtitle_y"]), cover_text.bottom_subtitle, font=sub_font, fill=_hex("muted"))

    tag_font = fit_font(draw, cover_text.bottom_tag, card_cfg["tag_max_width"], card_cfg["tag_font_size"], card_cfg["tag_min_font_size"], bold=True)
    tag_w, _ = text_size(draw, cover_text.bottom_tag, tag_font)
    tag_box = (left_x, card_cfg["tag_y"], left_x + min(card_cfg["tag_max_width"], tag_w + 28), card_cfg["tag_y"] + card_cfg["tag_height"])
    rounded_rect(draw, tag_box, 12, _hex("red"))
    draw_centered_text(draw, tag_box, cover_text.bottom_tag, tag_font, _hex("white"))

    dash_x = card_cfg["dash_x"]
    for dash_y in range(card_cfg["dash_y"][0], card_cfg["dash_y"][1], 16):
        draw.line((dash_x, dash_y, dash_x, dash_y + 7), fill=(185, 166, 140, 150), width=2)
    draw_heart(draw, card_cfg["heart_center"], card_cfg["heart_size"], _hex("yellow"), width=6)

    play_cfg = LAYOUT["play_button"]
    play_center = play_cfg["center"]
    play_radius = play_cfg["radius"]
    add_config_shadow(canvas, (play_center[0] - play_radius, play_center[1] - play_radius, play_center[0] + play_radius, play_center[1] + play_radius), play_radius, play_cfg["shadow"])
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((play_center[0] - play_radius, play_center[1] - play_radius, play_center[0] + play_radius, play_center[1] + play_radius), fill=_hex("cream"), outline=(255, 255, 255, 190), width=2)
    draw_play_triangle(draw, (play_center[0] + play_cfg["triangle_offset_x"], play_center[1]), play_cfg["triangle_size"], _hex("red"))

    canvas = apply_outer_rounding(canvas, radius=LAYOUT["outer_radius"])

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "PNG", optimize=True)
    return canvas


def read_csv_rows(csv_path: str | Path) -> list[CoverText]:
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as f:
        return [CoverText.from_mapping(row) for row in csv.DictReader(f)]


def batch_generate(csv_path: str | Path = INPUT_DIR / "covers.csv", input_dir: str | Path = INPUT_DIR, output_dir: str | Path = OUTPUT_DIR) -> list[Path]:
    rows = read_csv_rows(csv_path)
    output_paths: list[Path] = []
    for row in rows:
        folder = Path(input_dir) / row.id
        image_paths = [folder / "1.png", folder / "2.png", folder / "3.png"]
        missing = [str(path) for path in image_paths if not path.exists()]
        if missing:
            raise FileNotFoundError(f"{row.id} 缺少图片：{', '.join(missing)}")
        output_path = Path(output_dir) / f"{row.id}.png"
        draw_cover(image_paths, row, output_path)
        output_paths.append(output_path)
    return output_paths
