"""认证相关路由：注册、登录（支持角色）"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import hash_password, verify_password, create_token

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = ["admin", "vet", "staff"]


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """用户注册，支持角色选择"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "staff").strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少需要6个字符"}), 400
    if role not in VALID_ROLES:
        return jsonify({"error": f"无效角色，可选: {', '.join(VALID_ROLES)}"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM user_data WHERE username = ?", (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "用户名已存在"}), 409

    password_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO user_data (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "注册成功", "role": role}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """用户登录，返回 JWT 令牌（含角色）"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash, role FROM user_data WHERE username = ?", (username,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "用户名或密码错误"}), 401

    if not verify_password(password, row[0]):
        return jsonify({"error": "用户名或密码错误"}), 401

    token = create_token(username, row[1])
    return jsonify({"message": "登录成功", "token": token, "role": row[1]}), 200
