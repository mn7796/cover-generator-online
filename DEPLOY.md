# 线上部署说明

这个目录是部署专用项目：`生图网站_线上部署版`。

原本地稳定版在：

```text
/Users/mn/Documents/生主图
```

不要在原项目里做线上部署改动。线上相关修改只放在当前部署版项目里。

## 1. 创建 GitHub 仓库

1. 打开 GitHub。
2. 点击右上角 `+`，选择 `New repository`。
3. 仓库名可以写：`cover-generator-online`。
4. 建议先选 `Private`。
5. 不要勾选自动创建 README、.gitignore、license，因为本地项目里已经有这些文件。
6. 创建仓库后，GitHub 会显示一个远程地址，例如：

```text
https://github.com/你的用户名/cover-generator-online.git
```

## 2. 推送部署版到 GitHub

进入部署版目录：

```bash
cd /Users/mn/Documents/生图网站_线上部署版
```

确认当前状态：

```bash
git status
```

如果还没有提交部署适配改动：

```bash
git add .
git commit -m "prepare_streamlit_online_deploy"
```

添加 GitHub 远程仓库：

```bash
git remote add origin https://github.com/你的用户名/cover-generator-online.git
```

如果已经有 origin，可以改成：

```bash
git remote set-url origin https://github.com/你的用户名/cover-generator-online.git
```

推送当前分支：

```bash
git push -u origin optimize_v2
```

## 3. 打开 Streamlit Community Cloud

1. 打开 [https://share.streamlit.io](https://share.streamlit.io)。
2. 使用 GitHub 登录。
3. 点击 `Create app` 或 `New app`。
4. 选择刚才的 GitHub 仓库。

## 4. 选择 Repo、Branch、入口文件

部署配置填写：

```text
Repository: 你的用户名/cover-generator-online
Branch: optimize_v2
Main file path: app.py
```

确认 `app.py` 在项目根目录。

## 5. 配置 Secrets

在 Streamlit Cloud 的 App 设置里找到 `Secrets`，填入：

```toml
APP_PASSWORD = "给朋友使用的访问密码"
OPENAI_API_KEY = "你的真实 API Key"
OPENAI_BASE_URL = "https://www.aiartmirror.com/v1"
```

说明：

- `APP_PASSWORD`：朋友打开网页后需要输入的访问密码。
- `OPENAI_API_KEY`：用于 `gpt-image-2 AI 精修` 和迭代修改。
- `OPENAI_BASE_URL`：如果使用 OpenAI 官方接口，可删除这一行或改成官方兼容地址；如果使用 aiartmirror，就保持上面的值。

不要把真实 key 写进代码，也不要提交 `.streamlit/secrets.toml`。

## 6. 部署并获取链接

点击 `Deploy`。

部署成功后，Streamlit 会给你一个线上链接，类似：

```text
https://你的-app-name.streamlit.app
```

把这个链接和 `APP_PASSWORD` 发给朋友即可。

## 7. 部署失败怎么看日志

在 Streamlit Cloud App 页面点击：

```text
Manage app -> Logs
```

常见问题：

- `ModuleNotFoundError`：检查 `requirements.txt` 是否包含缺失依赖。
- `No secrets found`：检查 Streamlit Cloud 里的 Secrets 是否保存成功。
- `OPENAI_API_KEY` 报错：检查 API Key 是否有效，Base URL 是否正确。
- 找不到参考图：检查 `assets/reference/template.png` 是否已提交到 GitHub。

## 8. 线上版不满意，怎么回到原稳定版

原稳定项目没有被部署适配改动影响，仍在：

```text
/Users/mn/Documents/生主图
```

回到本地稳定版：

```bash
cd /Users/mn/Documents/生主图
git switch optimize_v2
git reset --hard stable_local_before_online_deploy
```

如果只是临时查看最早确认的模板稳定版：

```bash
cd /Users/mn/Documents/生主图
git switch --detach stable_v1_confirmed_template
```

看完后回到当前稳定分支：

```bash
git switch optimize_v2
```

## 9. 部署版和原项目的关系

- 原项目：`/Users/mn/Documents/生主图`
- 部署版：`/Users/mn/Documents/生图网站_线上部署版`

以后所有线上部署、密码、Secrets、Streamlit Cloud 相关配置，只改部署版。
