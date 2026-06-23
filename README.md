# 短视频封面批量生成工具

一个本地运行的 Streamlit 网页工具，用 `assets/reference/template.png` 作为唯一视觉模板，批量生成小红书/抖音英语学习类短视频封面。

- 输出尺寸：1080 x 1440
- 输出格式：PNG
- 版式：严格参考 `assets/reference/template.png`
- 适合：英语学习、vlog 跟读、口语拆句、精听听写类封面
- 生成方式：固定 Pillow 模板 + 可选 `gpt-image-2 AI 精修`

## 项目结构

```text
vlog-cover-generator/
├── app.py
├── generate.py
├── config.py
├── template_config.py
├── requirements.txt
├── README.md
├── input/
│   ├── covers.csv
│   └── demo/
│       ├── 1.png
│       ├── 2.png
│       └── 3.png
├── output/
└── assets/
    ├── reference/
    │   └── template.png
    └── fonts/
```

当前目录就是项目根目录。`input` 放 CSV 和原图，`output` 放生成后的封面。

## 安装依赖

建议使用 Python 3.10 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置 OpenAI API Key

如果要使用 `gpt-image-2 AI 精修` 模式，需要先配置 API Key：

```bash
export OPENAI_API_KEY="你的 API Key"
```

如果你使用的是 OpenAI 兼容网关，还需要配置接口地址：

```bash
export OPENAI_BASE_URL="https://www.aiartmirror.com"
```

如果只使用固定模板模式，可以不配置 API Key。

AI 精修模式默认请求尺寸为 `1088x1456`，因为很多兼容网关要求宽高都是 16 的倍数。程序会在生成后归一化输出为 `1080x1440`。不要使用 `1024x1536` 这类 2:3 尺寸，否则顶部标签或底部卡片容易被裁掉。

## 设置输出目录

网页左侧有「默认生成目录」输入框。可以填写绝对路径，也可以填写相对项目根目录的路径。

默认值：

```text
/Users/mn/Documents/生主图/output
```

单张生成和批量生成都会保存到这个目录。

## 运行网页版

```bash
streamlit run app.py
```

运行后浏览器会打开本地页面。如果没有自动打开，可以访问终端里显示的地址，通常是：

```text
http://localhost:8501
```

## 如何放参考图

参考图固定放在：

```text
assets/reference/template.png
```

当前项目已按你的路径复制好参考图：

```text
/Users/mn/Downloads/ChatGPT_Image_2026年6月17日_11_16_31.png
```

固定模板的所有关键坐标都写在 `template_config.py`，后续只根据这张参考图调整，不重新设计版式。

## 如何放三张截图

单张生成时，直接在网页里上传 3 张图片：

- 上图
- 中图
- 下图

批量生成时，按下面的结构放图片：

```text
input/
├── covers.csv
├── demo/
│   ├── 1.png
│   ├── 2.png
│   └── 3.png
├── 002/
│   ├── 1.png
│   ├── 2.png
│   └── 3.png
```

每个 `id` 文件夹里必须有 `1.png`、`2.png`、`3.png` 三张图。图片会自动裁切填充，不会被拉伸变形。

## 如何填写 CSV

CSV 文件路径：

```text
input/covers.csv
```

字段必须包含：

```text
id,top_label,red_tag,main_title,main_subtitle,feature_text,bottom_title,bottom_subtitle,bottom_tag
```

示例：

```csv
id,top_label,red_tag,main_title,main_subtitle,feature_text,bottom_title,bottom_subtitle,bottom_tag
demo,Sunday Reset Vlog,适合口语小白拆开练,全英vlog,逐句跟读,听一句｜跟一句｜精听｜听写,Getting My Life Together,Productive Sunday Reset ☁️,Clean With Me & Meal Prep
```

如果某个字段留空，程序会使用 `config.py` 里的默认文字。

## 单张生成

1. 启动网页：`streamlit run app.py`
2. 进入「单张生成」
3. 上传上图、中图、下图
4. 修改文字，也可以保留默认值
5. 选择生成模式：
   - `固定模板`：严格使用 `template_config.py` 坐标，位置稳定，适合批量。
   - `gpt-image-2 AI 精修`：把 `assets/reference/template.png` 作为第一张参考图，再把三张截图交给模型生成，视觉可能更细，但文字和版式稳定性不如固定模板。
6. 点击「生成封面」
7. 页面会显示预览图，并提供 PNG 下载按钮
8. 文件同时保存到 `output/<id>.png`
9. 右侧「生成记录」会保留最近 20 次生成结果，可重新预览和下载

AI 精修模式会保存为：

```text
output/<id>_ai.png
```

## 基于上一版迭代修改

网页顶部「模式选择」可以切换：

```text
新建封面
基于上一版迭代修改
```

选择「基于上一版迭代修改」后，系统会使用：

```text
output/iterations/current_baseline.png
```

