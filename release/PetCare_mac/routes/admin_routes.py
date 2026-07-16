"""兽医/助理/员工行政管理路由"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required, role_required

admin_bp = Blueprint("admin", __name__)

TABLE_MAP = {
    "vet": "vet_details",
    "assistant": "assistant_details",
    "worker": "other_workers_details",
}


@admin_bp.route("/api/admin/<string:role>", methods=["GET"])
@token_required
def list_staff(role):
    """查看指定角色全部人员"""
    table = TABLE_MAP.get(role)
    if not table:
        return jsonify({"error": "无效的角色类型，可选: vet/assistant/worker"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    result = [dict(zip(columns, row)) for row in rows]
    return jsonify({"count": len(result), "data": result}), 200


@admin_bp.route("/api/admin/<string:role>", methods=["POST"])
@role_required("admin")
def add_staff(role):
    """添加人员（仅管理员）"""
    table = TABLE_MAP.get(role)
    if not table:
        return jsonify({"error": "无效的角色类型，可选: vet/assistant/worker"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "姓名不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if role == "vet":
            cursor.execute(
                f"""INSERT INTO {table} (name, specialisation, license_no, age, address, contact, consultation_fee, monthly_salary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name,
                    data.get("specialisation", ""),
                    data.get("license_no", ""),
                    int(data.get("age", 0)),
                    data.get("address", ""),
                    str(data.get("contact", "")),
                    int(data.get("consultation_fee", 0)),
                    int(data.get("monthly_salary", 0)),
                ),
            )
        else:
            cursor.execute(
                f"""INSERT INTO {table} (name, role, age, address, contact, monthly_salary)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    name,
                    data.get("role", ""),
                    int(data.get("age", 0)),
                    data.get("address", ""),
                    str(data.get("contact", "")),
                    int(data.get("monthly_salary", 0)),
                ),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"添加失败: {str(e)}"}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "添加成功"}), 201


@admin_bp.route("/api/admin/<string:role>/<int:staff_id>", methods=["DELETE"])
@role_required("admin")
def delete_staff(role, staff_id):
    """删除人员（仅管理员）"""
    table = TABLE_MAP.get(role)
    if not table:
        return jsonify({"error": "无效的角色类型，可选: vet/assistant/worker"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (staff_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该记录"}), 404

    cursor.execute(f"DELETE FROM {table} WHERE id = ?", (staff_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "删除成功"}), 200
