"""认证 + 权限系统测试：含角色支持"""

import pytest


class TestBcrypt:
    def test_hash_and_verify(self):
        from auth.auth import hash_password, verify_password
        h = hash_password("mypass123")
        assert verify_password("mypass123", h)

    def test_wrong_password(self):
        from auth.auth import hash_password, verify_password
        h = hash_password("correct")
        assert not verify_password("wrong", h)


class TestJWT:
    def test_create_token_with_role(self):
        from auth.auth import create_token, decode_token
        token = create_token("admin1", "admin")
        payload = decode_token(token)
        assert payload["username"] == "admin1"
        assert payload["role"] == "admin"

    def test_default_role(self):
        from auth.auth import create_token, decode_token
        token = create_token("user1")
        payload = decode_token(token)
        assert payload["role"] == "staff"

    def test_invalid_token(self):
        from auth.auth import decode_token
        assert decode_token("bad.token") is None
        assert decode_token("") is None


class TestRoleRequired:
    def test_admin_access_allowed(self, client, auth_headers, mock_db_cursor):
        mock_db_cursor.description = [("id",), ("name",)]
        resp = client.post("/api/admin/vet", json={"name": "Dr. Li"}, headers=auth_headers)
        assert resp.status_code == 201

    def test_vet_denied_admin_action(self, client, vet_headers):
        resp = client.post("/api/admin/vet", json={"name": "Dr. Li"}, headers=vet_headers)
        assert resp.status_code == 403

    def test_staff_denied_admin_action(self, client, staff_headers):
        resp = client.post("/api/admin/vet", json={"name": "Dr. Li"}, headers=staff_headers)
        assert resp.status_code == 403

    def test_no_auth(self, client):
        resp = client.post("/api/admin/vet", json={"name": "Dr. Li"})
        assert resp.status_code == 401


class TestAuthRoutes:
    def test_register_with_role(self, client, mock_db_cursor, mock_db_connection):
        mock_db_cursor.fetchone.return_value = None
        resp = client.post("/api/auth/register", json={"username": "vet1", "password": "pass1234", "role": "vet"})
        assert resp.status_code == 201
        assert resp.get_json()["role"] == "vet"

    def test_register_invalid_role(self, client):
        resp = client.post("/api/auth/register", json={"username": "x", "password": "pass1234", "role": "owner"})
        assert resp.status_code == 400

    def test_login_returns_role(self, client, mock_db_cursor):
        from auth.auth import hash_password
        mock_db_cursor.fetchone.return_value = (hash_password("pass"), "vet")
        resp = client.post("/api/auth/login", json={"username": "vet1", "password": "pass"})
        assert resp.status_code == 200
        assert resp.get_json()["role"] == "vet"
