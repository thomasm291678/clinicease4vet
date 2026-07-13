"""
科大讯飞 实时语音转写 (RTASR) 服务

API: 实时语音转写 WebSocket
  端点: wss://rtasr.xfyun.cn/v1/ws?{appid}&{ts}&{signa}
  认证: MD5(appid + timestamp + secret_key) → base64
  协议: 首帧 JSON → 音频二进制帧 → 尾帧 JSON → 接收结果
  
音频格式: 16kHz, 16bit, mono, PCM raw
支持语种: zh_cn (中文普通话)

使用方式:
  1. 设置环境变量: IFLYTEK_APP_ID / IFLYTEK_API_KEY / IFLYTEK_API_SECRET
  2. 如未设置，自动回退到本地 Google STT 或手动输入
"""

import hashlib
import base64
import json
import time
import threading
from config import Config


class IflytekTranscriber:
    """
    科大讯飞 实时语音转写 (RTASR) 客户端

    协议流程:
      1. 构建签名 URL: wss://rtasr.xfyun.cn/v1/ws?appid=xxx&ts=xxx&signa=xxx
      2. WebSocket 连接
      3. 发送开始命令 (JSON): {"cmd": "spt", "audioFormat": "audio/L16;rate=16000"}
      4. 循环发送音频帧 (binary, 1280 bytes/frame)
      5. 接收服务端返回的转写结果 (JSON text)
      6. 发送结束命令 (JSON): {"cmd": "spt_end"}
      7. 接收最终结果，断开连接
    """

    FRAME_SIZE = 1280  # 每帧音频字节数

    def __init__(self):
        self.app_id = Config.IFLYTEK_APP_ID
        self.api_key = Config.IFLYTEK_API_KEY
        self.api_secret = Config.IFLYTEK_API_SECRET
        self._result_text = ""
        self._error = None
        self._done = threading.Event()

    # ---------- 公开 API ----------

    def is_configured(self) -> bool:
        return bool(self.app_id and self.api_key and self.api_secret)

    def transcribe(self, audio_data: bytes, language: str = "zh_cn") -> str:
        """
        转写音频数据为文本

        Args:
            audio_data: 原始 PCM 音频 (16kHz, 16bit, mono)
            language: 语种

        Returns:
            转写后的文本
        """
        if not audio_data:
            return ""

        if self.is_configured():
            return self._transcribe_rtasr(audio_data, language)
        else:
            return self._transcribe_local(audio_data)

    def transcribe_file(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                return self.transcribe(f.read())
        except FileNotFoundError:
            return ""
        except Exception as e:
            return f"[错误] 读取失败: {e}"

    # ---------- RTASR WebSocket ----------

    def _transcribe_rtasr(self, audio_data: bytes, language: str) -> str:
        self._result_text = ""
        self._error = None
        self._done.clear()

        ws_url = self._build_rtasr_url()
        if not ws_url:
            return "[错误] 无法生成签名"

        try:
            import websocket
        except ImportError:
            return "[错误] 请安装: pip install websocket-client"

        def on_open(ws):
            # 1. 发送开始命令
            start_cmd = json.dumps({
                "cmd": "spt",
                "audioFormat": "audio/L16;rate=16000",
                "language": language,
            })
            ws.send(start_cmd)

            # 2. 发送音频数据 (二进制帧)
            offset = 0
            while offset < len(audio_data):
                chunk = audio_data[offset:offset + self.FRAME_SIZE]
                offset += self.FRAME_SIZE
                ws.send(chunk, opcode=0x2)  # 0x2 = binary frame

            # 3. 发送结束命令
            ws.send(json.dumps({"cmd": "spt_end"}))

        def on_message(ws, message):
            # RTASR 返回的都是 JSON 文本帧
            try:
                msg = json.loads(message)
                action = msg.get("action", "")
                code = msg.get("code", 0)

                if code != 0:
                    self._error = msg.get("desc", msg.get("message", f"错误码 {code}"))
                    ws.close()
                    return

                if action == "result":
                    data = msg.get("data", "")
                    if data:
                        self._result_text += data

                elif action == "error":
                    self._error = msg.get("desc", "未知错误")
                    ws.close()

                elif action == "status":
                    # 状态更新，可以忽略
                    pass

            except json.JSONDecodeError:
                pass

        def on_error(ws, error):
            self._error = str(error)

        def on_close(ws, close_code, close_msg):
            self._done.set()

        try:
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )

            thread = threading.Thread(target=ws.run_forever)
            thread.daemon = True
            thread.start()

            finished = self._done.wait(timeout=30)
            ws.close()

            if not finished:
                return "[错误] 转写超时"

            if self._error:
                return f"[错误] {self._error}"

            result = self._result_text.strip()
            if not result:
                return "[提示] 未识别到语音内容"

            return self._restore_punctuation(result)

        except Exception as e:
            return f"[错误] 连接讯飞失败: {e}"

    def _build_rtasr_url(self) -> str:
        """构建 RTASR 签名 URL"""
        ts = str(int(time.time()))
        # signa = base64(MD5(appid + ts + secret_key))
        raw = self.app_id + ts + self.api_secret
        signa = base64.b64encode(
            hashlib.md5(raw.encode("utf-8")).digest()
        ).decode("utf-8")

        url = (
            f"wss://{Config.IFLYTEK_RTASR_HOST}{Config.IFLYTEK_RTASR_PATH}"
            f"?appid={self.app_id}&ts={ts}&signa={signa}"
        )
        return url

    # ---------- 离线回退 ----------

    def _transcribe_local(self, audio_data: bytes) -> str:
        try:
            import speech_recognition as sr
            import io
            import wave

            r = sr.Recognizer()
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            buf.seek(0)

            with sr.AudioFile(buf) as source:
                audio = r.record(source)

            return r.recognize_google(audio, language="zh-CN")

        except ImportError:
            return "[回退] Google STT 不可用，请手动输入"
        except Exception as e:
            return f"[回退] 语音识别失败: {e}，请手动输入"

    @staticmethod
    def _restore_punctuation(text: str) -> str:
        if not text:
            return text
        text = text.replace("  ", " ")
        if text[-1] not in "。！？，、.!?,":
            text += "。"
        return text


def record_and_transcribe(duration: int = 10) -> str:
    """客户端录音 + 转写"""
    transcriber = IflytekTranscriber()
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=duration)
        pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
        if transcriber.is_configured():
            return transcriber.transcribe(pcm)
        return r.recognize_google(audio, language="zh-CN")
    except ImportError:
        return input("\n[回退] 语音库未安装，请直接输入: ").strip()
    except OSError:
        return input("\n[回退] 未检测到麦克风，请直接输入: ").strip()
    except Exception as e:
        return input(f"\n[回退] 录音失败 ({e})，请直接输入: ").strip()
