import base64
import os
import sys
import subprocess
import cv2
import mss
import mss.windows  # 🔥关键
import numpy as np
from flask import Flask, jsonify, render_template, request
from detector import MultiROIDetector
from agent import Agent
from upload_manager import UploadManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, ".upload_cache")
SOURCES_DIR = os.path.join(BASE_DIR, "sources")
TEMP_SCREENSHOT = os.path.join(BASE_DIR, "temp_screenshot.png")
PREVIEW_FILE = TEMP_SCREENSHOT
OVERLAY_SCRIPT = os.path.join(BASE_DIR, "overlay_helper.py")
UPLOAD_URL = "http://127.0.0.1:8001/upload"
UPLOAD_TOKEN = "cbf123456"

overlay_process = None

os.makedirs(SOURCES_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# 自动截图识别 + 缓存上传

detector = MultiROIDetector("templates")
upload_manager = UploadManager(UPLOAD_URL, UPLOAD_TOKEN, cache_dir=CACHE_DIR, reset_count=True)
agent = Agent(detector, lambda: screenshot(), upload_manager=upload_manager)

app = Flask(__name__, template_folder="templates")


def screenshot():
    with mss.mss() as sct:
        screen_shot = np.array(sct.grab(sct.monitors[1]))
        img_bgr = cv2.cvtColor(screen_shot, cv2.COLOR_BGRA2BGR)
        return img_bgr


def init_services(start_agent=True):
    upload_manager.start()
    if start_agent:
        agent.start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    status = upload_manager.get_status()
    status['auto_running'] = agent.running
    status['overlay_running'] = overlay_process is not None and overlay_process.poll() is None
    status['preview_exists'] = os.path.exists(PREVIEW_FILE)
    # 添加pending_files列表
    status['pending_files'] = [os.path.basename(p) for p in upload_manager.pending_files()]
    return jsonify(status)


@app.route('/api/start_auto', methods=['POST'])
def api_start_auto():
    if agent.running:
        return jsonify({'status': 'already_running'})
    agent.start()
    return jsonify({'status': 'started'})


@app.route('/api/stop_auto', methods=['POST'])
def api_stop_auto():
    if not agent.running:
        return jsonify({'status': 'not_running'})
    agent.stop()
    return jsonify({'status': 'stopped'})


@app.route('/api/start_overlay', methods=['POST'])
def api_start_overlay():
    global overlay_process
    if overlay_process is not None and overlay_process.poll() is None:
        return jsonify({'status': 'already_running'})
    overlay_process = subprocess.Popen([sys.executable, OVERLAY_SCRIPT], cwd=BASE_DIR)
    return jsonify({'status': 'started'})


@app.route('/api/stop_overlay', methods=['POST'])
def api_stop_overlay():
    global overlay_process
    if overlay_process is not None and overlay_process.poll() is None:
        overlay_process.terminate()
        overlay_process = None
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'not_running'})


@app.route('/api/latest_screenshot')
def api_latest_screenshot():
    if os.path.exists(TEMP_SCREENSHOT):
        with open(TEMP_SCREENSHOT, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        return jsonify({'image': f'data:image/png;base64,{img_data}'})
    return jsonify({'error': '没有最新截图'}), 404


@app.route('/api/manual_screenshot', methods=['POST'])
def api_manual_screenshot():
    try:
        image = screenshot()
        success, buffer = cv2.imencode('.png', image)
        if not success:
            return jsonify({'error': '截图编码失败'}), 500
        png_bytes = buffer.tobytes()
        with open(PREVIEW_FILE, 'wb') as f:
            f.write(png_bytes)
        data = base64.b64encode(png_bytes).decode('utf-8')
        return jsonify({'image': f'data:image/png;base64,{data}'})
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@app.route('/api/upload_manual', methods=['POST'])
def api_upload_manual():
    if not os.path.exists(PREVIEW_FILE):
        return jsonify({'error': '没有可上传的截图'}), 400
    with open(PREVIEW_FILE, 'rb') as f:
        png_bytes = f.read()
    uploaded_path = upload_manager.enqueue(png_bytes, page_tag='manual')
    return jsonify({'status': 'queued', 'path': os.path.basename(uploaded_path)})


@app.route('/api/save', methods=['POST'])
def api_save():
    data = request.json or {}
    filename = (data.get('filename') or '').strip()
    if not filename:
        return jsonify({'error': '文件名不能为空'}), 400
    if not os.path.exists(PREVIEW_FILE):
        return jsonify({'error': '没有可保存的截图'}), 400
    safe_name = os.path.basename(filename)
    target = os.path.join(SOURCES_DIR, safe_name)
    try:
        os.replace(PREVIEW_FILE, target)
        return jsonify({'status': 'saved', 'target': safe_name})
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    if os.path.exists(PREVIEW_FILE):
        os.remove(PREVIEW_FILE)
    return jsonify({'status': 'cancelled'})


@app.route('/api/cache_files')
def api_cache_files():
    files = upload_manager.pending_files()
    return jsonify({'files': [os.path.basename(p) for p in files], 'count': len(files)})


if __name__ == '__main__':
    init_services(start_agent=True)
    app.run(host='127.0.0.1', port=5000, debug=True)
