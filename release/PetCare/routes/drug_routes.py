"""药品库存路由：入库、出库、查询、低库存预警"""

from datetime import date
from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required

drug_bp = Blueprint("drug", __name__)


@drug_bp.route("/api/drugs", methods=["GET"])
@token_required
def list_drugs():
    """查看药品库存，支持搜索、低库存预警"""
    search = request.args.get("search", "").strip()
    low_stock = request.args.get("low_stock", "").strip()
    expired = request.args.get("expired", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["1=1"]
    params = []

    if low_stock == "true":
        conditions.append("quantity <= min_stock_level")
    if expired == "true":
        conditions.append("expiry_date IS NOT NULL AND expiry_date <= ?")
        params.append(date.today().isoformat())
    if search:
        conditions.append("(drug_name LIKE ? OR category LIKE ? OR manufacturer LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query = f"SELECT * FROM drug_inventory WHERE {' AND '.join(conditions)} ORDER BY drug_name"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    result = [dict(zip(columns, row)) for row in rows]
    return jsonify({"count": len(result), "data": result}), 200


@drug_bp.route("/api/drugs", methods=["POST"])
@token_required
def add_drug():
    """添加新药品"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    drug_name = (data.get("drug_name") or "").strip()
    if not drug_name:
        return jsonify({"error": "药品名称不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO drug_inventory (drug_name, category, manufacturer, batch_number, quantity, unit, unit_price, expiry_date, storage_condition, min_stock_level, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                drug_name,
                data.get("category", ""),
                data.get("manufacturer", ""),
                data.get("batch_number", ""),
                int(data.get("quantity", 0)),
                data.get("unit", "瓶"),
                float(data.get("unit_price", 0)),
                data.get("expiry_date") or None,
                data.get("storage_condition", ""),
                int(data.get("min_stock_level", 5)),
                data.get("notes", ""),
            ),
        )
        conn.commit()
        drug_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"添加失败: {str(e)}"}), 500

    cursor.close()
    conn.close()
    return jsonify({"message": "药品添加成功", "drug_id": drug_id}), 201


@drug_bp.route("/api/drugs/<int:drug_id>/stock-in", methods=["POST"])
@token_required
def stock_in(drug_id):
    """药品入库"""
    data = request.get_json(silent=True) or {}
    qty = int(data.get("quantity", 0))
    if qty <= 0:
        return jsonify({"error": "入库数量必须大于0"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM drug_inventory WHERE id = ?", (drug_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该药品"}), 404

    cursor.execute(
        "UPDATE drug_inventory SET quantity = quantity + ? WHERE id = ?",
        (qty, drug_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": f"入库成功，数量 +{qty}"}), 200


@drug_bp.route("/api/drugs/<int:drug_id>/stock-out", methods=["POST"])
@token_required
def stock_out(drug_id):
    """药品出库"""
    data = request.get_json(silent=True) or {}
    qty = int(data.get("quantity", 0))
    if qty <= 0:
        return jsonify({"error": "出库数量必须大于0"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity, drug_name FROM drug_inventory WHERE id = ?", (drug_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该药品"}), 404

    if row[1] < qty:
        cursor.close()
        conn.close()
        return jsonify({"error": f"库存不足，当前库存: {row[1]}"}), 400

    cursor.execute(
        "UPDATE drug_inventory SET quantity = quantity - ? WHERE id = ?",
        (qty, drug_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": f"出库成功，数量 -{qty}"}), 200


@drug_bp.route("/api/drugs/<int:drug_id>", methods=["GET"])
@token_required
def get_drug(drug_id):
    """获取单个药品详情"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drug_inventory WHERE id = ?", (drug_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return jsonify({"error": "药品不存在"}), 404
    return jsonify(dict(row)), 200


@drug_bp.route("/api/drugs/<int:drug_id>", methods=["PUT"])
@token_required
def update_drug(drug_id):
    """更新药品信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM drug_inventory WHERE id = ?", (drug_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该药品"}), 404

    data = request.get_json(silent=True) or {}
    try:
        cursor.execute(
            """UPDATE drug_inventory SET drug_name=?, category=?, manufacturer=?,
               batch_number=?, quantity=?, unit=?, unit_price=?, expiry_date=?,
               storage_condition=?, min_stock_level=?, notes=? WHERE id=?""",
            (
                data.get("drug_name", ""),
                data.get("category", ""),
                data.get("manufacturer", ""),
                data.get("batch_number", ""),
                int(data.get("quantity", 0)),
                data.get("unit", "瓶"),
                float(data.get("unit_price", 0)),
                data.get("expiry_date") or None,
                data.get("storage_condition", ""),
                int(data.get("min_stock_level", 5)),
                data.get("notes", ""),
                drug_id,
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
    return jsonify({"message": "药品信息更新成功"}), 200


@drug_bp.route("/api/drugs/<int:drug_id>", methods=["DELETE"])
@token_required
def delete_drug(drug_id):
    """删除药品"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM drug_inventory WHERE id = ?", (drug_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该药品"}), 404

    cursor.execute("DELETE FROM drug_inventory WHERE id = ?", (drug_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "药品已删除"}), 200
