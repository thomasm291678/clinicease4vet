"""宠物管理路由测试"""

import pytest

PET_COLS = [("id",), ("name",), ("species",), ("breed",), ("gender",),
            ("age_months",), ("weight_kg",), ("color",),
            ("owner_name",), ("owner_contact",), ("owner_address",), ("registered_at",)]
FAKE_PET = (1, "旺财", "狗", "金毛", "公", 12, 25.5, "金色", "张三", "13800001111", "北京", "2025-01-01")


class TestListPets:
    def test_list_all(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = PET_COLS
        mock_db_cursor.fetchall.return_value = [FAKE_PET]
        resp = client.get("/api/pets", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1

    def test_filter_by_species(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = PET_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/pets?species=猫", headers=auth_headers)
        assert resp.status_code == 200

    def test_search(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = PET_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/pets?search=旺财", headers=auth_headers)
        assert resp.status_code == 200

    def test_no_auth(self, client):
        assert client.get("/api/pets").status_code == 401


class TestGetPet:
    def test_get_by_id(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = PET_COLS
        mock_db_cursor.fetchone.return_value = FAKE_PET
        resp = client.get("/api/pets/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "旺财"

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.get("/api/pets/999", headers=auth_headers).status_code == 404


class TestAddPet:
    def test_add_success(self, client, auth_headers, mock_db_connection):
        payload = {"name": "咪咪", "species": "猫", "breed": "英短", "owner_name": "李四"}
        resp = client.post("/api/pets", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()["pet_id"] == 1

    def test_missing_name(self, client, auth_headers):
        resp = client.post("/api/pets", json={"species": "狗", "owner_name": "王五"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_missing_species(self, client, auth_headers):
        resp = client.post("/api/pets", json={"name": "旺财", "owner_name": "王五"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_missing_owner(self, client, auth_headers):
        resp = client.post("/api/pets", json={"name": "旺财", "species": "狗"}, headers=auth_headers)
        assert resp.status_code == 400


class TestUpdatePet:
    def test_update_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = FAKE_PET
        resp = client.put("/api/pets/1", json={"name": "旺财2", "weight_kg": 30.0}, headers=auth_headers)
        assert resp.status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.put("/api/pets/999", json={}, headers=auth_headers).status_code == 404


class TestDeletePet:
    def test_delete_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = FAKE_PET
        resp = client.delete("/api/pets/1", headers=auth_headers)
        assert resp.status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.delete("/api/pets/999", headers=auth_headers).status_code == 404


class TestPetStats:
    def test_stats(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = (3,)
        mock_db_cursor.fetchall.return_value = [("狗", 2), ("猫", 1)]
        resp = client.get("/api/pets/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3
        assert len(data["by_species"]) == 2
