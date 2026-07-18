"""DeepSeek AI 服务测试"""

import pytest
import json
from unittest.mock import MagicMock, patch, Mock
from services.deepseek_service import DeepSeekAI, get_deepseek


class TestDeepSeekAI:
    """DeepSeek 客户端测试"""

    def test_is_configured(self):
        ds = DeepSeekAI()
        # 默认无 API key（需通过环境变量 DEEPSEEK_API_KEY 设置）
        default_state = ds.is_configured()

    def test_chat_basic(self):
        ds = DeepSeekAI()
        mock_response = {
            "choices": [{"message": {"content": "你好，我是DeepSeek"}}],
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)
            result = ds._chat("你是一个助手", "你好")
            assert "DeepSeek" in result

    def test_chat_error(self):
        ds = DeepSeekAI()
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=500,
                json=lambda: {"error": {"message": "Server Error"}},
            )
            result = ds._chat("", "test")
            assert "[API错误]" in result

    def test_parse_medical_text_with_deepseek(self):
        ds = DeepSeekAI()
        mock_parsed = json.dumps({
            "pet_info": {"pet_name": "旺财", "species": "狗", "breed": "金毛", "gender": "公", "owner_name": "张三"},
            "diagnosis": {"name": "耳螨感染", "confidence": 85, "keywords": ["耳螨", "抓耳"]},
            "treatment": {"plan": "耳漂洗耳液 每日2次", "medications": [{"drug": "耳漂洗耳液", "dosage": "每日2次"}], "prescription": ""},
            "dates": {"visit_date": "", "follow_up_date": "2026-07-20"},
            "vitals": {},
            "fee": {"fee_charged": 150},
            "notes": "",
            "summary": "金毛旺财诊断耳螨感染。",
        })
        mock_response = {"choices": [{"message": {"content": mock_parsed}}]}
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)
            result = ds.parse_medical_text("金毛叫旺财，耳螨感染，一周后复诊，150元")
            assert "error" not in result
            assert result["diagnosis"]["name"] == "耳螨感染"
            assert result["pet_info"]["pet_name"] == "旺财"
            assert result["fee"]["fee_charged"] == 150

    def test_parse_medical_text_api_error(self):
        ds = DeepSeekAI()
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=500,
                json=lambda: {"error": {"message": "Internal"}},
            )
            result = ds.parse_medical_text("test")
            assert "error" in result

    def test_auto_fill(self):
        ds = DeepSeekAI()
        mock_parsed = json.dumps({
            "pet_info": {"pet_name": "咪咪", "species": "猫"},
            "diagnosis": {"name": "肠胃炎", "confidence": 80, "keywords": ["呕吐", "腹泻"]},
            "treatment": {"plan": "口服益生菌", "medications": [], "prescription": ""},
            "dates": {"visit_date": "", "follow_up_date": ""},
            "vitals": {},
            "fee": {"fee_charged": 280},
            "notes": "",
            "summary": "猫咪咪诊断肠胃炎。",
        })
        mock_response = {"choices": [{"message": {"content": mock_parsed}}]}
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)
            result = ds.auto_fill("猫咪咪呕吐腹泻，280元", pet_id=1)
            assert "error" not in result
            assert result["form_data"]["diagnosis"] == "肠胃炎"
            assert result["form_data"]["pet_id"] == 1

    def test_suggest_diseases(self):
        ds = DeepSeekAI()
        mock_list = json.dumps([
            {"disease": "肠胃炎", "confidence": 85, "description": "胃肠道炎症"},
            {"disease": "胰腺炎", "confidence": 60, "description": "胰腺炎症"},
        ])
        mock_response = {"choices": [{"message": {"content": mock_list}}]}
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)
            result = ds.suggest_diseases("呕吐,腹泻")
            assert "error" not in result
            assert result["total_matches"] == 2
            assert result["suggestions"][0]["disease"] == "肠胃炎"

    def test_extract_json_from_text(self):
        ds = DeepSeekAI()
        # 直接 JSON
        assert ds._extract_json('{"a": 1}') == {"a": 1}
        # Markdown 代码块
        assert ds._extract_json('```json\n{"a": 1}\n```') == {"a": 1}
        # 嵌套在文本中
        assert ds._extract_json('结果是 {"a": 1} 完成') == {"a": 1}
        # 无效文本
        assert ds._extract_json("不是JSON") is None
        # None/empty
        assert ds._extract_json("") is None

    def test_get_deepseek_singleton(self):
        ds1 = get_deepseek()
        ds2 = get_deepseek()
        assert ds1 is ds2
        # is_configured 取决于环境变量 DEEPSEEK_API_KEY 是否设置


class TestLLMParser:
    """LLM 优先的解析器测试"""

    def test_llm_first_rule_fallback(self):
        """DeepSeek 可用时优先使用，不可用时回退规则引擎"""
        from services.ai_parser import parse_medical_text_with_llm
        from services.deepseek_service import get_deepseek

        ds = get_deepseek()
        mock_parsed = {
            "pet_info": {"pet_name": "旺财"},
            "diagnosis": {"name": "耳螨感染", "confidence": 85},
            "treatment": {"plan": "清洗", "medications": [], "prescription": ""},
            "dates": {"visit_date": "", "follow_up_date": ""},
            "vitals": {},
            "fee": {"fee_charged": 100},
            "notes": "",
            "summary": "test",
        }
        mock_response = {"choices": [{"message": {"content": json.dumps(mock_parsed)}}]}

        with patch.object(ds, "is_configured", return_value=True), \
             patch("requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)
            result = parse_medical_text_with_llm("狗叫旺财")
            assert result.get("engine") == "deepseek"
            assert result["diagnosis"]["name"] == "耳螨感染"

    def test_llm_fallback_when_deepseek_fails(self):
        """DeepSeek 请求失败时回退规则引擎"""
        from services.ai_parser import parse_medical_text_with_llm

        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection error")
            result = parse_medical_text_with_llm("狗呕吐腹泻，肠胃炎")
            # 应回退到规则引擎
            assert result.get("engine") == "rule_based"
            assert "肠胃炎" in result["diagnosis"]["name"]


class TestEngineStatus:
    """AI 引擎状态端点测试"""

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
        return {"Authorization": f"Bearer {create_token('vet', 'vet')}"}

    def test_engine_status(self, client, headers):
        resp = client.get("/api/ai/engine-status", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "ai_engine" in data
        assert "deepseek_configured" in data
        # 默认未配置 API key，需环境变量
