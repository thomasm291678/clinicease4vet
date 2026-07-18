"""测试共用 fixtures：mock 数据库，Flask test client"""

import pytest
from unittest.mock import MagicMock, patch
from app import create_app


@pytest.fixture
def mock_db_cursor():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    cursor.description = []
    cursor.lastrowid = 1
    return cursor


@pytest.fixture
def mock_db_connection(mock_db_cursor):
    conn = MagicMock()
    conn.cursor.return_value = mock_db_cursor
    return conn


@pytest.fixture
def app(mock_db_connection):
    with patch("routes.auth_routes.get_connection", return_value=mock_db_connection), \
         patch("routes.admin_routes.get_connection", return_value=mock_db_connection), \
         patch("routes.pet_routes.get_connection", return_value=mock_db_connection), \
         patch("routes.medical_routes.get_connection", return_value=mock_db_connection), \
         patch("routes.vaccination_routes.get_connection", return_value=mock_db_connection), \
         patch("routes.drug_routes.get_connection", return_value=mock_db_connection), \
         patch("app.init_database"):
        test_app = create_app()
        test_app.config["TESTING"] = True
        yield test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    from auth.auth import create_token
    token = create_token("testuser", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vet_headers():
    from auth.auth import create_token
    token = create_token("vetuser", "vet")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_headers():
    from auth.auth import create_token
    token = create_token("staffuser", "staff")
    return {"Authorization": f"Bearer {token}"}
