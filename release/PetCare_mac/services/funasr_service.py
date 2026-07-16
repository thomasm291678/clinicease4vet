"""FunASR 离线语音识别服务

依赖: funasr_onnx (阿里巴巴达摩院 FunASR ONNX 推理引擎)
模型: Paraformer + VAD + 标点恢复 (首次运行时自动下载 ~500MB)

基于 VocoType 开源项目的 FunASR 引擎:
  https://github.com/233stone/vocotype-cli
"""

import os
import time
import tempfile
import wave
import logging

logger = logging.getLogger(__name__)

_funasr_server = None
_models_available = None


def _get_funasr_server():
    global _funasr_server
    if _funasr_server is None:
        from services.funasr.funasr_server import FunASRServer

        _funasr_server = FunASRServer()
        init_result = _funasr_server.initialize()
        if not init_result.get("success"):
            error_msg = init_result.get("error", "FunASR 初始化失败")
            logger.error("FunASR 初始化失败: %s", error_msg)
            raise RuntimeError(error_msg)
        logger.info("FunASR 离线语音引擎初始化成功")
    return _funasr_server


def is_available() -> bool:
    global _models_available
    if _models_available is not None:
        return _models_available
    try:
        _get_funasr_server()
        _models_available = True
    except Exception:
        _models_available = False
    return _models_available


def transcribe_audio(audio_data: bytes, file_name: str = "recording.wav") -> dict:
    """FunASR 离线语音识别 — 与讯飞接口完全一致

    Args:
        audio_data: bytes 音频文件内容
        file_name: 文件名（用于推断后缀）

    Returns:
        {"text": "...", "confidence": 0.0}
    """
    fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="funasr_")
    os.close(fd)
    try:
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_data)

        server = _get_funasr_server()
        start = time.time()
        result = server.transcribe_audio(
            tmp_path,
            options={"use_vad": True, "use_punc": True, "language": "zh"},
        )
        elapsed = round(time.time() - start, 2)

        if result.get("success"):
            return {
                "text": result.get("text", "").strip(),
                "raw_text": result.get("raw_text", ""),
                "confidence": round(result.get("confidence", 0), 3),
                "duration": result.get("duration", 0),
                "engine": "funasr",
                "elapsed": elapsed,
            }
        else:
            return {
                "text": "",
                "confidence": 0,
                "error": result.get("error", "FunASR 转写失败"),
                "engine": "funasr",
                "elapsed": elapsed,
            }
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def cleanup():
    global _funasr_server, _models_available
    if _funasr_server:
        _funasr_server.cleanup()
        _funasr_server = None
    _models_available = None
