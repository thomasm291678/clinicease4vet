"""
SOAP 病历 + 临床推理 路由

端点:
  POST   /api/soap/from-transcript      - 对话文本 → AI生成完整SOAP+临床推理
  POST   /api/soap/from-transcript-audio - 上传录音 → 转文字 → 生成SOAP
  GET    /api/soap/<record_id>           - 获取某条记录的SOAP+推理数据
  PUT    /api/soap/<record_id>           - 更新SOAP+推理数据
  POST   /api/soap/<record_id>/reasoning - 单独重新生成临床推理
  POST   /api/soap/<record_id>/client    - 单独重新生成客户沟通
"""

import json
from flask import Blueprint, request, jsonify
from database.db import get_connection
from auth.auth import token_required
from services.clinical_reasoning import (
    generate_soap_from_transcript,
    generate_problem_list,
    generate_clinical_reasoning_path,
    generate_differential_diagnosis,
    generate_missing_info_and_tests,
    generate_client_communication,
    generate_case_summary,
)

soap_bp = Blueprint("soap", __name__)


# ======================== 从对话文本生成完整 SOAP ========================

@soap_bp.route("/api/soap/from-transcript", methods=["POST"])
@token_required
def from_transcript():
    """
    输入医生-主人对话文本 → AI 生成完整 SOAP + 临床推理

    请求: { "transcript": "对话文本...", "species": "狗"/"猫"/... }

    返回:
    {
      "soap": { subjective, objective, assessment, plan },
      "reasoning": { problem_list, reasoning_path, differential_list,
                     must_not_miss, missing_info, recommended_tests,
                     dynamic_questions },
      "client_communication": { observations, concerns, understanding,
                                shared_decision, follow_up },
      "summary": "...",
      "engine": "deepseek"
    }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    transcript = (data.get("transcript") or "").strip()
    if not transcript:
        return jsonify({"error": "请提供对话文本"}), 400

    species = (data.get("species") or "狗").strip()

    try:
        result = generate_soap_from_transcript(transcript, species)
    except Exception as e:
        return jsonify({"error": f"AI 分析失败: {e}"}), 500

    return jsonify(result), 200


# ======================== 从录音上传生成 SOAP ========================

@soap_bp.route("/api/soap/from-transcript-audio", methods=["POST"])
@token_required
def from_transcript_audio():
    """
    上传录音 → 讯飞转文字 → AI 生成完整 SOAP

    请求: multipart/form-data, 字段 "audio", 可选 "species"
    """
    if "audio" not in request.files:
        return jsonify({"error": "请上传音频文件"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "音频文件名为空"}), 400

    try:
        audio_data = audio_file.read()
    except Exception as e:
        return jsonify({"error": f"读取音频失败: {e}"}), 400

    if len(audio_data) == 0:
        return jsonify({"error": "音频数据为空"}), 400

    species = request.form.get("species", "狗").strip()

    try:
        from services.funasr_service import transcribe_audio as funasr_transcribe
        transcript_result = funasr_transcribe(audio_data, audio_file.filename or "recording.webm")
        transcript = transcript_result.get("text", "")
    except Exception as e:
        return jsonify({"error": f"语音转写失败: {e}"}), 500

    if not transcript:
        return jsonify({"error": "未识别到语音内容"}), 400

    # 生成 SOAP
    try:
        result = generate_soap_from_transcript(transcript, species)
        result["transcript"] = transcript
    except Exception as e:
        return jsonify({"error": f"AI 分析失败: {e}", "transcript": transcript}), 500

    return jsonify(result), 200


# ======================== 获取 SOAP 数据 ========================

@soap_bp.route("/api/soap/<int:record_id>", methods=["GET"])
@token_required
def get_soap(record_id):
    """获取某条诊疗记录的 SOAP 数据和临床推理"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM medical_records WHERE id = %s", (record_id,))
    record = cursor.fetchone()
    if not record:
        cursor.close()
        conn.close()
        return jsonify({"error": "记录不存在"}), 404

    columns = [desc[0] for desc in cursor.description]
    record_dict = dict(zip(columns, record))

    # 获取临床推理
    cursor.execute("SELECT * FROM clinical_reasoning WHERE record_id = %s", (record_id,))
    reasoning = cursor.fetchone()
    if reasoning:
        reasoning_cols = [desc[0] for desc in cursor.description]
        reasoning_dict = dict(zip(reasoning_cols, reasoning))

        # 将 JSON 字符串转为对象
        for json_field in ("problem_list", "differential_list", "must_not_miss", "recommended_tests", "client_communication"):
            val = reasoning_dict.get(json_field)
            if isinstance(val, str) and val:
                try:
                    reasoning_dict[json_field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
    else:
        reasoning_dict = None

    cursor.close()
    conn.close()

    soap = {
        "subjective": record_dict.get("subjective") or "",
        "objective": record_dict.get("objective") or "",
        "assessment": record_dict.get("assessment") or record_dict.get("diagnosis") or "",
        "plan": record_dict.get("plan") or "",
    }

    return jsonify({
        "record": record_dict,
        "soap": soap,
        "reasoning": reasoning_dict,
    }), 200


# ======================== 更新 SOAP 数据 ========================

@soap_bp.route("/api/soap/<int:record_id>", methods=["PUT"])
@token_required
def update_soap(record_id):
    """更新 SOAP 字段和临床推理"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM medical_records WHERE id = %s", (record_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "记录不存在"}), 404

    # 更新 SOAP 字段
    cursor.execute(
        """UPDATE medical_records SET subjective=%s, objective=%s,
           assessment=%s, plan=%s WHERE id=%s""",
        (
            data.get("subjective", ""),
            data.get("objective", ""),
            data.get("assessment", ""),
            data.get("plan", ""),
            record_id,
        ),
    )

    # 更新或插入临床推理
    reasoning = data.get("reasoning")
    if reasoning:
        cursor.execute("SELECT id FROM clinical_reasoning WHERE record_id = %s", (record_id,))
        existing = cursor.fetchone()

        def to_json(val):
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)

        if existing:
            cursor.execute(
                """UPDATE clinical_reasoning SET problem_list=%s, reasoning_path=%s,
                   differential_list=%s, must_not_miss=%s, missing_info=%s,
                   recommended_tests=%s, dynamic_questions=%s,
                   client_communication=%s, summary=%s WHERE record_id=%s""",
                (
                    to_json(reasoning.get("problem_list")),
                    reasoning.get("reasoning_path", ""),
                    to_json(reasoning.get("differential_list")),
                    to_json(reasoning.get("must_not_miss")),
                    reasoning.get("missing_info", ""),
                    to_json(reasoning.get("recommended_tests")),
                    reasoning.get("dynamic_questions", ""),
                    to_json(reasoning.get("client_communication")),
                    reasoning.get("summary", ""),
                    record_id,
                ),
            )
        else:
            cursor.execute(
                """INSERT INTO clinical_reasoning (record_id, problem_list, reasoning_path,
                   differential_list, must_not_miss, missing_info, recommended_tests,
                   dynamic_questions, client_communication, summary)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    record_id,
                    to_json(reasoning.get("problem_list")),
                    reasoning.get("reasoning_path", ""),
                    to_json(reasoning.get("differential_list")),
                    to_json(reasoning.get("must_not_miss")),
                    reasoning.get("missing_info", ""),
                    to_json(reasoning.get("recommended_tests")),
                    reasoning.get("dynamic_questions", ""),
                    to_json(reasoning.get("client_communication")),
                    reasoning.get("summary", ""),
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "SOAP 数据更新成功"}), 200


