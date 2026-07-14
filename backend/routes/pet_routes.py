"""宠物管理路由：登记、查看、搜索、更新、删除"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required

pet_bp = Blueprint("pet", __name__)


@pet_bp.route("/api/pets", methods=["GET"])
@token_required
def list_pets():
    """查看全部宠物，支持按 species/owner_name 过滤"""
    species = request.args.get("species", "").strip()
    owner = request.args.get("owner", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT p.*,
            (SELECT id FROM medical_records WHERE pet_id = p.id ORDER BY visit_date DESC LIMIT 1) AS recent_record_id,
            (SELECT diagnosis FROM medical_records WHERE pet_id = p.id ORDER BY visit_date DESC LIMIT 1) AS recent_diagnosis,
            (SELECT treatment FROM medical_records WHERE pet_id = p.id ORDER BY visit_date DESC LIMIT 1) AS recent_treatment,
            (SELECT visit_date FROM medical_records WHERE pet_id = p.id ORDER BY visit_date DESC LIMIT 1) AS recent_visit_date,
            (SELECT COUNT(*) FROM medical_records WHERE pet_id = p.id) AS total_visits
        FROM pet_details p WHERE 1=1
    """
    params = []

    if species:
        query += " AND p.species = %s"
        params.append(species)
    if owner:
        query += " AND p.owner_name LIKE %s"
        params.append(f"%{owner}%")
    if search:
        query += " AND (p.name LIKE %s OR p.breed LIKE %s OR p.owner_name LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY p.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    result = [dict(zip(columns, row)) for row in rows]
    return jsonify({"count": len(result), "data": result}), 200


@pet_bp.route("/api/pets/<int:pet_id>", methods=["GET"])
@token_required
def get_pet(pet_id):
    """查看单个宠物详情"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pet_details WHERE id = %s", (pet_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该宠物"}), 404

    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    return jsonify(dict(zip(columns, row))), 200


@pet_bp.route("/api/pets", methods=["POST"])
@token_required
def add_pet():
    """登记新宠物"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    name = (data.get("name") or "").strip()
    species = (data.get("species") or "").strip()
    owner_name = (data.get("owner_name") or "").strip()

    if not name:
        return jsonify({"error": "宠物名称不能为空"}), 400
    if not species:
        return jsonify({"error": "物种类别不能为空"}), 400
    if not owner_name:
        return jsonify({"error": "主人姓名不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO pet_details (name, species, breed, gender, age_months, weight_kg, color, owner_name, owner_contact, owner_address)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                name,
                species,
                data.get("breed", ""),
                data.get("gender", ""),
                int(data.get("age_months", 0)),
                float(data.get("weight_kg", 0)),
                data.get("color", ""),
                owner_name,
                str(data.get("owner_contact", "")),
                data.get("owner_address", ""),
            ),
        )
        conn.commit()
        pet_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"添加失败: {str(e)}"}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "宠物登记成功", "pet_id": pet_id}), 201


@pet_bp.route("/api/pets/<int:pet_id>", methods=["PUT"])
@token_required
def update_pet(pet_id):
    """更新宠物信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pet_details WHERE id = %s", (pet_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该宠物"}), 404

    data = request.get_json(silent=True) or {}

    try:
        cursor.execute(
            """UPDATE pet_details SET name=%s, species=%s, breed=%s, gender=%s, age_months=%s,
               weight_kg=%s, color=%s, owner_name=%s, owner_contact=%s, owner_address=%s
               WHERE id=%s""",
            (
                data.get("name", ""),
                data.get("species", ""),
                data.get("breed", ""),
                data.get("gender", ""),
                int(data.get("age_months", 0)),
                float(data.get("weight_kg", 0)),
                data.get("color", ""),
                data.get("owner_name", ""),
                str(data.get("owner_contact", "")),
                data.get("owner_address", ""),
                pet_id,
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
    return jsonify({"message": "宠物信息更新成功"}), 200


@pet_bp.route("/api/pets/<int:pet_id>", methods=["DELETE"])
@token_required
def delete_pet(pet_id):
    """删除宠物记录（级联删除关联的诊疗和疫苗记录）"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pet_details WHERE id = %s", (pet_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该宠物"}), 404

    cursor.execute("DELETE FROM pet_details WHERE id = %s", (pet_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "宠物记录已删除（含关联诊疗和疫苗记录）"}), 200


@pet_bp.route("/api/pets/stats", methods=["GET"])
@token_required
def pet_stats():
    """宠物统计信息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT species, COUNT(*) as cnt FROM pet_details GROUP BY species")
    species_stats = [{"species": r[0], "count": r[1]} for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM pet_details")
    total = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return jsonify({"total": total, "by_species": species_stats}), 200
