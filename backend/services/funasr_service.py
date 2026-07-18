"""FunASR 离线语音识别服务 + 后端统一音频处理

流程: 前端上传任意格式音频 → ffmpeg 降采样 16kHz 单声道 → FunASR 转文字 → DeepSeek 解析

依赖:
  - funasr_onnx (阿里巴巴 Paraformer + VAD + 标点)
  - ffmpeg (音频格式转换/降采样)
  - DeepSeek (AI 解析文本为结构化数据)
"""

import os
import time
import tempfile
import subprocess
import logging

logger = logging.getLogger(__name__)

_funasr_server = None
_models_available = None

# 目标音频参数：16kHz 采样率，单声道，16bit PCM —— FunASR 最佳输入
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH = 2  # 16bit


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


def _convert_to_wav16k(raw_bytes: bytes, input_ext: str = ".webm") -> bytes:
    """用 ffmpeg 将任意音频格式转为 16kHz 16bit 单声道 WAV"""
    import shutil

    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg 不可用，将使用原始音频数据（可能识别的 jing度下降）")
        return raw_bytes

    fd_in, tmp_in = tempfile.mkstemp(suffix=input_ext if input_ext.startswith(".") else ".webm")
    os.close(fd_in)
    fd_out, tmp_out = tempfile.mkstemp(suffix=".wav")
    os.close(fd_out)

    try:
        with open(tmp_in, "wb") as f:
            f.write(raw_bytes)

        cmd = [
            "ffmpeg",
            "-y", "-i", tmp_in,
            "-ar", str(TARGET_SAMPLE_RATE),
            "-ac", str(TARGET_CHANNELS),
            "-sample_fmt", "s16",
            "-f", "wav",
            "-loglevel", "error",
            tmp_out,
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            logger.warning("ffmpeg 转换失败: %s，使用原始数据", proc.stderr.strip())
            return raw_bytes

        with open(tmp_out, "rb") as f:
            return f.read()

    except Exception as e:
        logger.warning("音频转换异常: %s，使用原始数据", e)
        return raw_bytes
    finally:
        for p in (tmp_in, tmp_out):
            try:
                os.remove(p)
            except OSError:
                pass


def transcribe_audio(audio_data: bytes, file_name: str = "recording.webm") -> dict:
    """将音频转为文字（后端全链路：格式转换 → 16kHz 降采样 → FunASR 转写）

    Args:
        audio_data: 原始音频字节（支持 webm/mp3/wav/m4a/ogg 等任意格式）
        file_name: 文件名（用于推断输入格式）

    Returns:
        {"text": "...", "confidence": 0.85, "elapsed": 2.3, "engine": "funasr"}
    """
    # 1. 推断输入格式
    ext = os.path.splitext(file_name)[1].lower()
    if not ext:
        ext = ".webm"

    # 2. ffmpeg 转为 16kHz WAV
    start = time.time()
    wav_data = _convert_to_wav16k(audio_data, ext)

    # 3. 写入临时 WAV 文件给 FunASR
    fd, tmp_wav = tempfile.mkstemp(suffix=".wav", prefix="funasr_")
    os.close(fd)

    try:
        with open(tmp_wav, "wb") as f:
            f.write(wav_data)

        # 4. FunASR 转写
        server = _get_funasr_server()
        result = server.transcribe_audio(
            tmp_wav,
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
            os.remove(tmp_wav)
        except OSError:
            pass


def transcribe_and_parse(audio_data: bytes, file_name: str = "recording.webm") -> dict:
    """全链路处理：音频 → 转文字 → DeepSeek AI 解析为结构化数据

    这是前端语音工作台「录音 → 一键录入」的统一入口。
    后端完成所有重活，前端只需上传音频文件。

    Args:
        audio_data: 原始音频字节
        file_name: 文件名

    Returns:
        {
            "text": "转写的文字",
            "pet_form": { name, species, breed, ... },
            "medical_form": { diagnosis, treatment, ... },
            "vaccine_form": { vaccine_name, ... },
            "transcribe_elapsed": 1.2,
            "parse_elapsed": 3.5,
        }
    """
    from services.deepseek_service import get_deepseek

    t0 = time.time()

    # 1. 音频 → 文字
    transcribe_result = transcribe_audio(audio_data, file_name)
    text = transcribe_result.get("text", "")
    transcribe_elapsed = transcribe_result.get("elapsed", 0)

    if not text:
        return {
            "text": "",
            "error": transcribe_result.get("error", "语音转写失败"),
            "transcribe_elapsed": transcribe_elapsed,
        }

    # 2. 文字 → AI 解析
    ds = get_deepseek()
    parse_t0 = time.time()

    if not ds.is_configured():
        return {
            "text": text,
            "error": "DeepSeek API 未配置",
            "transcribe_elapsed": transcribe_elapsed,
        }

    auto_fill_result = ds.auto_fill(text)
    parse_elapsed = round(time.time() - parse_t0, 2)

    if "error" in auto_fill_result:
        return {
            "text": text,
            "error": auto_fill_result["error"],
            "transcribe_elapsed": transcribe_elapsed,
            "parse_elapsed": parse_elapsed,
        }

    # 3. 组装返回
    result = {
        "text": text,
        "transcribe_engine": "funasr",
        "parse_engine": "deepseek",
        "transcribe_elapsed": transcribe_elapsed,
        "parse_elapsed": parse_elapsed,
        "total_elapsed": round(time.time() - t0, 2),
    }

    fd = auto_fill_result.get("form_data", {})
    if fd:
        result["medical_form"] = {
            "diagnosis": fd.get("diagnosis", ""),
            "treatment": fd.get("treatment", ""),
            "symptoms": fd.get("symptoms", ""),
            "notes": fd.get("notes", ""),
            "visit_date": fd.get("visit_date", ""),
            "follow_up_date": fd.get("follow_up_date") or None,
            "fee_charged": fd.get("fee_charged", 0),
            "vet_name": fd.get("vet_name", ""),
        }

    vd = auto_fill_result.get("vaccine_data")
    if vd:
        result["vaccine_form"] = {
            "vaccine_name": vd.get("vaccine_name", ""),
            "administered_date": vd.get("administered_date", ""),
            "next_due_date": vd.get("next_due_date") or None,
            "vet_name": vd.get("vet_name", ""),
        }

    # 额外解析宠物信息
    parsed_full = ds.parse_medical_text(text)
    if "error" not in parsed_full:
        pi = parsed_full.get("pet_info", {})
        if pi and pi.get("pet_name"):
            result["pet_form"] = {
                "name": pi.get("pet_name", ""),
                "species": pi.get("species", ""),
                "breed": pi.get("breed", ""),
                "gender": pi.get("gender", ""),
                "owner_name": pi.get("owner_name", ""),
                "owner_contact": pi.get("owner_contact", ""),
            }

    result["summary"] = auto_fill_result.get("summary", "")
    result["confidence"] = auto_fill_result.get("confidence", 0)

    return result


def cleanup():
    global _funasr_server, _models_available
    if _funasr_server:
        _funasr_server.cleanup()
        _funasr_server = None
    _models_available = None
