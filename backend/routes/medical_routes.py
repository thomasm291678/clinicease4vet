"""诊疗记录路由：创建、查看、更新诊疗记录"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required

medical_bp = Blueprint("medical", __name__)


@medical_bp.route("/api/medical-records", methods=["GET"])
@token_required
def list_records():
    """查看诊疗记录，支持按 pet_id 过滤"""
    pet_id = request.args.get("pet_id", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    if pet_id:
        cursor.execute(
            """SELECT mr.*, p.name AS pet_name, p.species
               FROM medical_records mr
               JOIN pet_details p ON mr.pet_id = p.id
               WHERE mr.pet_id = %s
               ORDER BY mr.visit_date DESC""",
            (pet_id,),
        )
    else:
        cursor.execute(
            """SELECT mr.*, p.name AS pet_name, p.species
               FROM medical_records mr
               JOIN pet_details p ON mr.pet_id = p.id
               ORDER BY mr.visit_date DESC"""
        )

    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    result = [dict(zip(columns, row)) for row in rows]
    return jsonify({"count": len(result), "data": result}), 200


@medical_bp.route("/api/medical-records", methods=["POST"])
@token_required
def add_record():
    """创建新诊疗记录"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    pet_id = data.get("pet_id")
    visit_date = (data.get("visit_date") or "").strip()
    diagnosis = (data.get("diagnosis") or "").strip()

    if not pet_id:
        return jsonify({"error": "宠物ID不能为空"}), 400
    if not visit_date:
        return jsonify({"error": "就诊日期不能为空"}), 400
    if not diagnosis:
        return jsonify({"error": "诊断结果不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # 验证宠物存在
    cursor.execute("SELECT id FROM pet_details WHERE id = %s", (pet_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "宠物不存在"}), 404

    try:
        cursor.execute(
            """INSERT INTO medical_records (pet_id, vet_name, visit_date, diagnosis, treatment, symptoms,
               subjective, objective, assessment, plan, notes, follow_up_date, fee_charged)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                pet_id,
                data.get("vet_name", ""),
                visit_date,
                diagnosis,
                data.get("treatment", ""),
                data.get("symptoms", ""),
                data.get("subjective", ""),
                data.get("objective", ""),
                data.get("assessment", diagnosis),
                data.get("plan", ""),
                data.get("notes", ""),
                data.get("follow_up_date") or None,
                int(data.get("fee_charged", 0)),
            ),
        )
        conn.commit()
        record_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"添加失败: {str(e)}"}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "诊疗记录创建成功", "record_id": record_id}), 201


@medical_bp.route("/api/medical-records/<int:record_id>", methods=["PUT"])
@token_required
def update_record(record_id):
    """更新诊疗记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM medical_records WHERE id = %s", (record_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该记录"}), 404

    data = request.get_json(silent=True) or {}
    try:
        cursor.execute(
            """UPDATE medical_records SET vet_name=%s, visit_date=%s, diagnosis=%s,
               treatment=%s, symptoms=%s, subjective=%s, objective=%s,
               assessment=%s, plan=%s, notes=%s, follow_up_date=%s, fee_charged=%s WHERE id=%s""",
            (
                data.get("vet_name", ""),
                data.get("visit_date", ""),
                data.get("diagnosis", ""),
                data.get("treatment", ""),
                data.get("symptoms", ""),
                data.get("subjective", ""),
                data.get("objective", ""),
                data.get("assessment", data.get("diagnosis", "")),
                data.get("plan", ""),
                data.get("notes", ""),
                data.get("follow_up_date") or None,
                int(data.get("fee_charged", 0)),
                record_id,
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"更新失败: {str(e)}"}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "诊疗记录更新成功"}), 200


@medical_bp.route("/api/medical-records/<int:record_id>", methods=["DELETE"])
@token_required
def delete_record(record_id):
    """删除诊疗记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM medical_records WHERE id = %s", (record_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该记录"}), 404

    cursor.execute("DELETE FROM medical_records WHERE id = %s", (record_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "诊疗记录已删除"}), 200
