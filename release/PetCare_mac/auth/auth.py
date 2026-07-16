"""认证模块：bcrypt 密码哈希 + JWT 令牌 + 角色权限"""

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
from config import Config


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配哈希值"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(username: str, role: str = "staff") -> str:
    """生成 JWT 访问令牌，包含角色信息"""
    now = datetime.now(timezone.utc)
    payload = {
        "username": username,
        "role": role,
        "exp": now + timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES),
        "iat": now,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """解码并验证 JWT 令牌，返回 payload 或 None"""
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """装饰器：验证请求中的 JWT 令牌"""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "缺少认证令牌"}), 401

        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": "令牌无效或已过期"}), 401

        request.current_user = payload["username"]
        request.current_role = payload.get("role", "staff")
        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """装饰器：验证用户角色是否在允许列表中"""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "缺少认证令牌"}), 401

            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload is None:
                return jsonify({"error": "令牌无效或已过期"}), 401

            user_role = payload.get("role", "staff")
            if user_role not in allowed_roles:
                return jsonify({"error": "权限不足，需要以下角色之一: " + ", ".join(allowed_roles)}), 403

            request.current_user = payload["username"]
            request.current_role = user_role
            return f(*args, **kwargs)

        return decorated

    return decorator
