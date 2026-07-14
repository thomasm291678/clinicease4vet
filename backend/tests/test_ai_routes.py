"""AI 路由集成测试 — 纯 DeepSeek LLM"""

import pytest
import json
from unittest.mock import MagicMock, patch
from app import create_app


@pytest.fixture
def app():
    mock_ds = MagicMock()
    mock_ds.is_configured.return_value = True
    mock_ds.parse_medical_text.return_value = {
        "pet_info": {"pet_name": "旺财", "species": "狗", "breed": "金毛", "gender": "", "owner_name": "", "owner_contact": ""},
        "diagnosis": {"name": "耳螨感染", "confidence": 85, "keywords": ["耳螨"]},
        "treatment": {"plan": "耳漂洗耳液", "medications": [], "prescription": ""},
        "dates": {"visit_date": "", "follow_up_date": "2026-07-20"},
        "vitals": {},
        "fee": {"fee_charged": 150},
        "notes": "",
        "summary": "旺财诊断耳螨感染。",
        "engine": "deepseek",
    }
    mock_ds.auto_fill.return_value = {
        "form_data": {"pet_id": 1, "diagnosis": "肠胃炎", "treatment": "口服益生菌", "symptoms": "呕吐,腹泻", "notes": ""},
        "vaccine_data": None,
        "summary": "柯基诊断肠胃炎。",
        "confidence": 80,
    }
    mock_ds.suggest_diseases.return_value = {
        "suggestions": [{"disease": "肠胃炎", "confidence": 85, "description": "胃肠道炎症"}],
        "total_matches": 1,
    }

    with patch("routes.ai_routes.get_deepseek", return_value=mock_ds), \
         patch("services.deepseek_service.get_deepseek", return_value=mock_ds), \
         patch("services.ai_parser.get_deepseek", return_value=mock_ds), \
         patch("app.init_database"):
        test_app = create_app()
        test_app.config["TESTING"] = True
        yield test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def headers():
    from auth.auth import create_token
    token = create_token("vet", "vet")
    return {"Authorization": f"Bearer {token}"}


class TestParseRecord:
    def test_parse_ear_mites(self, client, headers):
        resp = client.post("/api/ai/parse-record", json={
            "text": "金毛旺财耳螨感染，开耳漂洗耳液，一周后复诊，150元"
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["engine"] == "deepseek"

    def test_empty_text(self, client, headers):
        resp = client.post("/api/ai/parse-record", json={"text": ""}, headers=headers)
        assert resp.status_code == 400

    def test_missing_text(self, client, headers):
        resp = client.post("/api/ai/parse-record", json={}, headers=headers)
        assert resp.status_code == 400

    def test_no_auth(self, client):
        resp = client.post("/api/ai/parse-record", json={"text": "test"})
        assert resp.status_code == 401


class TestAutoFill:
    def test_auto_fill(self, client, headers):
        resp = client.post("/api/ai/auto-fill", json={
            "text": "柯基叫短腿，呕吐腹泻两天，诊断肠胃炎，口服益生菌，三天后复诊，费用200",
            "pet_id": 1,
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["form_data"]["pet_id"] == 1
        assert "肠胃炎" in data["form_data"]["diagnosis"]

    def test_auto_fill_empty(self, client, headers):
        resp = client.post("/api/ai/auto-fill", json={"text": ""}, headers=headers)
        assert resp.status_code == 400


class TestDiseaseSuggest:
    def test_suggest(self, client, headers):
        resp = client.get("/api/ai/disease-suggest?symptoms=呕吐,腹泻,发烧", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["suggestions"]) > 0

    def test_no_symptoms(self, client, headers):
        resp = client.get("/api/ai/disease-suggest", headers=headers)
        assert resp.status_code == 400


class TestTemplates:
    def test_get_templates(self, client, headers):
        resp = client.get("/api/ai/templates", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] >= 5

    def test_no_auth(self, client):
        resp = client.get("/api/ai/templates")
        assert resp.status_code == 401
