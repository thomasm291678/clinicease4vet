"""
日历排班路由

端点:
  GET  /api/calendar/events?start=YYYY-MM-DD&end=YYYY-MM-DD  — 获取日期范围内的日程
  POST /api/calendar/events                                   — 创建日程
  PUT  /api/calendar/events/<id>                              — 更新日程
  DELETE /api/calendar/events/<id>                            — 删除日程
  GET  /api/calendar/today                                    — 今日日程
  POST /api/calendar/sync                                     — 手动同步诊疗记录到日历
"""

from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required
from datetime import date, datetime, timedelta

calendar_bp = Blueprint("calendar", __name__)

EVENT_COLORS = {
    "appointment": "#2563eb",
    "surgery": "#dc2626",
    "vaccine": "#16a34a",
    "follow_up": "#f59e0b",
    "checkup": "#8b5cf6",
    "other": "#6b7280",
}


@calendar_bp.route("/api/calendar/events", methods=["GET"])
@token_required
def get_events():
    """获取指定日期范围的日程（含诊疗记录自动同步）"""
    start = request.args.get("start", "")
    end = request.args.get("end", "")

    if not start:
        start = date.today().isoformat()
    if not end:
        end = (date.today() + timedelta(days=30)).isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    # 1. 获取日历事件
    cursor.execute(
        "SELECT * FROM calendar_events WHERE event_date >= %s AND event_date <= %s ORDER BY event_date, start_time",
        (start, end),
    )
    cols = [d[0] for d in cursor.description]
    events = [dict(zip(cols, r)) for r in cursor.fetchall()]

    # 1.5. 清理：删除诊疗记录已不存在或日期已变更的日历事件
    _cleanup_orphaned_events(cursor)
    # 重新获取（清理后可能有变）
    events = _refetch_events(cursor, start, end)

    # 2. 自动同步诊疗记录中还未加入日历的
    cursor.execute(
        """SELECT mr.id, mr.pet_id, mr.visit_date, mr.follow_up_date,
                  mr.diagnosis, mr.vet_name, pd.name as pet_name, pd.owner_name
           FROM medical_records mr
           LEFT JOIN pet_details pd ON mr.pet_id = pd.id
           WHERE (mr.visit_date >= %s AND mr.visit_date <= %s)
              OR (mr.follow_up_date >= %s AND mr.follow_up_date <= %s)""",
        (start, end, start, end),
    )
    med_cols = [d[0] for d in cursor.description]
    med_rows = [dict(zip(med_cols, r)) for r in cursor.fetchall()]

    # 检查哪些诊疗记录还没在日历中（用 (medical_record_id, event_type) 组合判断）
    existing_keys = {(e.get("medical_record_id"), e.get("event_type")) for e in events if e.get("medical_record_id")}

    for mr in med_rows:
        # 就诊日期 → 自动加入日历
        if mr["visit_date"]:
            visit_str = str(mr["visit_date"])
            if start <= visit_str <= end and (mr["id"], "appointment") not in existing_keys:
                evt = _create_event_from_medical(cursor, mr, "visit")
                if evt:
                    events.append(evt)
                    existing_keys.add((mr["id"], "appointment"))

        # 复诊日期 → 自动加入日历
        if mr["follow_up_date"]:
            fu_str = str(mr["follow_up_date"])
            if start <= fu_str <= end and (mr["id"], "follow_up") not in existing_keys:
                evt = _create_event_from_medical(cursor, mr, "follow_up")
                if evt:
                    events.append(evt)
                    existing_keys.add((mr["id"], "follow_up"))

    conn.commit()
    cursor.close()
    conn.close()

    # 按日期和时间排序
    events.sort(key=lambda e: (str(e.get("event_date", "")), str(e.get("start_time", "00:00"))))

    return jsonify({"events": events, "count": len(events), "range": {"start": start, "end": end}}), 200


