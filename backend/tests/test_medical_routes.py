"""诊疗记录路由测试"""

import pytest

MR_COLS = [("id",), ("pet_id",), ("vet_name",), ("visit_date",), ("diagnosis",),
           ("treatment",), ("notes",), ("follow_up_date",), ("fee_charged",),
           ("created_at",), ("pet_name",), ("species",)]


class TestListMedicalRecords:
    def test_list_all(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = MR_COLS
        mock_db_cursor.fetchall.return_value = [(1, 1, "Dr. Li", "2025-06-01", "感冒", "吃药", "", None, 200, "", "旺财", "狗")]
        resp = client.get("/api/medical-records", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1

    def test_filter_by_pet(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = MR_COLS
        mock_db_cursor.fetchall.return_value = []
        resp = client.get("/api/medical-records?pet_id=1", headers=auth_headers)
        assert resp.status_code == 200

    def test_no_auth(self, client):
        assert client.get("/api/medical-records").status_code == 401


class TestAddMedicalRecord:
    def test_add_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1,)  # pet exists
        payload = {"pet_id": 1, "vet_name": "Dr. Li", "visit_date": "2025-06-01", "diagnosis": "皮肤过敏", "treatment": "药膏", "fee_charged": 300}
        resp = client.post("/api/medical-records", json=payload, headers=auth_headers)
        assert resp.status_code == 201

    def test_pet_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        resp = client.post("/api/medical-records", json={"pet_id": 999, "visit_date": "2025-01-01", "diagnosis": "test"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_missing_diagnosis(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = (1,)
        resp = client.post("/api/medical-records", json={"pet_id": 1, "visit_date": "2025-01-01"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_missing_visit_date(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = (1,)
        resp = client.post("/api/medical-records", json={"pet_id": 1, "diagnosis": "test"}, headers=auth_headers)
        assert resp.status_code == 400


class TestUpdateMedicalRecord:
    def test_update_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1,)
        resp = client.put("/api/medical-records/1", json={"diagnosis": "updated"}, headers=auth_headers)
        assert resp.status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.put("/api/medical-records/999", json={}, headers=auth_headers).status_code == 404


class TestDeleteMedicalRecord:
    def test_delete_success(self, client, auth_headers, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = (1,)
        resp = client.delete("/api/medical-records/1", headers=auth_headers)
        assert resp.status_code == 200

    def test_not_found(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = None
        assert client.delete("/api/medical-records/999", headers=auth_headers).status_code == 404