# ======================== 单独重新生成临床推理 ========================

@soap_bp.route("/api/soap/<int:record_id>/reasoning", methods=["POST"])
@token_required
def regenerate_reasoning(record_id):
    """基于当前诊断和症状，重新生成临床推理"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT diagnosis, symptoms, subjective, objective, assessment, plan FROM medical_records WHERE id = %s",
            (record_id,),
        )
        record = cursor.fetchone()
        if not record:
            return jsonify({"error": "记录不存在"}), 404

        columns = [desc[0] for desc in cursor.description]
        rec = dict(zip(columns, record))

        diagnosis = rec.get("diagnosis") or ""
        symptoms = rec.get("symptoms") or ""
        plan = rec.get("plan") or ""
        species = "狗"

        try:
            problem_list = generate_problem_list(symptoms, diagnosis, species)
            reasoning_path = generate_clinical_reasoning_path(symptoms, diagnosis, species)
            diff_result = generate_differential_diagnosis(symptoms, diagnosis, species)
            missing_result = generate_missing_info_and_tests(symptoms, diagnosis, species)
            summary = generate_case_summary(rec, species)
            client_comm = generate_client_communication(diagnosis, plan, species)
        except Exception as e:
            return jsonify({"error": f"推理生成失败: {e}"}), 500

        reasoning_data = {
            "problem_list": problem_list,
            "reasoning_path": reasoning_path,
            "differential_list": diff_result.get("differential_list", []),
            "must_not_miss": diff_result.get("must_not_miss", []),
            "missing_info": missing_result.get("missing_info", ""),
            "recommended_tests": missing_result.get("recommended_tests", []),
            "dynamic_questions": missing_result.get("dynamic_questions", ""),
            "client_communication": client_comm,
            "summary": summary,
        }

        def to_json(val):
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)

        cursor.execute("SELECT id FROM clinical_reasoning WHERE record_id = %s", (record_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """UPDATE clinical_reasoning SET problem_list=%s, reasoning_path=%s,
                   differential_list=%s, must_not_miss=%s, missing_info=%s,
                   recommended_tests=%s, dynamic_questions=%s,
                   client_communication=%s, summary=%s WHERE record_id=%s""",
                (
                    to_json(reasoning_data["problem_list"]),
                    reasoning_data["reasoning_path"],
                    to_json(reasoning_data["differential_list"]),
                    to_json(reasoning_data["must_not_miss"]),
                    reasoning_data["missing_info"],
                    to_json(reasoning_data["recommended_tests"]),
                    reasoning_data["dynamic_questions"],
                    to_json(reasoning_data["client_communication"]),
                    reasoning_data["summary"],
                    record_id,
                ),
            )
        else:
            cursor.execute(
                """INSERT INTO clinical_reasoning (record_id, problem_list, reasoning_path,
                   differential_list, must_not_miss, missing_info, recommended_tests,
                   dynamic_questions, client_communication, summary)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    record_id,
                    to_json(reasoning_data["problem_list"]),
                    reasoning_data["reasoning_path"],
                    to_json(reasoning_data["differential_list"]),
                    to_json(reasoning_data["must_not_miss"]),
                    reasoning_data["missing_info"],
                    to_json(reasoning_data["recommended_tests"]),
                    reasoning_data["dynamic_questions"],
                    to_json(reasoning_data["client_communication"]),
                    reasoning_data["summary"],
                ),
            )

        conn.commit()
        return jsonify({"message": "临床推理已重新生成", "reasoning": reasoning_data}), 200
    except Exception as e:
        return jsonify({"error": f"操作失败: {e}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ======================== 单独重新生成客户沟通 ========================

@soap_bp.route("/api/soap/<int:record_id>/client", methods=["POST"])
@token_required
def regenerate_client_comm(record_id):
    """基于当前诊断和治疗计划，重新生成客户沟通模板"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT diagnosis, plan FROM medical_records WHERE id = %s", (record_id,))
        record = cursor.fetchone()
        if not record:
            return jsonify({"error": "记录不存在"}), 404

        diagnosis = record[0] or ""
        plan = record[1] or ""

        try:
            client_comm = generate_client_communication(diagnosis, plan, "狗")
        except Exception as e:
            return jsonify({"error": f"生成失败: {e}"}), 500

        cursor.execute("SELECT id FROM clinical_reasoning WHERE record_id = %s", (record_id,))
        existing = cursor.fetchone()

        client_json = json.dumps(client_comm, ensure_ascii=False)

        if existing:
            cursor.execute(
                "UPDATE clinical_reasoning SET client_communication=%s WHERE record_id=%s",
                (client_json, record_id),
            )
        else:
            cursor.execute(
                "INSERT INTO clinical_reasoning (record_id, client_communication) VALUES (%s, %s)",
                (record_id, client_json),
            )

        conn.commit()
        return jsonify({"message": "客户沟通已重新生成", "client_communication": client_comm}), 200
    except Exception as e:
        return jsonify({"error": f"操作失败: {e}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
