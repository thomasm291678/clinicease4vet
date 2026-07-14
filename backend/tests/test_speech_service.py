"""语音转写服务测试 — 科大讯飞"""

import pytest
import os
from unittest.mock import MagicMock, patch, Mock
from services.speech_service import IflytekTranscriber


class TestIflytekTranscriber:

    def test_not_configured_by_default(self):
        t = IflytekTranscriber()
        if not os.getenv("IFLYTEK_APP_ID"):
            assert not t.is_configured()

    def test_empty_audio_returns_empty(self):
        t = IflytekTranscriber()
        assert t.transcribe(b"") == ""

    def test_file_not_found(self):
        t = IflytekTranscriber()
        result = t.transcribe_file("/nonexistent/file.wav")
        assert result == ""

    def test_transcribe_with_config(self):
        t = IflytekTranscriber()
        t.app_id = "test_id"
        t.api_key = "test_key"
        t.api_secret = "test_secret"

        with patch.object(t, "_transcribe_rtasr", return_value="讯飞识别结果"):
            result = t.transcribe(b"audio_data")
            assert result == "讯飞识别结果"

    def test_is_configured_detection(self):
        t = IflytekTranscriber()
        default_state = t.is_configured()

        t.app_id = "test"
        t.api_key = "key"
        t.api_secret = "secret"
        assert t.is_configured()

        t.api_key = ""
        assert not t.is_configured()


class TestSpeechServiceIntegration:

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

    def test_engine_status(self, client, headers):
        resp = client.get("/api/ai/engine-status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "iflytek_configured" in data

    def test_transcribe_no_auth(self, client):
        resp = client.post("/api/ai/transcribe")
        assert resp.status_code == 401
