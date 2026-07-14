"""应用配置"""

import os


class Config:
    # MySQL 配置
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "max_hospitals")

    # JWT 配置
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clinicease-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 小时

    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # ========================
    # DeepSeek AI 配置
    # ========================
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192"))
    DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))

    # ========================
    # 科大讯飞 实时语音转写 (RTASR) 配置
    # 文档: https://www.xfyun.cn/doc/asr/rtasr/API.html
    # ========================
    IFLYTEK_APP_ID = os.getenv("IFLYTEK_APP_ID", "")
    IFLYTEK_API_KEY = os.getenv("IFLYTEK_API_KEY", "")
    IFLYTEK_API_SECRET = os.getenv("IFLYTEK_API_SECRET", "")
    # 实时语音转写 WebSocket 端点
    IFLYTEK_RTASR_HOST = "rtasr.xfyun.cn"
    IFLYTEK_RTASR_PATH = "/v1/ws"
    IFLYTEK_RTASR_URL = f"wss://{IFLYTEK_RTASR_HOST}{IFLYTEK_RTASR_PATH}"
