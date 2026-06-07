# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import requests

app = FastAPI()

# 认证 token
EXPECTED_TOKEN = "cbf123456"
SECURE_CACHE_KEY = b'opencv_v23_secure_cache_key_2026'

# 保存目录：同目录下的 images 文件夹
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "images"


def _decode_data(data: bytes) -> bytes:
    return bytes([b ^ SECURE_CACHE_KEY[i % len(SECURE_CACHE_KEY)] for i, b in enumerate(data)])


@app.post("/upload")
async def upload_image(request: Request, token: str = ""):
    # 1) 鉴权
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    # 2) 检查 content-type
    content_type = request.headers.get("content-type", "")
    if "application/octet-stream" not in content_type.lower() and "image/png" not in content_type.lower():
        raise HTTPException(status_code=415, detail="content-type must be application/octet-stream or image/png")

    # 3) 读取原始请求字节
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty body")

    # 4) 解密缓存数据
    if "application/octet-stream" in content_type.lower():
        try:
            body = _decode_data(body)
        except Exception:
            raise HTTPException(status_code=400, detail="failed to decode cache payload")

    # 5) 验证 PNG 头部并保存文件
    if not body.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="decoded payload is not a valid PNG image")

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.png"
    file_path = SAVE_DIR / filename

    with open(file_path, "wb") as f:
        f.write(body)

    return JSONResponse(
        {
            "success": True,
            "message": "upload ok",
            "filename": filename,
            "file_path": str(file_path),
            "size": len(body)
        }
    )

#
# "filename": filename,
# "file_path": str(file_path),




if __name__ == "__main__":
    # 先启动服务：
    #   python app.py
    #
    # 然后另开一个窗口执行测试：
    #   python app.py test
    # import sys
    #
    # if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
    #     test_upload()
    # else:
    uvicorn.run(app, host="0.0.0.0", port=8001)