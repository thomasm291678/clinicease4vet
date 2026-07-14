"""疫苗接种路由：接种记录管理、到期提醒"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required

vaccine_bp = Blueprint("vaccine", __name__)


@vaccine_bp.route("/api/vaccinations", methods=["GET"])
@token_required
def list_vaccinations():
    """查看接种记录，支持按 pet_id 过滤"""
    pet_id = request.args.get("pet_id", "").strip()
    upcoming = request.args.get("upcoming", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    if upcoming == "true":
        # 到期提醒：next_due_date 在今天之后 30 天内
        cursor.execute(
            """SELECT vr.*, p.name AS pet_name, p.species, p.owner_name, p.owner_contact
               FROM vaccination_records vr
               JOIN pet_details p ON vr.pet_id = p.id
               WHERE vr.next_due_date IS NOT NULL
                 AND vr.next_due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
               ORDER BY vr.next_due_date ASC"""
        )
    elif pet_id:
        cursor.execute(
            """SELECT vr.*, p.name AS pet_name, p.species, p.owner_name
               FROM vaccination_records vr
               JOIN pet_details p ON vr.pet_id = p.id
               WHERE vr.pet_id = %s
               ORDER BY vr.administered_date DESC""",
            (pet_id,),
        )
    else:
        cursor.execute(
            """SELECT vr.*, p.name AS pet_name, p.species, p.owner_name
               FROM vaccination_records vr
               JOIN pet_details p ON vr.pet_id = p.id
               ORDER BY vr.administered_date DESC"""
        )

    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    result = [dict(zip(columns, row)) for row in rows]
    return jsonify({"count": len(result), "data": result}), 200


@vaccine_bp.route("/api/vaccinations", methods=["POST"])
@token_required
def add_vaccination():
    """添加接种记录"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    pet_id = data.get("pet_id")
    vaccine_name = (data.get("vaccine_name") or "").strip()
    administered_date = (data.get("administered_date") or "").strip()

    if not pet_id:
        return jsonify({"error": "宠物ID不能为空"}), 400
    if not vaccine_name:
        return jsonify({"error": "疫苗名称不能为空"}), 400
    if not administered_date:
        return jsonify({"error": "接种日期不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM pet_details WHERE id = %s", (pet_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "宠物不存在"}), 404

    try:
        cursor.execute(
            """INSERT INTO vaccination_records (pet_id, vaccine_name, dose_number, administered_date, next_due_date, vet_name, batch_number, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                pet_id,
                vaccine_name,
                int(data.get("dose_number", 1)),
                administered_date,
                data.get("next_due_date") or None,
                data.get("vet_name", ""),
                data.get("batch_number", ""),
                data.get("notes", ""),
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
    return jsonify({"message": "接种记录添加成功", "record_id": record_id}), 201


@vaccine_bp.route("/api/vaccinations/<int:record_id>", methods=["DELETE"])
@token_required
def delete_vaccination(record_id):
    """删除接种记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM vaccination_records WHERE id = %s", (record_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该记录"}), 404

    cursor.execute("DELETE FROM vaccination_records WHERE id = %s", (record_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "接种记录已删除"}), 200
