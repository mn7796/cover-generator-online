from __future__ import annotations

import io
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from ai_generate import default_ai_output_path, generate_ai_cover, generate_iteration_cover
from config import BASE_DIR, DEFAULT_TEXT, INPUT_DIR, ITERATIONS_DIR, OUTPUT_DIR
from generate import CoverText, draw_cover, ensure_dirs, read_csv_rows


st.set_page_config(page_title="短视频封面批量生成工具", page_icon="🎬", layout="wide")
ensure_dirs()


def get_secret_value(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return str(value or os.getenv(name, default) or "").strip()


def require_app_password() -> None:
    expected_password = get_secret_value("APP_PASSWORD")
    if not expected_password:
        st.error("线上部署版未配置 APP_PASSWORD。请先在 Streamlit Secrets 里配置访问密码。")
        st.stop()

    if st.session_state.get("app_authenticated"):
        return

    st.title("短视频封面批量生成工具")
    st.caption("请输入访问密码后继续使用。")
    entered_password = st.text_input("访问密码", type="password")
    if st.button("进入", type="primary"):
        if entered_password == expected_password:
            st.session_state["app_authenticated"] = True
            st.rerun()
        st.error("密码不正确，请重新输入。")
    st.stop()


def safe_error_message(exc: Exception) -> str:
    message = str(exc)
    if "sk-" in message:
        start = message.find("sk-")
        end = message.find(" ", start)
        if end == -1:
            end = min(len(message), start + 80)
        message = message[:start] + "sk-***" + message[end:]
    return message


def text_inputs(prefix: str = "") -> dict[str, str]:
    return {
        "top_label": st.text_input("顶部标签 top_label", DEFAULT_TEXT["top_label"], key=f"{prefix}top_label"),
        "red_tag": st.text_input("红色标签 red_tag", DEFAULT_TEXT["red_tag"], key=f"{prefix}red_tag"),
        "main_title": st.text_input("中间主标题 main_title", DEFAULT_TEXT["main_title"], key=f"{prefix}main_title"),
        "main_subtitle": st.text_input("中间副标题 main_subtitle", DEFAULT_TEXT["main_subtitle"], key=f"{prefix}main_subtitle"),
        "feature_text": st.text_input("小条文字 feature_text", DEFAULT_TEXT["feature_text"], key=f"{prefix}feature_text"),
        "bottom_title": st.text_input("底部主标题 bottom_title", DEFAULT_TEXT["bottom_title"], key=f"{prefix}bottom_title"),
        "bottom_subtitle": st.text_input("底部副标题 bottom_subtitle", DEFAULT_TEXT["bottom_subtitle"], key=f"{prefix}bottom_subtitle"),
        "bottom_tag": st.text_input("底部红色标签 bottom_tag", DEFAULT_TEXT["bottom_tag"], key=f"{prefix}bottom_tag"),
    }


def image_to_bytes(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def make_zip(paths: list[Path]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, arcname=path.name)
    return buffer.getvalue()


def resolve_output_dir(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_iterations_dir(output_dir: Path) -> Path:
    if output_dir == OUTPUT_DIR:
        return ITERATIONS_DIR
    return output_dir / "iterations"


def get_current_baseline_path(iterations_dir: Path) -> Path:
    return iterations_dir / "current_baseline.png"


def set_iteration_baseline(source_path: Path, iterations_dir: Path) -> Path:
    iterations_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = get_current_baseline_path(iterations_dir)
    shutil.copyfile(source_path, baseline_path)
    return baseline_path


def next_iteration_path(iterations_dir: Path) -> Path:
    iterations_dir.mkdir(parents=True, exist_ok=True)
    max_index = 0
    for path in iterations_dir.glob("iter_*.png"):
        try:
            max_index = max(max_index, int(path.stem.removeprefix("iter_")))
        except ValueError:
            continue
    return iterations_dir / f"iter_{max_index + 1:03d}.png"


def latest_iteration_path(iterations_dir: Path) -> Path | None:
    paths = sorted(iterations_dir.glob("iter_*.png"), key=lambda path: path.stat().st_mtime, reverse=True)
    return paths[0] if paths else None


def latest_cover_path(output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    candidates = []
    for path in output_dir.glob("*.png"):
        if path.name in {"stable_v1_sample.png", ".gitkeep"}:
            continue
        candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def get_image_sources(uploads: list, fallback_folder: Path) -> list | None:
    provided = [file is not None for file in uploads]
    if any(provided):
        if not all(provided):
            raise ValueError("这个模块如果上传图片，需要一次上传上图、中图、下图三张。")
        for file in uploads:
            file.seek(0)
        return uploads

    image_paths = [fallback_folder / "1.png", fallback_folder / "2.png", fallback_folder / "3.png"]
    missing = [str(path) for path in image_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"缺少图片：{', '.join(missing)}")
    return image_paths


def generate_with_mode(
    sources: list,
    cover_text: CoverText,
    output_path: Path,
    mode: str,
    api_key: str,
    base_url: str,
    image_size: str,
):
    if mode == "固定模板":
        return draw_cover(sources, cover_text, output_path)
    return generate_ai_cover(
        sources,
        cover_text,
        output_path,
        api_key=api_key.strip() or None,
        base_url=base_url.strip() or None,
        image_size=image_size.strip() or None,
    )


def render_iteration_page(output_dir: Path, api_key: str, base_url: str, image_size: str) -> None:
    iterations_dir = get_iterations_dir(output_dir)
    iterations_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = get_current_baseline_path(iterations_dir)

    if not baseline_path.exists():
        latest_cover = latest_cover_path(output_dir)
        if latest_cover:
            set_iteration_baseline(latest_cover, iterations_dir)
            st.info(f"已用最近生成图初始化当前基准图：{latest_cover.name}")

    baseline_exists = baseline_path.exists()
    latest_iter = st.session_state.get("latest_iteration_path")
    latest_path = Path(latest_iter) if latest_iter else latest_iteration_path(iterations_dir)
    if latest_path and not latest_path.exists():
        latest_path = latest_iteration_path(iterations_dir)

    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        st.subheader("迭代设置")
        st.caption(f"版本目录：{iterations_dir}")
        lock_layout = st.toggle("锁定版式", value=True)
        instruction = st.text_area(
            "本次修改意见",
            placeholder="左上角 Vlog 3 改成 Vlog 4；白色小条里的“让女生变穷的消费习惯”后面加上(2)；其他不变。",
            height=150,
        )
        iterate_btn = st.button("基于上一版生成迭代图", type="primary", use_container_width=True)

        if iterate_btn:
            if not baseline_exists:
                st.error("还没有 current_baseline.png。请先在「新建封面」生成一张图，或把基准图放到迭代目录。")
            elif not instruction.strip():
                st.error("请先填写本次修改意见。")
            else:
                try:
                    output_path = next_iteration_path(iterations_dir)
                    with st.spinner("正在基于上一版做局部迭代，请稍等..."):
                        image = generate_iteration_cover(
                            baseline_path,
                            instruction,
                            output_path,
                            api_key=api_key.strip() or None,
                            base_url=base_url.strip() or None,
                            image_size=image_size.strip() or None,
                            lock_layout=lock_layout,
                        )
                    st.session_state["latest_iteration_path"] = str(output_path)
                    latest_path = output_path
                    st.success(f"已保存到：{output_path}")
                    st.image(image, use_container_width=True)
                except Exception as exc:
                    st.error(safe_error_message(exc))

    with right:
        st.subheader("当前基准图")
        if baseline_path.exists():
            st.image(str(baseline_path), use_container_width=True)
        else:
            st.warning("当前还没有基准图。先在「新建封面」里生成一张图后，再回来迭代。")

        st.divider()
        st.subheader("最新迭代图")
        if latest_path and latest_path.exists():
            st.image(str(latest_path), use_container_width=True)
            st.download_button(
                "下载最新迭代图",
                data=latest_path.read_bytes(),
                file_name=latest_path.name,
                mime="image/png",
                use_container_width=True,
            )
            if st.button("设为新的基准图", use_container_width=True):
                set_iteration_baseline(latest_path, iterations_dir)
                st.success("已设为新的 current_baseline.png。下一次会基于它继续迭代。")
                st.rerun()
        else:
            st.info("完成一次迭代后，这里会显示最新结果。")


def add_history(record: dict) -> None:
    st.session_state.setdefault("single_history", [])
    st.session_state["single_history"].insert(0, record)
    st.session_state["single_history"] = st.session_state["single_history"][:20]


def make_default_module(index: int, row: CoverText | None = None) -> dict:
    row = row or CoverText.from_mapping({"id": f"{index:03d}"})
    return {
        "id": row.id or f"{index:03d}",
        "top_label": row.top_label,
        "red_tag": row.red_tag,
        "main_title": row.main_title,
        "main_subtitle": row.main_subtitle,
        "feature_text": row.feature_text,
        "bottom_title": row.bottom_title,
        "bottom_subtitle": row.bottom_subtitle,
        "bottom_tag": row.bottom_tag,
    }


def ensure_batch_modules() -> None:
    if "batch_modules" not in st.session_state:
        csv_path = INPUT_DIR / "covers.csv"
        if csv_path.exists():
            rows = read_csv_rows(csv_path)
            st.session_state["batch_modules"] = [make_default_module(i, row) for i, row in enumerate(rows, 1)]
        else:
            st.session_state["batch_modules"] = [make_default_module(1)]


require_app_password()

st.title("短视频封面批量生成工具")
st.caption("固定模板生成 1080x1440 PNG，小红书/抖音英语学习类封面。")

with st.sidebar:
    st.subheader("输出设置")
    output_dir_text = st.text_input("默认生成目录", value=str(OUTPUT_DIR))
    try:
        selected_output_dir = resolve_output_dir(output_dir_text)
        st.caption(f"当前输出目录：{selected_output_dir}")
    except Exception as exc:
        st.error(f"输出目录不可用：{safe_error_message(exc)}")
        selected_output_dir = OUTPUT_DIR

    st.subheader("AI 接口设置")
    secret_api_key = get_secret_value("OPENAI_API_KEY")
    secret_base_url = get_secret_value("OPENAI_BASE_URL", "https://www.aiartmirror.com/v1")
    ai_api_key_override = st.text_input("API Key 临时覆盖", type="password", help="线上优先使用 Secrets 里的 OPENAI_API_KEY；这里仅用于临时覆盖，不会写入项目文件。")
    ai_api_key = ai_api_key_override.strip() or secret_api_key
    ai_base_url = st.text_input("Base URL", value=secret_base_url or "https://www.aiartmirror.com/v1")
    ai_image_size = st.text_input("AI 图片尺寸", value="1088x1456")
    st.caption("固定模板不需要 API Key。AI 精修/迭代会优先读取 Streamlit Secrets 或环境变量。")

page_mode = st.radio("模式选择", ["新建封面", "基于上一版迭代修改"], horizontal=True)

if page_mode == "基于上一版迭代修改":
    render_iteration_page(selected_output_dir, ai_api_key, ai_base_url, ai_image_size)
    st.stop()

tab_single, tab_batch = st.tabs(["单张生成", "批量生成"])

with tab_single:
    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        st.subheader("图片")
        img1 = st.file_uploader("上图", type=["png", "jpg", "jpeg", "webp"], key="img1")
        img2 = st.file_uploader("中图", type=["png", "jpg", "jpeg", "webp"], key="img2")
        img3 = st.file_uploader("下图", type=["png", "jpg", "jpeg", "webp"], key="img3")

        st.subheader("文字")
        fields = text_inputs("single_")
        output_id = st.text_input("输出文件名 id", DEFAULT_TEXT["id"])
        generation_mode = st.radio(
            "生成模式",
            ["固定模板", "gpt-image-2 AI 精修"],
            horizontal=True,
            help="AI 精修更接近样例质感；固定模板更稳定、速度更快、文字位置绝对固定。",
        )
        generate_btn = st.button("生成封面", type="primary", use_container_width=True)

    with right:
        st.subheader("预览")
        if generate_btn:
            uploads = [img1, img2, img3]
            if any(file is None for file in uploads):
                st.error("请先上传上图、中图、下图三张图片。")
            else:
                for file in uploads:
                    file.seek(0)
                cover_text = CoverText.from_mapping({"id": output_id, **fields})
                try:
                    with st.spinner("正在生成封面，请稍等..."):
                        if generation_mode == "固定模板":
                            output_path = selected_output_dir / f"{output_id.strip() or 'cover'}.png"
                            image = generate_with_mode(
                                uploads,
                                cover_text,
                                output_path,
                                generation_mode,
                                ai_api_key,
                                ai_base_url,
                                ai_image_size,
                            )
                        else:
                            output_path = selected_output_dir / default_ai_output_path(output_id).name
                            image = generate_with_mode(
                                uploads,
                                cover_text,
                                output_path,
                                generation_mode,
                                ai_api_key,
                                ai_base_url,
                                ai_image_size,
                            )
                        png_bytes = image_to_bytes(image)
                        baseline_path = set_iteration_baseline(output_path, get_iterations_dir(selected_output_dir))
                        add_history(
                            {
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "mode": generation_mode,
                                "path": str(output_path),
                                "file_name": output_path.name,
                            }
                        )
                        st.image(image, use_container_width=True)
                        st.success(f"已保存到：{output_path}")
                        st.caption(f"已同步为迭代基准图：{baseline_path}")
                        st.download_button(
                            "下载 PNG",
                            data=png_bytes,
                            file_name=output_path.name,
                            mime="image/png",
                            use_container_width=True,
                        )
                except Exception as exc:
                    st.error(safe_error_message(exc))
        else:
            st.info("上传 3 张图片并点击生成后，这里会显示预览。")

        history = st.session_state.get("single_history", [])
        if history:
            st.divider()
            st.subheader("生成记录")
            for index, record in enumerate(history, 1):
                path = Path(record["path"])
                if not path.exists():
                    continue
                with st.expander(f"{index}. {record['file_name']} · {record['mode']} · {record['time']}", expanded=index == 1):
                    st.image(str(path), use_container_width=True)
                    st.download_button(
                        "下载这张",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="image/png",
                        key=f"single_history_download_{index}_{path.name}",
                        use_container_width=True,
                    )

with tab_batch:
    st.subheader("批量生成")
    st.write("自定义模块数量。每个模块可以上传 3 张图，也可以读取 `input/<模块ID>/1.png`、`2.png`、`3.png`。")

    ensure_batch_modules()
    csv_file = st.file_uploader("从 CSV 导入模块（可选）", type=["csv"], key="batch_csv")
    batch_mode = st.radio("批量生成模式", ["固定模板", "gpt-image-2 AI 精修"], horizontal=True, key="batch_mode")

    controls = st.columns([1, 1, 1, 1])
    with controls[0]:
        desired_count = st.number_input(
            "模块数量",
            min_value=1,
            max_value=100,
            value=len(st.session_state["batch_modules"]),
            step=1,
        )
    with controls[1]:
        if st.button("应用数量", use_container_width=True):
            current = st.session_state["batch_modules"]
            if desired_count > len(current):
                for i in range(len(current) + 1, desired_count + 1):
                    current.append(make_default_module(i))
            else:
                st.session_state["batch_modules"] = current[:desired_count]
            st.rerun()
    with controls[2]:
        if st.button("增加模块", use_container_width=True):
            st.session_state["batch_modules"].append(make_default_module(len(st.session_state["batch_modules"]) + 1))
            st.rerun()
    with controls[3]:
        if st.button("重置模块", use_container_width=True):
            st.session_state["batch_modules"] = [make_default_module(1)]
            st.rerun()

    if csv_file is not None and st.button("导入 CSV 覆盖当前模块", use_container_width=True):
        temp_csv = INPUT_DIR / "_uploaded_covers.csv"
        temp_csv.write_bytes(csv_file.getvalue())
        rows = read_csv_rows(temp_csv)
        if rows:
            st.session_state["batch_modules"] = [make_default_module(i, row) for i, row in enumerate(rows, 1)]
            st.rerun()
        else:
            st.error("CSV 为空，无法导入。")

    module_configs = []
    st.info(f"当前共有 {len(st.session_state['batch_modules'])} 个模块。")

    for index, module in enumerate(st.session_state["batch_modules"], 1):
        initial_id = module.get("id") or f"{index:03d}"
        module_key = f"batch_{index}_{initial_id}"
        with st.expander(f"模块 {index} · {initial_id}", expanded=index == 1):
            st.caption(f"默认图片目录：input/{initial_id}/")
            image_cols = st.columns(3)
            with image_cols[0]:
                top_image = st.file_uploader("上图", type=["png", "jpg", "jpeg", "webp"], key=f"{module_key}_img1")
            with image_cols[1]:
                middle_image = st.file_uploader("中图", type=["png", "jpg", "jpeg", "webp"], key=f"{module_key}_img2")
            with image_cols[2]:
                bottom_image = st.file_uploader("下图", type=["png", "jpg", "jpeg", "webp"], key=f"{module_key}_img3")

            text_cols = st.columns(2)
            with text_cols[0]:
                module_id = st.text_input("模块 ID / 文件名", initial_id, key=f"{module_key}_id")
                top_label = st.text_input("顶部标题", module["top_label"], key=f"{module_key}_top_label")
                red_tag = st.text_input("红色标签", module["red_tag"], key=f"{module_key}_red_tag")
                main_title = st.text_input("中间主标题", module["main_title"], key=f"{module_key}_main_title")
            with text_cols[1]:
                main_subtitle = st.text_input("中间副标题", module["main_subtitle"], key=f"{module_key}_main_subtitle")
                feature_text = st.text_input("小白条", module["feature_text"], key=f"{module_key}_feature_text")
                bottom_title = st.text_input("底部主标题", module["bottom_title"], key=f"{module_key}_bottom_title")
                bottom_subtitle = st.text_input("底部小标题", module["bottom_subtitle"], key=f"{module_key}_bottom_subtitle")
                bottom_tag = st.text_input("底部红色小标签", module["bottom_tag"], key=f"{module_key}_bottom_tag")

            st.session_state["batch_modules"][index - 1] = {
                "id": module_id,
                "top_label": top_label,
                "red_tag": red_tag,
                "main_title": main_title,
                "main_subtitle": main_subtitle,
                "feature_text": feature_text,
                "bottom_title": bottom_title,
                "bottom_subtitle": bottom_subtitle,
                "bottom_tag": bottom_tag,
            }

            cover_text = CoverText.from_mapping(st.session_state["batch_modules"][index - 1])
            uploads = [top_image, middle_image, bottom_image]
            output_name = f"{module_id}.png" if batch_mode == "固定模板" else f"{module_id}_ai.png"
            output_path = selected_output_dir / output_name
            module_configs.append(
                {
                    "index": index,
                    "id": module_id,
                    "uploads": uploads,
                    "folder": INPUT_DIR / module_id,
                    "text": cover_text,
                    "output_path": output_path,
                }
            )

            if st.button(f"生成模块 {index}", key=f"{module_key}_generate", use_container_width=True):
                try:
                    sources = get_image_sources(uploads, INPUT_DIR / module_id)
                    with st.spinner(f"正在生成模块 {index}..."):
                        image = generate_with_mode(
                            sources,
                            cover_text,
                            output_path,
                            batch_mode,
                            ai_api_key,
                            ai_base_url,
                            ai_image_size,
                        )
                    st.success(f"模块 {index} 已保存到：{output_path}")
                    st.image(image, use_container_width=True)
                    st.download_button(
                        "下载这个模块",
                        data=output_path.read_bytes(),
                        file_name=output_path.name,
                        mime="image/png",
                        key=f"{module_key}_download",
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.error(safe_error_message(exc))

    st.divider()
    all_col, zip_col = st.columns([1, 1])
    with all_col:
        generate_all = st.button("全部生成", type="primary", use_container_width=True)

    generated_paths: list[Path] = []
    if generate_all:
        for config in module_configs:
            try:
                sources = get_image_sources(config["uploads"], config["folder"])
                with st.spinner(f"正在生成模块 {config['index']}..."):
                    generate_with_mode(
                        sources,
                        config["text"],
                        config["output_path"],
                        batch_mode,
                        ai_api_key,
                        ai_base_url,
                        ai_image_size,
                    )
                generated_paths.append(config["output_path"])
            except Exception as exc:
                st.error(f"模块 {config['index']} 失败：{safe_error_message(exc)}")

        if generated_paths:
            st.success(f"全部生成完成：{len(generated_paths)} 张。")
            st.dataframe(
                [{"模块": path.stem, "输出文件": str(path)} for path in generated_paths],
                use_container_width=True,
                hide_index=True,
            )
            with zip_col:
                zip_bytes = make_zip(generated_paths)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "下载全部 ZIP",
                    data=zip_bytes,
                    file_name=f"covers_{stamp}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
