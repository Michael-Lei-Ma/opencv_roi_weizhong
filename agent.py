import time
import threading
from pynput import mouse
import imagehash
from PIL import Image
import numpy as np
import cv2


class Agent:
    def __init__(self, detector, screenshot_func, upload_manager=None):
        self.detector = detector
        self.screenshot_func = screenshot_func
        self.upload_manager = upload_manager

        self.last_hash = None
        self.current_page = None
        self.running = False
        self.listener = None

        self.lock = threading.Lock()

        # 参数（可调）
        self.delay = 0.3
        self.hash_threshold = 3
        self.stable_required = 2

    # =========================
    # 🎯 事件入口
    # =========================
    def trigger(self, event_type):
        if self.lock.locked():
            return

        def run():
            with self.lock:
                print(f"[EVENT] {event_type}")

                # ① 等UI开始变化
                time.sleep(self.delay)
                screenshot = self.screenshot_func()
                # ② 判断页面是否变化
                is_page_change = self.is_significant_change(screenshot)
                if not is_page_change:
                    return

                # ③ 页面识别（带防抖）
                page, score = self.detector.detect(screenshot)

                print(f"[DETECT] {page} ({score:.3f})")

                # ④ 状态机处理
                self.handle_state(page, screenshot, is_page_change)

        threading.Thread(target=run, daemon=True).start()


    def is_significant_change(self, screenshot):
        hash_value = imagehash.phash(Image.fromarray(screenshot))

        if self.last_hash is not None and hash_value - self.last_hash < 3:
            return False

        self.last_hash = hash_value
        return True


    # =========================
    # 🧠 状态机（核心）
    # =========================
    def handle_state(self, new_page, screenshot, is_page_change):
        old_page = self.current_page

        if new_page == "detecting":
            return

        if new_page == old_page and is_page_change:
            self.on_update(new_page, screenshot)
            return

        # 页面离开
        if old_page:
            self.on_leave(old_page)

        # 页面进入
        if new_page != "unknown":
            self.on_enter(new_page, screenshot)

        self.current_page = new_page

    # =========================
    # 🎬 页面进入动作
    # =========================
    def on_enter(self, page, screenshot):
        print(f"[ENTER] {page}")

        # 👉 你可以在这里扩展
        if page == "basic_info":
            self.handle_basic_info(screenshot)

        elif page == "important_info":
            self.handle_important_info(screenshot)
        elif page == "case_circulation_record":
            self.handle_case_circulation_record(screenshot)

    # =========================
    # 🎬 页面离开动作
    # =========================
    def on_leave(self, page):
        print(f"[LEAVE] {page}")


    def on_update(self, page, screenshot):
        # 👉 滚动 / 点击 / 局部变化 都会进这里
        print(f"[UPDATE] {page}")

        if page == "basic_info":
            self.handle_basic_info(screenshot)
        elif page == "important_info":
            self.handle_important_info(screenshot)
        elif page == "case_circulation_record":
            self.handle_case_circulation_record(screenshot)

    # =========================
    # 📸 业务逻辑（示例）
    # =========================
    def handle_basic_info(self, screenshot):
        print("👉 处理基础信息+地址页")
        self._enqueue_upload(screenshot, 'basic_info')

        # 👉 后面可以接 OCR / 数据提取
    def handle_important_info(self, screenshot):
        print("👉 处理重要信息+电话信息页")
        self._enqueue_upload(screenshot, 'important_info')

        # 👉 后面可以接 OCR / 数据提取
    def handle_case_circulation_record(self, screenshot):
        print("👉 处理案件流转记录页")
        self._enqueue_upload(screenshot, 'case_circulation_record')

    def _enqueue_upload(self, screenshot, page_tag):
        if self.upload_manager is None:
            print("[WARN] upload_manager not configured, skip upload")
            return
        success, buffer = cv2.imencode('.png', screenshot)
        if not success:
            print(f"[ERROR] PNG encode failed for {page_tag}")
            return
        path = self.upload_manager.enqueue(buffer.tobytes(), page_tag)
        print(f"[QUEUE] queued upload: {path}")

    # =========================
    # 🖱️ 启动监听
    # =========================
    def start(self):
        if self.running:
            return
        self.listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener.start()
        self.running = True

    def stop(self):
        if self.listener is not None and self.running:
            self.listener.stop()
            self.listener = None
        self.running = False

    def join(self):
        if self.listener is not None:
            self.listener.join()

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.trigger("click")

    def on_scroll(self, x, y, dx, dy):
        self.trigger("scroll")