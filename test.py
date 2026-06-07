from pathlib import Path
import requests

# 认证 token
EXPECTED_TOKEN = "cbf123456"

# 保存目录：同目录下的 images 文件夹
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "images"

def test_upload():
    """
    测试请求：读取同目录下 screenshot_basic_info.png 并上传到本地接口
    """
    img_path = BASE_DIR /'pngs'/ "screenshot_20260515_155925_168629.png"
    if not img_path.exists():
        print(f"测试图片不存在：{img_path}")
        return

    url = "http://127.0.0.1:8001/upload"
    params = {"token": EXPECTED_TOKEN}

    with open(img_path, "rb") as f:
        data = f.read()

    headers = {
        "Content-Type": "image/png"
    }

    resp = requests.post(url, params=params, data=data, headers=headers, timeout=30)
    print("status:", resp.status_code)
    print("result:", resp.text)

if __name__ == "__main__":
    test_upload()
    # img_path = BASE_DIR /'pngs'/ "screenshot_20260515_155925_168629.png"
    # print(f"测试图片路径：{img_path}, 是否存在：{img_path.exists()}")