作为当前基准图。单张新建封面生成成功后，会自动同步为新的 `current_baseline.png`。如果当前还没有基准图，页面会尝试从输出目录里最近的一张 PNG 初始化。

每次迭代会保存为：

```text
output/iterations/
├── current_baseline.png
├── iter_001.png
├── iter_002.png
└── iter_003.png
```

使用方式：

1. 选择「基于上一版迭代修改」
2. 保持「锁定版式」打开
3. 在「本次修改意见」里写清楚要改哪里
4. 点击「基于上一版生成迭代图」
5. 满意后点击「设为新的基准图」，下一次会继续基于它修改

迭代模式不会改固定模板生成逻辑。它会把固定迭代规则和你的修改意见拼接成 prompt，要求模型只做局部修改，不重做整张图，不改播放按钮、底部信息卡、图片顺序和未提到的文字。

## 批量生成

1. 准备 `input/covers.csv`
2. 按 `input/<id>/1.png`、`2.png`、`3.png` 放好图片
3. 启动网页：`streamlit run app.py`
4. 进入「批量生成」
5. 可以用「模块数量」直接设置模块数，也可以点击「增加模块」
6. 可以上传 CSV 覆盖当前模块，也可以不用 CSV
7. 每个模块可以单独上传上图、中图、下图，也可以使用 `input/<模块ID>/` 下的默认图片
8. 点击模块里的「生成模块」可单独生成
9. 点击底部「全部生成」可一次生成所有模块
10. 生成结果保存到左侧设置的默认生成目录
11. 全部生成后页面会提供 ZIP 下载按钮

当前批量生成默认使用固定模板。这样可以避免大量 API 调用，也能保证每张结构一致、位置不乱。

批量输出示例：

```text
output/
├── demo.png
└── 002.png
```

## 如何修改模板位置

所有关键元素都在 `template_config.py`：

- 画布尺寸
- 三张图区域坐标
- 顶部标签坐标和尺寸
- 红色标签坐标和尺寸
- 黑色标题块坐标和尺寸
- 小白条坐标和尺寸
- 底部信息卡坐标和尺寸
- 播放按钮坐标和尺寸
- 字体大小
- 颜色
- 圆角半径
- 阴影参数

如果要更贴近参考图，只调这个文件，不需要改生成逻辑。

## 如何修改字体路径

字体配置在 `config.py`：

```python
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    ...
]

BOLD_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    ...
]
```

Mac 默认优先使用苹方字体。如果你的机器找不到字体，可以把字体文件放到：

```text
assets/fonts/
```

然后在 `config.py` 里加入完整路径，例如：

```python
str(FONTS_DIR / "YourFont.ttf")
```

建议使用支持中文的字体，例如 PingFang、Noto Sans CJK、思源黑体。

## 常见报错

### 1. ModuleNotFoundError: No module named 'streamlit'

没有安装依赖。执行：

```bash
pip install -r requirements.txt
```

### 2. ModuleNotFoundError: No module named 'openai'

没有安装 OpenAI SDK。执行：

```bash
pip install -r requirements.txt
```

### 3. 未设置 OPENAI_API_KEY

使用 AI 精修模式前，需要在启动 Streamlit 的同一个终端里执行：

```bash
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="https://www.aiartmirror.com"  # 使用兼容网关时才需要
streamlit run app.py
```

### 4. 批量生成提示缺少图片

检查图片路径是否符合：

```text
input/<id>/1.png
input/<id>/2.png
input/<id>/3.png
```

CSV 里的 `id` 必须和文件夹名完全一致，例如 `001` 对应 `input/001/`。

### 5. 中文显示成方块

说明当前字体不支持中文。把中文字体放进 `assets/fonts/`，然后修改 `config.py` 里的 `FONT_CANDIDATES` 和 `BOLD_FONT_CANDIDATES`。

### 6. 标题太长

程序会自动缩小标题字号，底部标题会自动换行。建议主标题保持短句，视觉效果最好。

### 7. 图片比例不一致

程序会自动裁切填充到固定区域，不会变形。为了人像更居中，建议原图主体尽量在画面中间。

## 命令行批量生成

如果不想打开网页，也可以在 Python 里调用：

```python
from generate import batch_generate

batch_generate()
```

默认读取 `input/covers.csv`，输出到 `output/`。

## 稳定版与回退

当前确认满意的稳定版已保存为 Git 标签：

```text
stable_v1_confirmed_template
```

稳定版同时保留了两份对照文件：

```text
template_config_stable_v1.py
output/stable_v1_sample.png
```

后续优化会在 `optimize_v2` 分支上进行。如果优化效果不满意，可以一键回到稳定版：

```bash
cd /Users/mn/Documents/生主图
git switch main
git reset --hard stable_v1_confirmed_template
```

如果只是想临时查看稳定版，不想覆盖当前优化分支，可以执行：

```bash
cd /Users/mn/Documents/生主图
git switch --detach stable_v1_confirmed_template
```

看完后回到优化分支：

```bash
git switch optimize_v2
```
