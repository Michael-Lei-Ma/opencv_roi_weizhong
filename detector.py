import cv2
import numpy as np
import os
from collections import deque, Counter
import time


class MultiROIDetector:
    def __init__(self, template_dir):
        self.templates = {}
        # self.threshold = 0.75
        self.threshold = 0.01
        # 防抖
        self.history = deque(maxlen=5)
        self.stable_threshold = 3

        # debug开关（避免疯狂写文件）
        self.debug = False

        self._load_templates(template_dir)

    def _load_templates(self, template_dir):
        """
        模板加载逻辑：
        templates/
        page1/
        roi_1/
            img1.png
            img2.png
            ...
        """
        for page in os.listdir(template_dir):
            page_path = os.path.join(template_dir, page)
            if not os.path.isdir(page_path):
                continue

            self.templates[page] = {}

            for roi_name in os.listdir(page_path):
                roi_path = os.path.join(page_path, roi_name)
                if not os.path.isdir(roi_path):
                    continue

                self.templates[page][roi_name] = []

                for file in os.listdir(roi_path):
                    img_path = os.path.join(roi_path, file)
                    img = cv2.imread(img_path, 0)
                    if img is not None:
                        self.templates[page][roi_name].append(img)

        print("✅ Templates loaded")

    def match(self, roi_img, template):
        # ✅ 防止 template 比 ROI 大
        h, w = roi_img.shape
        th, tw = template.shape

        if th > h or tw > w:
            return 0  # 直接跳过

        res = cv2.matchTemplate(roi_img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val
    
    # 获取ROI图像,返回字典结构,彩色图片转换成灰度图像素值
    def get_rois(self, gray):
        h, w = gray.shape

        rois = {
            "basic_info": {
                "roi_1": gray[int(0.23*h):int(0.27*h), int(0.2*w):int(0.26*w)],
                "roi_2": gray[int(0.41*h):int(0.453*h), int(0.2*w):int(0.26*w)],
                "roi_3": gray[int(0.232*h):int(0.264*h), int(0.68*w):int(0.73*w)],
                "roi_4": gray[int(0.232*h):int(0.264*h), int(0.744*w):int(0.78*w)],
                "roi_5": gray[int(0.232*h):int(0.264*h), int(0.80*w):int(0.83*w)],
            },
            "important_info": {
                "roi_1": gray[int(0.23*h):int(0.27*h), int(0.2*w):int(0.25*w)],
                "roi_2": gray[int(0.23*h):int(0.27*h), int(0.44*w):int(0.48*w)],
                "roi_3": gray[int(0.58*h):int(0.62*h), int(0.2*w):int(0.25*w)],
                "roi_4": gray[int(0.74*h):int(0.78*h), int(0.2*w):int(0.025*w)],
                "roi_5": gray[int(0.25*h):int(0.29*h), int(0.68*w):int(0.73*w)],
                "roi_6": gray[int(0.25*h):int(0.29*h), int(0.744*w):int(0.78*w)],
                "roi_7": gray[int(0.25*h):int(0.29*h), int(0.825*w):int(0.845*w)],
                "roi_8": gray[int(0.25*h):int(0.29*h), int(0.905*w):int(0.92*w)],
            },
            "case_circulation_record": {
                "roi_1": gray[int(0.23*h):int(0.27*h), int(0.2*w):int(0.23*w)],
                "roi_2": gray[int(0.23*h):int(0.27*h), int(0.23*w):int(0.27*w)],
                "roi_3": gray[int(0.23*h):int(0.26*h), int(0.35*w):int(0.37*w)],
                "roi_4": gray[int(0.23*h):int(0.26*h), int(0.45*w):int(0.49*w)],
                "roi_5": gray[int(0.23*h):int(0.26*h), int(0.56*w):int(0.6*w)],
            },
        }

        return rois

    def detect_once(self, screenshot):
        # 彩色图片转换成灰度图像素值
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        rois = self.get_rois(gray)

        best_page = None
        best_score = 0

        for page, roi_dict in self.templates.items():
            if page not in rois:
                continue  # ✅ 修复：防止 key 不存在

            total_score = 0
            roi_count = 0

            for roi_name, templates in roi_dict.items():
                if roi_name not in rois[page]:
                    continue  # ✅ 修复核心 bug

                roi_img = rois[page][roi_name]

                if roi_img.size == 0:
                    continue

                roi_best = 0

                for template in templates:
                    try:
                        """计算匹配分数,并取当前 ROI 的最高分数,作为该 ROI 的匹配结果,
                        之后计算所有 ROI 的平均分数,作为页面的匹配结果，
                        最后选取匹配结果最高的页面作为最终识别结果，
                        这样可以避免单个 ROI 匹配失败导致整个页面识别失败的情况，
                        同时也能提高识别的稳定性和准确性。
                        roi_img: 当前截图中裁剪出的 ROI 图像
                        template: 预先定义好的模板图像
                        """
                        score = self.match(roi_img, template)
                        roi_best = max(roi_best, score)
                        # cv2.imwrite(f"outputs/{page}_{roi_name}.png", roi_img)

                    except Exception as e:
                        print(f"Error matching {page}-{roi_name}: {e}")
                        continue

                total_score += roi_best
                roi_count += 1

            if roi_count > 0:
                avg_score = total_score / roi_count

                if avg_score > best_score:
                    best_score = avg_score
                    best_page = page

        if best_score < self.threshold:
            return "unknown", best_score

        return best_page, best_score

    def detect(self, screenshot):
        page, score = self.detect_once(screenshot)
        return page, score