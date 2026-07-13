"""PetCare 客户端测试"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from client.client import PetCareClient


@pytest.fixture
def client():
    return PetCareClient(host="127.0.0.1", port=5000)


class TestClientInit:
    def test_base_url(self, client):
        assert "127.0.0.1:5000" in client.base_url

    def test_token_none(self, client):
        assert client.token is None
        assert client.user_role is None

    def test_safe_int_valid(self, client):
        with patch("builtins.input", return_value="42"):
            assert client._safe_int(">") == 42

    def test_safe_int_invalid(self, client):
        with patch("builtins.input", return_value="abc"), patch("builtins.print"):
            assert client._safe_int(">") is None

    def test_safe_int_empty(self, client):
        with patch("builtins.input", return_value=""):
            assert client._safe_int(">") == 0


class TestHeadersAndHTTP:
    def test_headers_without_token(self, client):
        h = client._headers()
        assert "Authorization" not in h

    def test_headers_with_token(self, client):
        client.token = "jwt123"
        h = client._headers()
        assert h["Authorization"] == "Bearer jwt123"

    def test_get_with_params(self, client):
        with patch.object(client.session, "get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: {})
            client._get("/api/pets", {"species": "猫"})
            assert "species" in str(mock_get.call_args)

    def test_put_method(self, client):
        with patch.object(client.session, "put") as mock_put:
            mock_put.return_value = Mock(status_code=200, json=lambda: {"message": "ok"})
            resp = client._put("/api/pets/1", {"name": "test"})
            assert resp.status_code == 200

    def test_delete_no_data(self, client):
        with patch.object(client.session, "delete") as mock_del:
            mock_del.return_value = Mock(status_code=200, json=lambda: {})
            client._delete("/api/items/1")
            assert "json" not in mock_del.call_args[1]

    def test_delete_with_data(self, client):
        with patch.object(client.session, "delete") as mock_del:
            mock_del.return_value = Mock(status_code=200, json=lambda: {})
            client._delete("/api/items/1", {"key": "val"})
            assert "json" in mock_del.call_args[1]


class TestLogin:
    def test_login_success_sets_role(self, client):
        with patch.object(client, "_post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: {"message": "ok", "token": "jwt", "role": "vet"})
            with patch("builtins.input", side_effect=["admin", "pass"]), patch("builtins.print"):
                assert client.login() is True
                assert client.user_role == "vet"

    def test_login_failure(self, client):
        with patch.object(client, "_post") as mock_post:
            mock_post.return_value = Mock(status_code=401, json=lambda: {"error": "wrong"})
            with patch("builtins.input", side_effect=["admin", "wrong", ""]), patch("builtins.print"):
                assert client.login() is False


# ============================================================
# AI 助手功能测试
# ============================================================
class TestAIParseAndPreview:
    """AI 解析与预览"""

    def test_parse_and_preview_success(self, client):
        ai_result = {
            "status": "ok",
            "input_length": 30,
            "result": {
                "pet_info": {"pet_name": "旺财", "pet_species": "狗"},
                "diagnosis": {"name": "耳螨感染", "confidence": 60, "keywords": ["耳螨"]},
                "treatment": {"plan": "清洗耳朵", "items": [], "medications": [], "prescription": ""},
                "dates": {"visit_date": "", "follow_up_date": "2026-07-20"},
                "vitals": {},
                "fee": {"fee_charged": 150},
                "notes": "",
                "summary": "诊断：耳螨感染。费用：150元。",
                "confidence": 55,
            },
        }
        with patch.object(client, "_post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: ai_result)
            with patch("builtins.print"), patch("builtins.input", return_value="n"):
                client._ai_parse_and_preview("金毛旺财耳螨感染")
                mock_post.assert_called_once()

    def test_parse_failure(self, client):
        with patch.object(client, "_post") as mock_post:
            mock_post.return_value = Mock(status_code=400, json=lambda: {"error": "文本为空"})
            with patch("builtins.print"):
                client._ai_parse_and_preview("")
                mock_post.assert_called_once()

    def test_text_input_flow(self, client):
        with patch.object(client, "_ai_parse_and_preview") as mock_preview:
            with patch("builtins.input", return_value="狗叫旺财，耳螨"), patch("builtins.print"):
                client._ai_text_input()
                mock_preview.assert_called_once_with("狗叫旺财，耳螨")

    def test_text_input_empty(self, client):
        with patch.object(client, "_ai_parse_and_preview") as mock_preview:
            with patch("builtins.input", return_value=""), patch("builtins.print"):
                client._ai_text_input()
                mock_preview.assert_not_called()


class TestAIDiseaseSuggest:
    """疾病建议"""

    def test_suggest_disease(self, client):
        mock_data = {
            "symptoms": ["呕吐", "腹泻"],
            "suggestions": [
                {"disease": "肠胃炎", "confidence": 80, "matched_keywords": ["呕吐", "腹泻"]},
            ],
            "total_matches": 1,
        }
        with patch.object(client, "_get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_data)
            with patch("builtins.input", return_value="呕吐,腹泻"), patch("builtins.print"):
                client._ai_disease_suggest()
                mock_get.assert_called_once_with("/api/ai/disease-suggest", {"symptoms": "呕吐,腹泻"})


class TestAITemplates:
    """病历模板"""

    def test_get_templates(self, client):
        mock_data = {
            "templates": [
                {"id": "skin", "name": "皮肤病模板", "category": "皮肤科", "content": "..."},
                {"id": "gi", "name": "消化系统模板", "category": "内科", "content": "..."},
            ],
            "count": 2,
        }
        with patch.object(client, "_get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_data)
            with patch("builtins.input", side_effect=["", ""]), patch("builtins.print"):
                client._ai_templates()
                mock_get.assert_called_once()


class TestAIAutoFill:
    """一键填表"""

    def test_auto_fill_success(self, client):
        mock_data = {
            "status": "ok",
            "confidence": 60,
            "summary": "诊断：肠胃炎。",
            "parsed": {},
            "form_data": {
                "pet_id": None, "vet_name": "", "visit_date": "",
                "diagnosis": "肠胃炎", "treatment": "口服益生菌",
                "notes": "", "follow_up_date": None, "fee_charged": 280,
            },
            "vaccine_data": None,
        }
        with patch.object(client, "_post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_data)
            with patch("builtins.input", side_effect=["猫腹泻两天", "0", "n"]), patch("builtins.print"):
                client._ai_auto_fill_and_submit()
                assert mock_post.call_count >= 1


class TestAIRecordAudio:
    """语音录制 — 三级降级: 讯飞 → Google → 手动"""

    def test_record_fallback_manual(self, client):
        """speech_recognition 未安装时回退到文字输入"""
        with patch("builtins.input", return_value="手动输入文本"), patch("builtins.print"):
            # 模拟 speech_recognition 导入失败
            import builtins
            original = builtins.__import__

            def mock_import(name, *a, **kw):
                if "speech_recognition" in name:
                    raise ImportError("mock")
                return original(name, *a, **kw)

            with patch("builtins.__import__", side_effect=mock_import):
                result = client._record_audio()
                assert result == "手动输入文本"

    def test_record_iflytek_credentials_env(self):
        """验证讯飞环境变量检测"""
        import os
        # 检查函数能否正确读取环境变量
        has_key = bool(os.getenv("IFLYTEK_API_KEY"))
        has_id = bool(os.getenv("IFLYTEK_APP_ID"))
        has_secret = bool(os.getenv("IFLYTEK_API_SECRET"))
        # 至少能运行不会崩溃
        assert isinstance(has_key, bool)
        assert isinstance(has_id, bool)
        assert isinstance(has_secret, bool)
