from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, Iterable, Mapping

import requests
from openai import OpenAI
from PIL import Image

from config import CANVAS_HEIGHT, CANVAS_WIDTH, OUTPUT_DIR
from generate import CoverText
from template_config import AI_REFERENCE_PROMPT, REFERENCE_PATH


AI_MODEL = "gpt-image-2"
AI_WORK_SIZE = "1088x1456"


ITERATION_BASE_RULES = """
基于当前这一版继续迭代，不要重新生成，不要改原本的产出逻辑，只按用户本次口述做局部修改，其余保持不变。

保持不变：
- 整体版式逻辑
- 三图拼接逻辑
- 标题区逻辑
- 底部信息卡逻辑
- 播放按钮逻辑
- 图片顺序逻辑
- 整体色调和风格
- 人物脸部质感和清晰度

本次只修改用户明确指出的内容。
不要重做整张图，不要重新设计，不要改变布局，不要移动播放按钮，不要放大底部卡片，不要修改未提到的文字。
""".strip()


LOCK_LAYOUT_RULES = """
锁定版式要求：
- 不改版式
- 不改元素位置
- 不改播放按钮位置
- 不改底部信息卡大小
- 不改图片顺序
- 不改没有提到的文字
""".strip()


def normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    normalized = base_url.strip().rstrip("/")
    if normalized == "https://www.aiartmirror.com":
        return f"{normalized}/v1"
    return normalized


def build_cover_prompt(text: CoverText | Mapping[str, str]) -> str:
    cover_text = text if isinstance(text, CoverText) else CoverText.from_mapping(text)
    return f"""
Create one polished vertical short-video cover for Xiaohongshu/Douyin English-learning content.

{AI_REFERENCE_PROMPT}

Input image order:
- image 1 is the confirmed cover template and must be the only layout reference
- image 2 is the top screenshot band
- image 3 is the middle screenshot band
- image 4 is the bottom screenshot band

Hard layout requirements:
- Final composition must be a 3:4 vertical cover.
- Generate the image at 1088x1456 pixels. This is a near-3:4 canvas with both dimensions divisible by 16.
- The result will be normalized to 1080x1440 after generation, so keep all UI safely inside the canvas.
- Keep every UI element fully inside the canvas. Nothing may touch or be cropped by the top, bottom, left, or right edges.
- Leave a generous safe margin around the top labels and bottom card/play button.
- Do not place any label partially outside the image. The top cream label must be fully visible.
- Use a clean three-band screenshot collage, top/middle/bottom.
- Warm lifestyle vlog look, refined mobile cover design, premium but not poster-like.
- Keep the structure consistent and readable.
- Use cream, black, white, yellow, and red as the main UI colors.
- Do not invent extra paragraphs or random decorative text.
- Do not move the play button away from the bottom-right corner.

Required visible text:
- Top cream rounded label: {cover_text.top_label}
- Red rounded label with white play triangle: {cover_text.red_tag}
- Large black rounded title block:
  line 1 in white: {cover_text.main_title}
  line 2 in yellow: {cover_text.main_subtitle}
- Cream feature strip: {cover_text.feature_text}
- Bottom cream info card:
  title: {cover_text.bottom_title}
  subtitle: {cover_text.bottom_subtitle}
  red tag: {cover_text.bottom_tag}

Design details:
- Top labels should sit at the upper-left, with soft realistic shadow.
- Top cream label and red label must be completely visible, not clipped.
- Main black title block should be large, bold, and anchored over the left side of the middle/lower-middle area.
- Feature strip should sit below the black title block.
- Bottom info card should be compact and low, not covering too much image.
- Bottom info card and bottom-right play button must be completely visible, not clipped.
- Bottom card needs a red starburst icon on the left, a subtle vertical dashed separator on the right, and a yellow hand-drawn heart.
- Bottom-right play button is a cream/white circle with a red play triangle.
- Text must be sharp, large, and correctly spelled.
- Preserve the people and lifestyle scene from the input screenshots as much as possible.
""".strip()


def build_iteration_prompt(instruction: str, lock_layout: bool = True) -> str:
    user_instruction = instruction.strip()
    if not user_instruction:
        raise ValueError("请先填写本次修改意见。")

    parts = [
        "你正在编辑一张已经生成好的短视频封面图。",
        "输入图就是当前基准图 current_baseline.png，请基于它继续做局部迭代。",
        ITERATION_BASE_RULES,
    ]
    if lock_layout:
        parts.append(LOCK_LAYOUT_RULES)
    parts.extend(
        [
            "本次修改意见：",
            user_instruction,
            "输出一张完整 PNG 封面图。文字必须清晰、准确，不要出现错字、乱码或重复字。",
        ]
    )
    return "\n\n".join(parts)


def _save_uploads_to_temp_files(images: Iterable[BinaryIO | str | Path]) -> list[str]:
    paths: list[str] = []
    for index, image in enumerate(images, 1):
        if isinstance(image, str | Path):
            source = Path(image)
            if not source.exists():
                raise FileNotFoundError(f"找不到图片：{source}")
            suffix = source.suffix.lower() if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{index}{suffix}")
            temp.close()
            shutil.copyfile(source, temp.name)
            paths.append(temp.name)
            continue

        suffix = Path(getattr(image, "name", "")).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            suffix = ".png"
        image.seek(0)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{index}{suffix}")
        temp.write(image.read())
        temp.close()
        paths.append(temp.name)
    return paths


