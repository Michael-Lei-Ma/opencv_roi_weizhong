# opencv_roi_weizhong

## 项目概述

`opencv_roi_weizhong` 是一个基于 OpenCV、Flask 和 FastAPI 的 Windows 截图识别与上传系统。它通过屏幕截图、模板匹配和事件驱动的页面检测，自动识别特定页面并将截图缓存后上传到本地上传服务。

## 关键功能

- 自动截屏：使用 `mss` 在 Windows 上抓取主屏幕并转换为 BGR 图像。
- 页面检测：通过 `detector.py` 中的 ROI 模板匹配识别三类页面：
  - `basic_info`
  - `important_info`
  - `case_circulation_record`
- 事件驱动：`agent.py` 监听鼠标点击与滚轮事件，触发截图识别流程。
- 异步缓存上传：`upload_manager.py` 将截图加密存储到缓存目录，并在后台线程中上传到 `app.py` 提供的接口。
- UI / 控制接口：`main.py` 提供 Flask Web 界面和 REST API，用户可以手动截屏、上传、启动/停止自动识别、控制遮罩层，以及查看上传状态。
- 模板生成：`get_template.py` 用于从 `sources/` 中的图片生成 ROI 模板到 `templates/`，并使用 `configs/` 下的 YAML 配置定义裁剪区域。

## 目录结构

- `app.py` - FastAPI 上传服务，监听 `/upload` 接口并保存 PNG 图片。
- `main.py` - Flask Web 应用主入口，提供前端接口和 `Agent` 自动识别服务。
- `web_app.py` - 方便启动 `main.py` 的 wrapper，可直接运行。
- `agent.py` - 自动截图与页面状态管理逻辑。
- `detector.py` - 模板匹配检测逻辑，基于 ROI 比对多个页面模板。
- `upload_manager.py` - 缓存上传队列与重试机制。
- `get_template.py` - 从 `sources/` 图片生成模板 ROI 文件。
- `read_yaml.py` - 辅助读取 YAML 配置（项目中未直接分析，但存在于仓库）。
- `configs/` - ROI 配置文件，控制模板生成坐标。
- `templates/` - 页面模板目录，供 `detector.py` 加载使用。
- `sources/` - 原始截图文件目录，用于生成模板。
- `.upload_cache/` - 上传缓存目录。

## 主要运行方式

### 启动上传接收服务

```powershell
python app.py
```

- 服务在 `0.0.0.0:8001` 运行。
- 接收 POST 请求 `/upload?token=cbf123456`。
- 支持 `application/octet-stream` 和 `image/png`。

### 启动主应用与自动识别服务

```powershell
python web_app.py
```

或直接运行：

```powershell
python main.py
```

- 服务在 `127.0.0.1:5000` 运行。
- 提供页面状态查询和控制接口。

## Flask / REST API 接口

- `GET /api/status` - 查询当前上传状态、自动识别状态、待上传缓存等。
- `POST /api/start_auto` - 启动自动识别服务。
- `POST /api/stop_auto` - 停止自动识别服务。
- `POST /api/start_overlay` - 启动 `overlay_helper.py` 进程。
- `POST /api/stop_overlay` - 停止 overlay 进程。
- `GET /api/latest_screenshot` - 获取最新截图的 Base64 数据。
- `POST /api/manual_screenshot` - 手动截屏并保存为预览。
- `POST /api/upload_manual` - 上传手动截图到缓存队列。
- `POST /api/save` - 保存当前预览截图到 `sources/`。
- `POST /api/cancel` - 取消当前预览截图。
- `GET /api/cache_files` - 查询缓存文件列表。

## 模板与检测

- `detector.py` 从 `templates/` 目录读取每个页面下的 ROI 子目录。
- 通过 `cv2.matchTemplate` 计算每个 ROI 与模板的匹配分数。
- 对每个页面计算平均分数，并选出最高匹配页面。
- 当匹配分数低于阈值时返回 `unknown`。

## 上传缓存机制

- `UploadManager` 会将待上传 PNG 使用 XOR 加密后保存到 `.upload_cache/`。
- 后台线程轮询待上传文件并 POST 到 `app.py` 的 `/upload`。
- 失败时会重试，并将状态写入 `status.json`。

## 依赖说明

项目依赖 `requirements.txt`，其中关键依赖包括：

- `Flask`、`FastAPI`、`uvicorn`
- `opencv-python`
- `numpy`
- `Pillow`、`ImageHash`
- `mss`
- `pynput`
- `requests`
- `ruamel.yaml`

## 运行建议

1. 确保 Windows 环境可用 `mss` 截图。
2. 首先运行 `app.py`，再运行 `web_app.py`。
3. 若模板识别效果不佳，可通过 `get_template.py` 结合 `configs/*.yaml` 重新生成 `templates/`。
4. 检查 `templates/` 下目录是否对应 `basic_info`、`important_info`、`case_circulation_record`。

## 结论

`opencv_roi_weizhong` 是一个面向 Windows 屏幕自动抓图、模板识别与上传的项目，适合用于业务屏幕页的自动化截图提交与缓存管理。该项目以 `main.py`/`web_app.py` 为前端控制入口，以 `app.py` 为图片上传接口，并通过 `agent.py` 和 `detector.py` 构建自动化识别流程。
