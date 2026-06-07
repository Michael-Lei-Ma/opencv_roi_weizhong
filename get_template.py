import cv2
import os
import time
import shutil

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
CONFIGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
SOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources")
OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


# =====================
# YAML 读取
# =====================
def load_yaml_file(file_path):
    try:
        import yaml
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except ImportError:
        from ruamel.yaml import YAML

        yaml_loader = YAML(typ="safe")
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml_loader.load(file)


# =====================
# 初始化目录
# =====================
def init_dirs(roi_config, output_dir):
    for roi_name in roi_config.keys():
        path = os.path.join(output_dir, roi_name)
        os.makedirs(path, exist_ok=True)


# =====================
# ROI裁剪
# =====================
def crop_rois(img, roi_config):
    h, w = img.shape[:2]
    print(f"裁剪图片大小: h={h}, w={w}")
    rois = {}

    for name, (y1, y2, x1, x2) in roi_config.items():
        y1i = max(0, min(int(round(y1 * h)), h))
        y2i = max(0, min(int(round(y2 * h)), h))
        x1i = max(0, min(int(round(x1 * w)), w))
        x2i = max(0, min(int(round(x2 * w)), w))

        if y2i <= y1i or x2i <= x1i:
            print(f"跳过无效 ROI: {name} -> {(y1, y2, x1, x2)}")
            continue

        roi = img[y1i:y2i, x1i:x2i]
        rois[name] = roi

    return rois


# =====================
# 保存
# =====================
def save_rois(rois, output_dir):
    timestamp = int(time.time() * 1000)

    for name, roi in rois.items():
        filename = os.path.join(output_dir, name, f"{name}_{timestamp}.png")
        cv2.imwrite(filename, roi)


# =====================
# 工具函数
# =====================
def list_source_images(source_dir):
    if not os.path.exists(source_dir):
        raise FileNotFoundError(f"sources 目录不存在: {source_dir}")

    return sorted(
        f
        for f in os.listdir(source_dir)
        if os.path.splitext(f.lower())[1] in SUPPORTED_IMAGE_EXTENSIONS
    )


def get_template_name_from_filename(filename):
    return os.path.splitext(filename)[0]


def load_roi_config_from_yaml(yaml_path):
    data = load_yaml_file(yaml_path)
    if not isinstance(data, dict):
        raise ValueError(f"YAML 内容格式不正确: {yaml_path}")

    roi_config = {}
    for key, coords in data.items():
        if not isinstance(coords, list) or len(coords) != 4:
            print(f"跳过 ROI 配置 {key}, 期望 4 个坐标值, 实际: {coords}")
            continue
        try:
            roi_config[key] = tuple(float(value) for value in coords)
        except (TypeError, ValueError):
            print(f"跳过 ROI 配置 {key}, 无效坐标值: {coords}")

    return roi_config


def build_output_dir(template_name):
    return os.path.join(OUTPUT_ROOT, template_name)


def process_screenshot(screenshot_path, template_name):
    config_path = os.path.join(CONFIGS_DIR, f"{template_name}.yaml")
    if not os.path.exists(config_path):
        print(f"跳过 {template_name}: 未找到匹配的 YAML 文件 {config_path}")
        return

    roi_config = load_roi_config_from_yaml(config_path)
    if not roi_config:
        print(f"跳过 {template_name}: 未加载到有效 ROI 配置")
        return

    screenshot = cv2.imread(screenshot_path)
    if screenshot is None:
        print(f"无法读取截图文件: {screenshot_path}")
        return

    output_dir = build_output_dir(template_name)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    init_dirs(roi_config, output_dir)
    rois = crop_rois(screenshot, roi_config)
    if not rois:
        print(f"{template_name} 未生成任何 ROI 模板，可能 ROI 配置无效")
        return

    save_rois(rois, output_dir)
    print(f"🎉 {template_name} 模板已生成到: {output_dir}")


# =====================
# 主流程
# =====================
def main():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    try:
        screenshots = list_source_images(SOURCES_DIR)
    except FileNotFoundError as e:
        print(e)
        return

    if not screenshots:
        print("未找到 sources 目录中的截图文件，请检查 sources 下是否包含 png/jpg 文件")
        return

    for screenshot_file in screenshots:
        screenshot_path = os.path.join(SOURCES_DIR, screenshot_file)
        template_name = get_template_name_from_filename(screenshot_file)
        process_screenshot(screenshot_path, template_name)

    print("🎉 全部模板处理完成")


if __name__ == "__main__":
    main()
