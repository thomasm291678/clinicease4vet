"""科大讯飞 语音转写 (LFASR) 服务"""

import hashlib
import hmac
import base64
import time
import json
import requests
from config import Config

ASR_HOST = "https://raasr.xfyun.cn/api"
APP_ID = Config.IFLYTEK_APP_ID or ""
SECRET_KEY = Config.IFLYTEK_API_SECRET or ""
FILE_PIECE_SIZE = 10 * 1024 * 1024  # 10MB per slice


class SliceIdGenerator:
    def __init__(self):
        self.__ch = "aaaaaaaaa`"

    def get_next_slice_id(self):
        ch = self.__ch
        j = len(ch) - 1
        while j >= 0:
            cj = ch[j]
            if cj != "z":
                ch = ch[:j] + chr(ord(cj) + 1) + ch[j + 1 :]
                break
            else:
                ch = ch[:j] + "a" + ch[j + 1 :]
                j = j - 1
        self.__ch = ch
        return self.__ch


def _generate_signa(app_id, ts, secret_key):
    """生成讯飞 API 签名"""
    base_string = app_id + ts
    md5_hash = hashlib.md5(base_string.encode()).hexdigest()
    hmac_sign = hmac.new(
        secret_key.encode(), md5_hash.encode(), hashlib.sha1
    ).digest()
    return base64.b64encode(hmac_sign).decode()


def _post(url, data=None, files=None):
    ts = str(int(time.time()))
    signa = _generate_signa(APP_ID, ts, SECRET_KEY)

    if files:
        headers = {}
        form_data = {
            "app_id": APP_ID,
            "signa": signa,
            "ts": ts,
        }
        form_data.update(data or {})
        resp = requests.post(url, data=form_data, files=files, timeout=30)
    else:
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        form_data = {
            "app_id": APP_ID,
            "signa": signa,
            "ts": ts,
        }
        form_data.update(data or {})
        resp = requests.post(url, data=form_data, headers=headers, timeout=30)

    return resp.json()


def transcribe_audio(audio_data, file_name="recording.wav"):
    """
    上传音频并获取转写结果。
    audio_data: bytes 音频文件内容
    file_name: str 文件名（带后缀，如 recording.wav）
    返回: {"text": "...", "confidence": 0.0}
    """
    file_len = len(audio_data)

    # 计算分片数量
    slice_num = max(1, (file_len + FILE_PIECE_SIZE - 1) // FILE_PIECE_SIZE)

    # 1. 预处理
    prepare_result = _post(
        f"{ASR_HOST}/prepare",
        data={
            "file_len": str(file_len),
            "file_name": file_name,
            "slice_num": str(slice_num),
            "has_participle": "false",
            "eng_vad_margin": "0",
        },
    )

    if prepare_result.get("ok") != 0:
        err = prepare_result.get("failed", "预处理失败")
        return {"text": "", "confidence": 0, "error": err}

    task_id = prepare_result.get("data", "")
    if not task_id:
        return {"text": "", "confidence": 0, "error": "未获取到任务ID"}

    # 2. 分片上传
    sig = SliceIdGenerator()

    for i in range(slice_num):
        start = i * FILE_PIECE_SIZE
        end = min(start + FILE_PIECE_SIZE, file_len)
        piece = audio_data[start:end]
        slice_id = sig.get_next_slice_id()

        upload_result = _post(
            f"{ASR_HOST}/upload",
            data={
                "task_id": task_id,
                "slice_id": slice_id,
            },
            files={"content": (file_name, piece, "application/octet-stream")},
        )

        if upload_result.get("ok") != 0:
            return {
                "text": "",
                "confidence": 0,
                "error": upload_result.get("failed", "上传失败"),
            }

    # 3. 合并
    merge_result = _post(f"{ASR_HOST}/merge", data={"task_id": task_id})

    if merge_result.get("ok") != 0:
        return {
            "text": "",
            "confidence": 0,
            "error": merge_result.get("failed", "合并失败"),
        }

    # 4. 轮询进度
    max_polls = 60  # 最多轮询60次
    poll_interval = 2  # 每2秒

    for _ in range(max_polls):
        time.sleep(poll_interval)

        progress_result = _post(
            f"{ASR_HOST}/getProgress", data={"task_id": task_id}
        )

        if progress_result.get("ok") != 0:
            continue

        try:
            status_data = json.loads(progress_result.get("data", "{}"))
        except (json.JSONDecodeError, TypeError):
            continue

        status = status_data.get("status", -1)
        if status == 9:
            break
        elif status < 0:
            return {
                "text": "",
                "confidence": 0,
                "error": status_data.get("desc", "转写失败"),
            }
    else:
        return {"text": "", "confidence": 0, "error": "转写超时"}

    # 5. 获取结果
    result_response = _post(f"{ASR_HOST}/getResult", data={"task_id": task_id})

    if result_response.get("ok") != 0:
        return {
            "text": "",
            "confidence": 0,
            "error": result_response.get("failed", "获取结果失败"),
        }

    try:
        result_data = json.loads(result_response.get("data", "[]"))
    except (json.JSONDecodeError, TypeError):
        return {"text": "", "confidence": 0, "error": "解析结果失败"}

    if not result_data:
        return {"text": "", "confidence": 0, "error": "转写结果为空"}

    sentences = []
    total_confidence = 0
    for seg in result_data:
        sentences.append(seg.get("onebest", ""))
        total_confidence += seg.get("wc", 0) if isinstance(seg.get("wc"), (int, float)) else 0

    full_text = "".join(sentences)
    avg_confidence = round(total_confidence / len(result_data) * 100, 1) if result_data else 0

    return {"text": full_text, "confidence": avg_confidence}
