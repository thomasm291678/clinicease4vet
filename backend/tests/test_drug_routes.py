"""药品库存路由测试"""

import pytest

DRUG_COLS = [("id",), ("drug_name",), ("category",), ("manufacturer",), ("batch_number",),
             ("quantity",), ("unit",), ("unit_price",), ("expiry_date",),
             ("storage_condition",), ("min_stock_level",), ("notes",), ("updated_at",)]

FAKE_DRUG = (1, "阿莫西林", "抗生素", "XX药厂", "B2025", 100, "盒", 25.0, "2026-12-31", "常温", 10, "", "")


class TestListDrugs:
    def test_list_all(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = DRUG_COLS
        mock_db_cursor.fetchall.return_value = [FAKE_DRUG]
        resp = client.get("/api/drugs", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1

    def test_low_stock(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = DRUG_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/drugs?low_stock=true", headers=auth_headers)
        assert resp.status_code == 200

    def test_expired(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = DRUG_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/drugs?expired=true", headers=auth_headers)
        assert resp.status_code == 200

    def test_search(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = DRUG_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/drugs?search=阿莫西林", headers=auth_headers)
        assert resp.status_code == 200

    def test_no_auth(self, client):
        assert client.get("/api/drugs").status_code == 401


class TestAddDrug:
    def test_add_success(self, client, auth_headers, mock_db_connection):
        payload = {"drug_name": "阿莫西林", "quantity": 100, "unit_price": 25.0}
        resp = client.post("/api/drugs", json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_missing_name(self, client, auth_headers):
        resp = client.post("/api/drugs", json={"quantity": 10}, headers=auth_headers)
        assert resp.status_code == 400


class TestStockInOut:
    def test_stock_in_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1, 100)
        resp = client.post("/api/drugs/1/stock-in", json={"quantity": 20}, headers=auth_headers)
        assert resp.status_code == 200
        assert "入库成功" in resp.get_json()["message"]

    def test_stock_in_zero(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = (1, 100)
        resp = client.post("/api/drugs/1/stock-in", json={"quantity": 0}, headers=auth_headers)
        assert resp.status_code == 400

    def test_stock_out_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1, 100, "阿莫西林")
        resp = client.post("/api/drugs/1/stock-out", json={"quantity": 5}, headers=auth_headers)
        assert resp.status_code == 200

    def test_stock_out_exceed(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = (1, 10, "阿莫西林")
        resp = client.post("/api/drugs/1/stock-out", json={"quantity": 100}, headers=auth_headers)
        assert resp.status_code == 400

    def test_stock_out_drug_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        resp = client.post("/api/drugs/999/stock-out", json={"quantity": 1}, headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateDrug:
    def test_update_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = FAKE_DRUG
        resp = client.put("/api/drugs/1", json={"drug_name": "更新药品"}, headers=auth_headers)
        assert resp.status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.put("/api/drugs/999", json={}, headers=auth_headers).status_code == 404


class TestDeleteDrug:
    def test_delete_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = FAKE_DRUG
        assert client.delete("/api/drugs/1", headers=auth_headers).status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.delete("/api/drugs/999", headers=auth_headers).status_code == 404
