"""患者管理路由：查看、添加、出院结算"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required

patient_bp = Blueprint("patient", __name__)

# 住院费用：每天 800，含 GST 系数 1.5
DAILY_CHARGE = 800
GST_FACTOR = 1.5


@patient_bp.route("/api/patients", methods=["GET"])
@token_required
def list_patients():
    """查看全部患者"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patient_details")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    result = [dict(zip(columns, row)) for row in rows]
    return jsonify({"count": len(result), "data": result}), 200


@patient_bp.route("/api/patients", methods=["POST"])
@token_required
def add_patient():
    """添加新患者（入院）"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "患者姓名不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO patient_details (name, gender, age, address, contact)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                name,
                data.get("gender", ""),
                int(data.get("age", 0)),
                data.get("address", ""),
                str(data.get("contact", "")),
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
    return jsonify({"message": "患者添加成功"}), 201


@patient_bp.route("/api/patients/<int:patient_id>", methods=["DELETE"])
@token_required
def discharge_patient(patient_id):
    """出院结算"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patient_details WHERE id = %s", (patient_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该患者"}), 404

    data = request.get_json(silent=True) or {}
    nights = int(data.get("nights", 0))

    total_bill = DAILY_CHARGE * GST_FACTOR * nights

    if data.get("bill_paid", "").lower() != "y":
        cursor.close()
        conn.close()
        return jsonify({
            "patient": row[1],
            "nights": nights,
            "total_bill": total_bill,
            "message": "请先结清账单",
        }), 400

    cursor.execute("DELETE FROM patient_details WHERE id = %s", (patient_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": "出院成功",
        "patient": row[1],
        "total_bill": total_bill,
    }), 200


@patient_bp.route("/api/patients/<int:patient_id>/bill", methods=["POST"])
@token_required
def calculate_bill(patient_id):
    """计算患者住院费用"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patient_details WHERE id = %s", (patient_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该患者"}), 404

    cursor.close()
    conn.close()

    data = request.get_json(silent=True) or {}
    nights = int(data.get("nights", 0))
    total_bill = DAILY_CHARGE * GST_FACTOR * nights

    return jsonify({
        "patient": row[1],
        "nights": nights,
        "daily_charge": DAILY_CHARGE,
        "gst_factor": GST_FACTOR,
        "total_bill": total_bill,
    }), 200