def _create_event_from_medical(cursor, mr, typ):
    """从诊疗记录创建日历事件"""
    is_follow_up = typ == "follow_up"
    event_date = str(mr["follow_up_date"]) if is_follow_up else str(mr["visit_date"])
    diagnosis = mr.get("diagnosis", "") or ""

    title = f"复诊: {mr.get('pet_name', '未知')}" if is_follow_up else f"就诊: {mr.get('pet_name', '未知')}"
    if diagnosis:
        title += f" ({diagnosis[:15]}{'...' if len(diagnosis) > 15 else ''})"

    event_type = "follow_up" if is_follow_up else "appointment"
    color = EVENT_COLORS.get(event_type, "#2563eb")

    # 检查是否已存在
    cursor.execute(
        "SELECT id FROM calendar_events WHERE medical_record_id = %s AND event_type = %s",
        (mr["id"], event_type),
    )
    if cursor.fetchone():
        return None

    cursor.execute(
        """INSERT INTO calendar_events
           (title, event_date, start_time, end_time, event_type, pet_id, pet_name,
            owner_name, medical_record_id, notes, status, color)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            title,
            event_date,
            "09:00",
            "09:30",
            event_type,
            mr.get("pet_id"),
            mr.get("pet_name", ""),
            mr.get("owner_name", ""),
            mr["id"],
            f"诊断: {diagnosis}" if diagnosis else "",
            "scheduled",
            color,
        ),
    )

    return {
        "id": cursor.lastrowid,
        "title": title,
        "event_date": event_date,
        "start_time": "09:00",
        "end_time": "09:30",
        "event_type": event_type,
        "pet_id": mr.get("pet_id"),
        "pet_name": mr.get("pet_name", ""),
        "owner_name": mr.get("owner_name", ""),
        "medical_record_id": mr["id"],
        "notes": f"诊断: {diagnosis}" if diagnosis else "",
        "status": "scheduled",
        "color": color,
    }


def _cleanup_orphaned_events(cursor):
    """清理失效的日历事件：
    1. 诊疗记录已被删除的 → 删除对应日历事件
    2. 诊疗记录的日期已变更的 → 删除旧日期的事件（下次查询时会重新创建）
    """
    deleted_count = 0

    # 1. 删除 medical_record_id 指向不存在的诊疗记录的事件
    cursor.execute(
        """DELETE FROM calendar_events
           WHERE medical_record_id IS NOT NULL
             AND medical_record_id NOT IN (SELECT id FROM medical_records)"""
    )
    deleted_count += cursor.rowcount

    # 2. 就诊类事件：event_date 与诊疗记录的 visit_date 不一致则删除
    cursor.execute(
        """DELETE FROM calendar_events
           WHERE event_type = 'appointment'
             AND medical_record_id IS NOT NULL
             AND medical_record_id IN (SELECT id FROM medical_records)
             AND event_date != (SELECT visit_date FROM medical_records WHERE id = calendar_events.medical_record_id)"""
    )
    deleted_count += cursor.rowcount

    # 3. 复诊类事件：event_date 与诊疗记录的 follow_up_date 不一致则删除
    cursor.execute(
        """DELETE FROM calendar_events
           WHERE event_type = 'follow_up'
             AND medical_record_id IS NOT NULL
             AND medical_record_id IN (SELECT id FROM medical_records)
             AND event_date != (SELECT follow_up_date FROM medical_records WHERE id = calendar_events.medical_record_id)"""
    )
    deleted_count += cursor.rowcount

    # 4. 复诊类事件：诊疗记录的 follow_up_date 已清空 → 删除
    cursor.execute(
        """DELETE FROM calendar_events
           WHERE event_type = 'follow_up'
             AND medical_record_id IS NOT NULL
             AND medical_record_id IN (
                 SELECT id FROM medical_records WHERE follow_up_date IS NULL
             )"""
    )
    deleted_count += cursor.rowcount

    if deleted_count > 0:
        print(f"[Calendar] 清理了 {deleted_count} 条失效日程")


def _refetch_events(cursor, start, end):
    """重新获取清理后的事件列表"""
    cursor.execute(
        "SELECT * FROM calendar_events WHERE event_date >= %s AND event_date <= %s ORDER BY event_date, start_time",
        (start, end),
    )
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in cursor.fetchall()]


@calendar_bp.route("/api/calendar/events", methods=["POST"])
@token_required
def create_event():
    """创建日历日程"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    title = (data.get("title") or "").strip()
    event_date = (data.get("event_date") or "").strip()
    if not title or not event_date:
        return jsonify({"error": "标题和日期不能为空"}), 400

    start_time = data.get("start_time", "09:00")
    end_time = data.get("end_time", "09:30")
    event_type = data.get("event_type", "appointment")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO calendar_events
           (title, event_date, start_time, end_time, event_type, pet_id, pet_name,
            owner_name, medical_record_id, notes, status, color)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            title,
            event_date,
            start_time,
            end_time,
            event_type,
            data.get("pet_id"),
            (data.get("pet_name") or "").strip(),
            (data.get("owner_name") or "").strip(),
            data.get("medical_record_id"),
            (data.get("notes") or "").strip(),
            data.get("status", "scheduled"),
            data.get("color") or EVENT_COLORS.get(event_type, "#2563eb"),
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM calendar_events WHERE id = %s", (new_id,))
    cols = [d[0] for d in cursor.description]
    evt = dict(zip(cols, cursor.fetchone()))
    cursor.close()
    conn.close()

    return jsonify({"event": evt, "message": "日程已创建"}), 201


@calendar_bp.route("/api/calendar/events/<int:event_id>", methods=["PUT"])
@token_required
def update_event(event_id):
    """更新日历日程"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM calendar_events WHERE id = %s", (event_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "日程不存在"}), 404

    title = data.get("title")
    event_date = data.get("event_date")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    event_type = data.get("event_type")
    status = data.get("status")
    notes = data.get("notes")
    color = data.get("color")

    updates = []
    params = []
    if title is not None:
        updates.append("title = %s")
        params.append(title.strip())
    if event_date is not None:
        updates.append("event_date = %s")
        params.append(event_date.strip())
    if start_time is not None:
        updates.append("start_time = %s")
        params.append(start_time)
    if end_time is not None:
        updates.append("end_time = %s")
        params.append(end_time)
    if event_type is not None:
        updates.append("event_type = %s")
        params.append(event_type)
        if not color:
            color = EVENT_COLORS.get(event_type, "#2563eb")
    if status is not None:
        updates.append("status = %s")
        params.append(status)
    if notes is not None:
        updates.append("notes = %s")
        params.append(notes.strip())
    if color is not None:
        updates.append("color = %s")
        params.append(color)

    if updates:
        params.append(event_id)
        cursor.execute(f"UPDATE calendar_events SET {', '.join(updates)} WHERE id = %s", tuple(params))
        conn.commit()

    cursor.execute("SELECT * FROM calendar_events WHERE id = %s", (event_id,))
    cols = [d[0] for d in cursor.description]
    evt = dict(zip(cols, cursor.fetchone()))
    cursor.close()
    conn.close()

    return jsonify({"event": evt, "message": "日程已更新"}), 200


@calendar_bp.route("/api/calendar/events/<int:event_id>", methods=["DELETE"])
@token_required
def delete_event(event_id):
    """删除日历日程"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM calendar_events WHERE id = %s", (event_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "日程不存在"}), 404

    cursor.execute("DELETE FROM calendar_events WHERE id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "日程已删除"}), 200


@calendar_bp.route("/api/calendar/today", methods=["GET"])
@token_required
def today_schedule():
    """获取今日日程"""
    today_str = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()

    # 获取今日日历事件
    cursor.execute(
        "SELECT * FROM calendar_events WHERE event_date = %s ORDER BY start_time",
        (today_str,),
    )
    cols = [d[0] for d in cursor.description]
    events = [dict(zip(cols, r)) for r in cursor.fetchall()]

    # 获取今日就诊
    cursor.execute(
        """SELECT mr.*, pd.name as pet_name, pd.owner_name
           FROM medical_records mr
           LEFT JOIN pet_details pd ON mr.pet_id = pd.id
           WHERE mr.visit_date = %s OR mr.follow_up_date = %s
           ORDER BY mr.visit_date""",
        (today_str, today_str),
    )
    med_cols = [d[0] for d in cursor.description]
    todays_medical = [dict(zip(med_cols, r)) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return jsonify({
        "date": today_str,
        "events": events,
        "medical_records": todays_medical,
        "total": len(events) + len(todays_medical),
    }), 200


@calendar_bp.route("/api/calendar/sync", methods=["POST"])
@token_required
def force_sync():
    """强制同步：将所有未关联的诊疗记录同步到日历"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT mr.id, mr.pet_id, mr.visit_date, mr.follow_up_date,
                  mr.diagnosis, mr.vet_name, pd.name as pet_name, pd.owner_name
           FROM medical_records mr
           LEFT JOIN pet_details pd ON mr.pet_id = pd.id
           WHERE mr.visit_date IS NOT NULL""",
    )
    med_cols = [d[0] for d in cursor.description]
    med_rows = [dict(zip(med_cols, r)) for r in cursor.fetchall()]

    synced = 0
    for mr in med_rows:
        if mr["visit_date"]:
            r = _create_event_from_medical(cursor, mr, "visit")
            if r:
                synced += 1
        if mr["follow_up_date"]:
            r = _create_event_from_medical(cursor, mr, "follow_up")
            if r:
                synced += 1

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": f"同步完成，新增 {synced} 条日程", "synced_count": synced}), 200