def _normalize_to_output_size(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    src_w, src_h = image.size
    target_ratio = CANVAS_WIDTH / CANVAS_HEIGHT
    source_ratio = src_w / src_h

    if abs(source_ratio - target_ratio) > 0.02:
        raise RuntimeError(
            f"AI 接口返回尺寸是 {src_w}x{src_h}，不是 3:4。为避免裁掉顶部/底部元素，已停止后处理。"
            f"请确认网关支持 size={AI_WORK_SIZE}，或改用固定模板。"
        )

    scale = max(CANVAS_WIDTH / src_w, CANVAS_HEIGHT / src_h)
    resized = image.resize((round(src_w * scale), round(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - CANVAS_WIDTH) // 2)
    top = max(0, (resized.height - CANVAS_HEIGHT) // 2)
    return resized.crop((left, top, left + CANVAS_WIDTH, top + CANVAS_HEIGHT))


def _decode_image_payload(payload) -> bytes:
    if isinstance(payload, bytes):
        return payload

    if not isinstance(payload, str):
        raise RuntimeError(f"图片接口返回了无法识别的数据类型：{type(payload).__name__}")

    value = payload.strip()
    if not value:
        raise RuntimeError("图片接口返回为空。")

    if value.startswith("{") or value.startswith("["):
        return _decode_image_payload(json.loads(value))

    if value.lower().startswith("<!doctype html") or value.lower().startswith("<html"):
        raise RuntimeError("图片接口返回了网页 HTML，不是 API 数据。请确认 Base URL 是 API 地址，例如：https://www.aiartmirror.com/v1")

    if value.startswith("data:image"):
        _, encoded = value.split(",", 1)
        return base64.b64decode(encoded)

    if value.startswith("http://") or value.startswith("https://"):
        response = requests.get(value, timeout=120)
        response.raise_for_status()
        return response.content

    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise RuntimeError(f"图片接口返回了字符串，但不是图片 URL 或 base64：{value[:160]}") from exc


def _extract_image_bytes(result) -> bytes:
    if isinstance(result, str):
        return _decode_image_payload(result)

    if isinstance(result, Mapping):
        data = result.get("data")
        if data:
            if isinstance(data, list) and data:
                return _extract_image_bytes(data[0])
            return _extract_image_bytes(data)
        for key in ("b64_json", "base64", "image", "url", "output"):
            if result.get(key):
                return _decode_image_payload(result[key])
        raise RuntimeError(f"图片接口返回 JSON，但没有找到图片字段：{str(result)[:220]}")

    data = getattr(result, "data", None)
    if data:
        item = data[0]
        image_base64 = getattr(item, "b64_json", None)
        image_url = getattr(item, "url", None)
        if image_base64:
            return _decode_image_payload(image_base64)
        if image_url:
            return _decode_image_payload(image_url)

    raise RuntimeError(f"图片接口返回格式暂不支持：{type(result).__name__}")


def generate_ai_cover(
    images: list[BinaryIO],
    text: CoverText | Mapping[str, str],
    output_path: str | Path | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    image_size: str | None = None,
) -> Image.Image:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未设置 API Key。请在左侧「AI 接口设置」里填写 API Key，或在终端设置 OPENAI_API_KEY。")

    if len(images) != 3:
        raise ValueError("AI 生成也需要正好 3 张图片。")

    reference_path = Path(REFERENCE_PATH)
    if not reference_path.exists():
        raise FileNotFoundError(f"没有找到参考模板：{reference_path}")

    base_url = normalize_base_url(base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or os.getenv("NEWAPI_BASE_URL"))
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    temp_paths = _save_uploads_to_temp_files(images)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = Path(tmpdir) / "ai_cover.png"
            files = [reference_path.open("rb")] + [open(path, "rb") for path in temp_paths]
            try:
                result = client.images.edit(
                    model=AI_MODEL,
                    image=files,
                    prompt=build_cover_prompt(text),
                    size=image_size or AI_WORK_SIZE,
                    quality="high",
                )
            finally:
                for file in files:
                    file.close()

            result_path.write_bytes(_extract_image_bytes(result))
            image = _normalize_to_output_size(Image.open(result_path))

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, "PNG", optimize=True)
        return image
    finally:
        for path in temp_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


def default_ai_output_path(cover_id: str) -> Path:
    safe_id = str(cover_id).strip() or "cover"
    return OUTPUT_DIR / f"{safe_id}_ai.png"


def generate_iteration_cover(
    baseline_path: str | Path,
    instruction: str,
    output_path: str | Path,
    api_key: str | None = None,
    base_url: str | None = None,
    image_size: str | None = None,
    lock_layout: bool = True,
) -> Image.Image:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未设置 API Key。请在左侧「AI 接口设置」里填写 API Key，或在终端设置 OPENAI_API_KEY。")

    baseline_path = Path(baseline_path)
    if not baseline_path.exists():
        raise FileNotFoundError(f"没有找到当前基准图：{baseline_path}")

    base_url = normalize_base_url(base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or os.getenv("NEWAPI_BASE_URL"))
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    with tempfile.TemporaryDirectory() as tmpdir:
        result_path = Path(tmpdir) / "iteration_cover.png"
        with baseline_path.open("rb") as baseline_file:
            result = client.images.edit(
                model=AI_MODEL,
                image=[baseline_file],
                prompt=build_iteration_prompt(instruction, lock_layout=lock_layout),
                size=image_size or AI_WORK_SIZE,
                quality="high",
            )

        result_path.write_bytes(_extract_image_bytes(result))
        image = _normalize_to_output_size(Image.open(result_path))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG", optimize=True)
    return image
