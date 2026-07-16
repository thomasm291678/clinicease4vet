"""宠物管理路由：登记、查看、搜索、更新、删除（SQLite 版）"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required

pet_bp = Blueprint("pets", __name__)


@pet_bp.route("/api/pets", methods=["GET"])
@token_required
def list_pets():
    species = request.args.get("species", "").strip()
    owner = request.args.get("owner", "").strip()
    search = request.args.get("search", "").strip()

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
        query += " AND p.species = ?"
        params.append(species)
    if owner:
        query += " AND p.owner_name LIKE ?"
        params.append(f"%{owner}%")
    if search:
        query += " AND (p.name LIKE ? OR p.breed LIKE ? OR p.owner_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY p.id DESC"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    data = [dict(r) for r in rows]
    cursor.close()
    conn.close()

    return jsonify({"data": data, "count": len(data)}), 200


@pet_bp.route("/api/pets/<int:pet_id>", methods=["GET"])
@token_required
def get_pet(pet_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pet_details WHERE id = ?", (pet_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "宠物不存在"}), 404

    return jsonify({"data": dict(row)}), 200


@pet_bp.route("/api/pets", methods=["POST"])
@token_required
def create_pet():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    name = (data.get("name") or "").strip()
    species = (data.get("species") or "").strip()
    owner_name = (data.get("owner_name") or "").strip()

    if not name:
        return jsonify({"error": "宠物名称不能为空"}), 400
    if not species:
        return jsonify({"error": "宠物种类不能为空"}), 400
    if not owner_name:
        return jsonify({"error": "主人姓名不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO pet_details (name, species, breed, gender, age_months, weight_kg,
               color, owner_name, owner_contact, owner_address)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                species,
                data.get("breed", ""),
                data.get("gender", ""),
                data.get("age_months"),
                data.get("weight_kg"),
                data.get("color", ""),
                owner_name,
                data.get("owner_contact", ""),
                data.get("owner_address", ""),
            ),
        )
        conn.commit()
        pet_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "宠物登记成功", "pet_id": pet_id}), 201


@pet_bp.route("/api/pets/<int:pet_id>", methods=["PUT"])
@token_required
def update_pet(pet_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pet_details WHERE id = ?", (pet_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "宠物不存在"}), 404

    data = request.get_json(silent=True) or {}
    try:
        cursor.execute(
            """UPDATE pet_details SET name=?, species=?, breed=?, gender=?, age_months=?,
               weight_kg=?, color=?, owner_name=?, owner_contact=?, owner_address=?
               WHERE id=?""",
            (
                data.get("name", ""),
                data.get("species", ""),
                data.get("breed", ""),
                data.get("gender", ""),
                data.get("age_months"),
                data.get("weight_kg"),
                data.get("color", ""),
                data.get("owner_name", ""),
                data.get("owner_contact", ""),
                data.get("owner_address", ""),
                pet_id,
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "宠物信息更新成功"}), 200


@pet_bp.route("/api/pets/<int:pet_id>", methods=["DELETE"])
@token_required
def delete_pet(pet_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pet_details WHERE id = ?", (pet_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "宠物不存在"}), 404

    cursor.execute("DELETE FROM pet_details WHERE id = ?", (pet_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "宠物删除成功"}), 200


@pet_bp.route("/api/pets/stats", methods=["GET"])
@token_required
def pet_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT species, COUNT(*) as cnt FROM pet_details GROUP BY species")
    rows = cursor.fetchall()
    stats = [{"species": r[0], "count": r[1]} for r in rows]
    cursor.close()
    conn.close()
    return jsonify({"data": stats}), 200
