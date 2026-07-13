"""AI 路由集成测试"""

import pytest
from unittest.mock import MagicMock, patch
from app import create_app


@pytest.fixture
def app():
    """创建测试 app，mock DeepSeek 使其回退到规则引擎"""
    mock_ds = MagicMock()
    mock_ds.is_configured.return_value = False  # 强制回退规则引擎

    with patch("routes.ai_routes.get_deepseek", return_value=mock_ds), \
         patch("services.deepseek_service.get_deepseek", return_value=mock_ds), \
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
        text = "金毛旺财耳螨感染，开耳漂洗耳液，一周后复诊，150元"
        resp = client.post("/api/ai/parse-record", json={"text": text}, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        result = data["result"]
        assert "耳螨" in result["diagnosis"]["name"]
        assert result["confidence"] > 0
        assert data["engine"] == "rule_based"

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
        text = "柯基叫短腿，呕吐腹泻两天，诊断肠胃炎，口服益生菌，三天后复诊，费用200"
        resp = client.post("/api/ai/auto-fill", json={"text": text, "pet_id": 1}, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["form_data"]["pet_id"] == 1
        assert "肠胃炎" in data["form_data"]["diagnosis"]
        assert data["confidence"] > 0

    def test_auto_fill_with_vaccine(self, client, headers):
        text = "泰迪豆豆今天打狂犬疫苗第二针"
        resp = client.post("/api/ai/auto-fill", json={"text": text}, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["vaccine_data"] is not None

    def test_auto_fill_empty(self, client, headers):
        resp = client.post("/api/ai/auto-fill", json={"text": ""}, headers=headers)
        assert resp.status_code == 400


class TestDiseaseSuggest:
    def test_suggest(self, client, headers):
        resp = client.get("/api/ai/disease-suggest?symptoms=呕吐,腹泻,发烧", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["suggestions"]) > 0
        assert data["engine"] == "rule_based"

    def test_no_symptoms(self, client, headers):
        resp = client.get("/api/ai/disease-suggest", headers=headers)
        assert resp.status_code == 400

    def test_no_match(self, client, headers):
        resp = client.get("/api/ai/disease-suggest?symptoms=xyz", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["total_matches"] == 0


class TestTemplates:
    def test_get_templates(self, client, headers):
        resp = client.get("/api/ai/templates", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] >= 5
        assert data["templates"][0]["id"] == "skin"

    def test_no_auth(self, client):
        resp = client.get("/api/ai/templates")
        assert resp.status_code == 401
