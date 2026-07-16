"""应用配置"""

import os


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # MySQL 配置
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "max_hospitals")

    # JWT 配置
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clinicease-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = 3600

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
    # RAG 知识库配置
    # ========================
    RAG_DATA_DIR = os.path.join(BASE_DIR, "data", "knowledge_base_en")
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    RAG_MODEL_CACHE_DIR = os.getenv("RAG_MODEL_CACHE_DIR", os.path.join(BASE_DIR, "data", "knowledge_base", "models"))
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.35"))

    # ========================
    # FunASR 离线语音识别 (阿里巴巴达摩院 Paraformer)
    # ========================
    FUNASR_MODEL_CACHE_DIR = os.getenv("FUNASR_MODEL_CACHE_DIR", os.path.join(BASE_DIR, "data", "funasr_models"))

    # ========================
    # Tavily 联网搜索 (增强 RAG)
    # ========================
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
