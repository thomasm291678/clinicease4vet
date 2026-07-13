"""语音转写服务测试 — 科大讯飞 + 降级策略"""

import pytest
import os
from unittest.mock import MagicMock, patch, Mock
from services.speech_service import IflytekTranscriber


class TestIflytekTranscriber:
    """科大讯飞转写器测试"""

    def test_not_configured_by_default(self):
        """默认未配置"""
        t = IflytekTranscriber()
        # 如果没有环境变量，应该未配置
        if not os.getenv("IFLYTEK_APP_ID"):
            assert not t.is_configured()

    def test_empty_audio_returns_empty(self):
        t = IflytekTranscriber()
        assert t.transcribe(b"") == ""

    def test_file_not_found(self):
        t = IflytekTranscriber()
        result = t.transcribe_file("/nonexistent/file.wav")
        assert result == ""

    def test_transcribe_without_config(self):
        """未配置时回退到本地模式"""
        t = IflytekTranscriber()
        with patch.object(t, "_transcribe_local", return_value="测试文本"):
            result = t.transcribe(b"fake_audio_data")
            assert result == "测试文本"

    def test_transcribe_with_config(self):
        """已配置时使用 WebSocket"""
        t = IflytekTranscriber()
        t.app_id = "test_id"
        t.api_key = "test_key"
        t.api_secret = "test_secret"

        with patch.object(t, "_transcribe_rtasr", return_value="讯飞识别结果"):
            result = t.transcribe(b"audio_data")
            assert result == "讯飞识别结果"

    def test_local_transcribe(self):
        """本地转写测试"""
        t = IflytekTranscriber()
        # 空数据或无 speech_recognition 时应返回回退提示
        result = t._transcribe_local(b"")
        assert isinstance(result, str)

    def test_is_configured_detection(self):
        t = IflytekTranscriber()
        # 默认应该基于环境变量
        default_state = t.is_configured()

        # 手动设置
        t.app_id = "test"
        t.api_key = "key"
        t.api_secret = "secret"
        assert t.is_configured()

        t.api_key = ""
        assert not t.is_configured()


class TestSpeechServiceIntegration:
    """语音服务集成测试 (Flask test client)"""

    @pytest.fixture
    def app(self):
        from app import create_app
        with patch("app.init_database"):
            test_app = create_app()
            test_app.config["TESTING"] = True
            yield test_app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @pytest.fixture
    def headers(self):
        from auth.auth import create_token
        token = create_token("testuser", "vet")
        return {"Authorization": f"Bearer {token}"}

    def test_transcribe_no_file(self, client, headers):
        resp = client.post("/api/ai/transcribe", headers=headers)
        assert resp.status_code == 400

    def test_speech_config(self, client, headers):
        resp = client.get("/api/ai/speech-config", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "iflytek_configured" in data
        assert "engines_available" in data

    def test_transcribe_with_empty_file(self, client, headers):
        """上传空音频文件"""
        import io
        data = {"audio": (io.BytesIO(b""), "empty.wav")}
        resp = client.post(
            "/api/ai/transcribe",
            data=data,
            content_type="multipart/form-data",
            headers=headers,
        )
        assert resp.status_code == 400  # 空文件被拒绝

    def test_transcribe_no_auth(self, client):
        resp = client.post("/api/ai/transcribe")
        assert resp.status_code == 401
