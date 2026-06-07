import os
import json
import glob
import time
import random
import threading
import urllib.request
import urllib.error
import ctypes
from datetime import datetime


class UploadManager:
    def __init__(self, upload_url, token, cache_dir=None, retry_delay=5, reset_count=True):
        self.upload_url = upload_url
        self.token = token
        self.retry_delay = retry_delay
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '.upload_cache')
        self.status_file = os.path.join(self.cache_dir, 'status.json')
        self.file_suffix = '.cache'
        self.legacy_suffix = '.png'
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.current_file = None
        self.last_error = None
        self.uploaded_count = 0
        self.failed_count = 0
        self.retry_count = 0
        self._ensure_cache_dir()
        self._migrate_legacy_cache_files()
        self._load_status()
        # reset_count=True 表示这是一次新的启动，仅重置上传计数，保留失败计数以供实时展示
        if reset_count:
            self.uploaded_count = 0

    def _ensure_cache_dir(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self._set_hidden(self.cache_dir)

    def _set_hidden(self, path):
        if os.name == 'nt':
            try:
                ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)
            except Exception:
                pass

    def _migrate_legacy_cache_files(self):
        legacy_pattern = os.path.join(self.cache_dir, f'*{self.legacy_suffix}')
        for old_path in sorted(glob.glob(legacy_pattern)):
            try:
                with open(old_path, 'rb') as f:
                    old_data = f.read()
                new_path = old_path[:-len(self.legacy_suffix)] + self.file_suffix
                with open(new_path, 'wb') as f:
                    f.write(self._encode_data(old_data))
                self._set_hidden(new_path)
                os.remove(old_path)
            except Exception:
                pass

    def _load_status(self):
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.uploaded_count = data.get('uploaded_count', 0)
                self.failed_count = data.get('failed_count', 0)
                self.retry_count = data.get('retry_count', 0)
                self.last_error = data.get('last_error')
                self.current_file = data.get('current_file')
            except Exception:
                self._save_status()
        else:
            self._save_status()

    def _save_status(self):
        payload = {
            'uploaded_count': self.uploaded_count,
            'pending_count': self.pending_count,
            'failed_count': self.failed_count,
            'retry_count': self.retry_count,
            'current_file': self.current_file,
            'last_error': self.last_error,
            'updated_at': datetime.now().isoformat()
        }
        temp_file = self.status_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, self.status_file)
        if os.name == 'nt':
            try:
                ctypes.windll.kernel32.SetFileAttributesW(self.status_file, 0x02)
            except Exception:
                pass

    @property
    def pending_count(self):
        cache_files = glob.glob(os.path.join(self.cache_dir, f'*{self.file_suffix}'))
        legacy_files = glob.glob(os.path.join(self.cache_dir, f'*{self.legacy_suffix}'))
        return len(cache_files) + len(legacy_files)

    def get_status(self):
        with self.lock:
            return {
                'uploaded_count': self.uploaded_count,
                'pending_count': self.pending_count,
                'failed_count': self.failed_count,
                'retry_count': self.retry_count,
                'current_file': self.current_file,
                'last_error': self.last_error,
                'cache_dir': self.cache_dir,
                'updated_at': datetime.now().isoformat()
            }

    def pending_files(self):
        """返回待上传的文件列表"""
        cache_files = glob.glob(os.path.join(self.cache_dir, f'*{self.file_suffix}'))
        legacy_files = glob.glob(os.path.join(self.cache_dir, f'*{self.legacy_suffix}'))
        return sorted(cache_files + legacy_files)

    def enqueue(self, png_bytes, page_tag=None):
        filename = f'upload_{page_tag or "unknown"}_{int(time.time() * 1000)}_{random.randint(1000,9999)}{self.file_suffix}'
        file_path = os.path.join(self.cache_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(self._encode_data(png_bytes))
        self._set_hidden(file_path)
        with self.lock:
            self.current_file = None
            self.last_error = None
            self._save_status()
        return file_path

    def start(self):
        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()

    def stop(self):
        self.stop_event.set()

    def _worker(self):
        while not self.stop_event.is_set():
            pending_files = self.pending_files()
            if not pending_files:
                time.sleep(1)
                continue
            for path in pending_files:
                if self.stop_event.is_set():
                    break
                self.current_file = os.path.basename(path)
                self._save_status()
                try:
                    self._upload_file(path)
                    self.uploaded_count += 1
                    self.failed_count = 0
                    self.last_error = None
                    self.current_file = None
                    self._save_status()
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as ex:
                    self.failed_count += 1
                    self.last_error = str(ex)
                    self._save_status()
                    time.sleep(self.retry_delay)
                    continue
            time.sleep(0.5)

    def _upload_file(self, file_path):
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        if file_path.lower().endswith(self.file_suffix):
            data = raw_data
        else:
            data = self._encode_data(raw_data)
        url = f"{self.upload_url}?token={self.token}"
        headers = {'Content-Type': 'application/octet-stream'}
        request = urllib.request.Request(url, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status_code = response.getcode()
                if status_code < 200 or status_code >= 300:
                    raise RuntimeError(f'HTTP {status_code}')
                print(f"status_code: {status_code}\nResponse: {response.read().decode()}")
                print(f"Uploaded {os.path.basename(file_path)} successfully.")
                print(f"Status updated: uploaded_count={self.uploaded_count + 1}, failed_count={self.failed_count}")
                print(f"Pending files: {self.pending_count - 1}")
                print(f"Current file: {self.current_file}, Last error: {self.last_error}")
                print(f"Status file path: {self.status_file}, Exists: {os.path.exists(self.status_file)}")
                print(f"Cache directory: {self.cache_dir}, Files: {os.listdir(self.cache_dir)}")
                
        except urllib.error.HTTPError as ex:
            raise RuntimeError(f'HTTPError {ex.code}: {ex.reason}')
        except urllib.error.URLError as ex:
            raise RuntimeError(f'URLError: {ex.reason}')
        except Exception as ex:
            raise RuntimeError(str(ex))

    def _encode_data(self, data):
        key = b'opencv_v23_secure_cache_key_2026'
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    def _decode_data(self, data):
        return self._encode_data(data)
