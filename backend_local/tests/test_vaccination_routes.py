"""疫苗接种路由测试"""

import pytest

VAC_COLS = [("id",), ("pet_id",), ("vaccine_name",), ("dose_number",), ("administered_date",),
            ("next_due_date",), ("vet_name",), ("batch_number",), ("notes",),
            ("created_at",), ("pet_name",), ("species",)]


class TestListVaccinations:
    def test_list_all(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = VAC_COLS
        mock_db_cursor.fetchall.return_value = [(1, 1, "狂犬疫苗", 1, "2025-01-01", "2025-07-01", "Dr. Li", "B001", "", "", "旺财", "狗")]
        resp = client.get("/api/vaccinations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1

    def test_by_pet(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = VAC_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/vaccinations?pet_id=1", headers=auth_headers)
        assert resp.status_code == 200

    def test_upcoming(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = VAC_COLS + [("owner_name",), ("owner_contact",)]
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/vaccinations?upcoming=true", headers=auth_headers)
        assert resp.status_code == 200

    def test_no_auth(self, client):
        assert client.get("/api/vaccinations").status_code == 401


class TestAddVaccination:
    def test_add_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1,)
        payload = {"pet_id": 1, "vaccine_name": "狂犬疫苗", "administered_date": "2025-06-01", "dose_number": 2}
        resp = client.post("/api/vaccinations", json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_pet_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        resp = client.post("/api/vaccinations", json={"pet_id": 999, "vaccine_name": "狂犬", "administered_date": "2025-01-01"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_missing_vaccine_name(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = (1,)
        resp = client.post("/api/vaccinations", json={"pet_id": 1, "administered_date": "2025-01-01"}, headers=auth_headers)
        assert resp.status_code == 400


class TestDeleteVaccination:
    def test_delete_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1,)
        assert client.delete("/api/vaccinations/1", headers=auth_headers).status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.delete("/api/vaccinations/999", headers=auth_headers).status_code == 404
