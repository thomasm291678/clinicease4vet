"""
AI 助手路由：DeepSeek LLM + FunASR 离线语音识别

端点:
  POST /api/ai/transcribe           - 上传音频 → FunASR 离线转文字
  POST /api/ai/transcribe-and-fill  - 音频/文本 → DeepSeek解析 → 预填表单
  POST /api/ai/parse-record         - DeepSeek 解析文本为结构化病历
  POST /api/ai/auto-fill            - 文本 → DeepSeek 解析 → 预填表单
  GET  /api/ai/disease-suggest      - DeepSeek 症状 → 疾病建议
  GET  /api/ai/pet-summary          - 宠物病程汇总
  GET  /api/ai/templates            - 获取模板列表
  GET  /api/ai/templates/<id>       - 获取模板详情
  POST /api/ai/generate-treatment   - DeepSeek 生成治疗方案
  GET  /api/ai/engine-status        - AI 引擎状态
"""

from flask import Blueprint, request, jsonify
from config import Config
from services.ai_parser import parse_medical_text_with_llm
from services.deepseek_service import get_deepseek
from services.funasr_service import transcribe_audio as funasr_transcribe
from database.db import get_connection
from auth.auth import token_required

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/api/ai/transcribe", methods=["POST"])
@token_required
def transcribe_audio_route():
    if "audio" not in request.files:
        return jsonify({"error": "请上传音频文件"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "音频文件名为空"}), 400

    audio_data = audio_file.read()
    if len(audio_data) == 0:
        return jsonify({"error": "音频数据为空"}), 400
    if len(audio_data) > 500 * 1024 * 1024:
        return jsonify({"error": "音频文件过大 (最大 500MB)"}), 413

    try:
        result = funasr_transcribe(audio_data, audio_file.filename or "recording.wav")
    except Exception as e:
        return jsonify({"error": f"语音转写失败: {e}"}), 500

    if result.get("error"):
        return jsonify({"error": result["error"]}), 500

    return jsonify({
        "text": result.get("text", ""),
        "confidence": result.get("confidence", 0),
        "engine": "funasr",
        "elapsed": result.get("elapsed", 0),
        "audio_size": len(audio_data),
    }), 200


@ai_bp.route("/api/ai/transcribe-and-fill", methods=["POST"])
@token_required
def transcribe_and_fill():
    text = ""

    if request.is_json:
        data = request.get_json(silent=True)
        if data:
            text = (data.get("text") or "").strip()
    elif "audio" in request.files:
        audio_file = request.files["audio"]
        if audio_file and audio_file.filename:
            audio_data = audio_file.read()
            if audio_data:
                try:
                    result = funasr_transcribe(audio_data, audio_file.filename or "audio.webm")
                    text = result.get("text", "")
                except Exception as e:
                    return jsonify({"error": f"语音转写失败: {e}"}), 500

    if not text:
        return jsonify({"error": "文本内容不能为空"}), 400

    ds = get_deepseek()
    if not ds.is_configured():
        return jsonify({"error": "DeepSeek API 未配置"}), 503

    auto_fill_result = ds.auto_fill(text)
    if "error" in auto_fill_result:
        return jsonify({"error": auto_fill_result["error"]}), 500

    medical_form = None
    pet_form = None
    vaccine_form = None
    fd = auto_fill_result.get("form_data", {})
    if fd:
        medical_form = {
            "diagnosis": fd.get("diagnosis", ""),
            "treatment": fd.get("treatment", ""),
            "symptoms": fd.get("symptoms", ""),
            "notes": fd.get("notes", ""),
            "visit_date": fd.get("visit_date", ""),
            "follow_up_date": fd.get("follow_up_date"),
            "fee_charged": fd.get("fee_charged", 0),
            "vet_name": fd.get("vet_name", ""),
        }

    vd = auto_fill_result.get("vaccine_data")
    if vd:
        vaccine_form = {
            "vaccine_name": vd.get("vaccine_name", ""),
            "administered_date": vd.get("administered_date", ""),
            "next_due_date": vd.get("next_due_date"),
            "vet_name": vd.get("vet_name", ""),
        }

    parsed_full = ds.parse_medical_text(text)
    if "error" not in parsed_full:
        pi = parsed_full.get("pet_info", {})
        if pi and pi.get("pet_name"):
            pet_form = {
                "name": pi.get("pet_name", ""),
                "species": pi.get("species", ""),
                "breed": pi.get("breed", ""),
                "gender": pi.get("gender", ""),
                "owner_name": pi.get("owner_name", ""),
                "owner_contact": pi.get("owner_contact", ""),
            }

    return jsonify({
        "text": text,
        "pet_form": pet_form,
        "medical_form": medical_form,
        "vaccine_form": vaccine_form,
        "summary": auto_fill_result.get("summary", ""),
        "confidence": auto_fill_result.get("confidence", 0),
        "engine": "deepseek",
    }), 200


@ai_bp.route("/api/ai/parse-record", methods=["POST"])
@token_required
def parse_record():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "文本内容不能为空"}), 400

    result = parse_medical_text_with_llm(text)
    if "error" in result:
        return jsonify(result), 500

    return jsonify({
        "status": "ok",
        "input_length": len(text),
        "result": result,
        "engine": "deepseek",
    }), 200


@ai_bp.route("/api/ai/auto-fill", methods=["POST"])
@token_required
def auto_fill():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    text = (data.get("text") or "").strip()
    pet_id = data.get("pet_id")

    if not text:
        return jsonify({"error": "文本内容不能为空"}), 400

    ds = get_deepseek()
    if not ds.is_configured():
        return jsonify({"error": "DeepSeek API 未配置"}), 503

    result = ds.auto_fill(text, pet_id)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result), 200


@ai_bp.route("/api/ai/disease-suggest", methods=["GET"])
@token_required
def disease_suggest():
    symptoms = request.args.get("symptoms", "").strip()
    if not symptoms:
        return jsonify({"error": "请提供症状关键词，用逗号分隔"}), 400

    ds = get_deepseek()
    if not ds.is_configured():
        return jsonify({"error": "DeepSeek API 未配置"}), 503

    result = ds.suggest_diseases(symptoms)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result), 200


@ai_bp.route("/api/ai/pet-summary", methods=["GET"])
@token_required
def pet_summary():
    pet_id = request.args.get("pet_id", "").strip()
    if not pet_id:
        return jsonify({"error": "请提供 pet_id 参数"}), 400

    try:
        pet_id = int(pet_id)
    except ValueError:
        return jsonify({"error": "pet_id 必须为整数"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pet_details WHERE id = ?", (pet_id,))
    pet_row = cursor.fetchone()
    if not pet_row:
        cursor.close()
        conn.close()
        return jsonify({"error": "未找到该宠物"}), 404

    pet_cols = [desc[0] for desc in cursor.description]
    pet = dict(zip(pet_cols, pet_row))

    cursor.execute(
        "SELECT * FROM medical_records WHERE pet_id = ? ORDER BY visit_date DESC",
        (pet_id,),
    )
    med_rows = cursor.fetchall()
    med_cols = [desc[0] for desc in cursor.description]
    medical = [dict(zip(med_cols, r)) for r in med_rows]

    cursor.execute(
        "SELECT * FROM vaccination_records WHERE pet_id = ? ORDER BY administered_date DESC",
        (pet_id,),
    )
    vacc_rows = cursor.fetchall()
    vacc_cols = [desc[0] for desc in cursor.description]
    vaccines = [dict(zip(vacc_cols, r)) for r in vacc_rows]

    cursor.close()
    conn.close()

    timeline = []
    for m in medical:
        timeline.append({
            "date": str(m.get("visit_date", "")),
            "type": "诊疗",
            "diagnosis": m.get("diagnosis", ""),
            "treatment": m.get("treatment", ""),
            "fee": m.get("fee_charged", 0),
        })
    for v in vaccines:
        timeline.append({
            "date": str(v.get("administered_date", "")),
            "type": "疫苗",
            "vaccine": v.get("vaccine_name", ""),
            "next_due": str(v.get("next_due_date", "")) if v.get("next_due_date") else "",
        })
    timeline.sort(key=lambda x: x["date"])

    summary_text = ""
    ds = get_deepseek()
    if ds.is_configured() and (medical or vaccines):
        records_text = f"宠物: {pet.get('name','')}, 种类: {pet.get('species','')}, 品种: {pet.get('breed','')}\n"
        for t in timeline:
            if t["type"] == "诊疗":
                records_text += f"[{t['date']}] 诊疗 - 诊断: {t['diagnosis']}, 治疗: {t['treatment']}\n"
            else:
                records_text += f"[{t['date']}] 疫苗 - {t['vaccine']}\n"

        result = ds._chat(
            "你是一个兽医AI助手。根据以下宠物就诊记录，生成一段简洁的病程摘要（200字以内），概括主要问题和治疗趋势。",
            records_text,
        )
        if not result.startswith("[API错误]"):
            summary_text = result

    return jsonify({
        "pet_id": pet_id,
        "pet_name": pet.get("name", ""),
        "pet_species": pet.get("species", ""),
        "total_visits": len(medical),
        "total_vaccines": len(vaccines),
        "timeline": timeline,
        "summary": summary_text,
    }), 200


# ======================== 模板 ========================

import json as _json
import os as _os

_TEMPLATES_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "templates")
_INDEX_PATH = _os.path.join(_TEMPLATES_DIR, "index.json")


def _load_templates_index():
    if _os.path.exists(_INDEX_PATH):
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            return _json.load(f)
    return []


@ai_bp.route("/api/ai/templates", methods=["GET"])
@token_required
def get_templates():
    templates = _load_templates_index()
    result = [{"id": t["id"], "name": t["name"], "category": t["category"]} for t in templates]
    return jsonify({"templates": result, "count": len(result)}), 200


@ai_bp.route("/api/ai/templates/<template_id>", methods=["GET"])
@token_required
def get_template_detail(template_id):
    templates = _load_templates_index()
    t = next((x for x in templates if x["id"] == template_id), None)
    if not t:
        return jsonify({"error": "模板不存在"}), 404

    file_path = _os.path.join(_TEMPLATES_DIR, t["file"])
    if not _os.path.exists(file_path):
        return jsonify({"error": "模板文件缺失"}), 404

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return jsonify({"id": t["id"], "name": t["name"], "category": t["category"], "content": content}), 200


# ======================== AI 生成治疗方案 ========================

@ai_bp.route("/api/ai/generate-treatment", methods=["POST"])
@token_required
def generate_treatment():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    symptoms = (data.get("symptoms") or "").strip()
    diagnosis = (data.get("diagnosis") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not symptoms and not diagnosis:
        return jsonify({"error": "请提供症状或诊断信息"}), 400

    ds = get_deepseek()
    if not ds.is_configured():
        return jsonify({"error": "DeepSeek API 未配置"}), 503

    user_msg = f"宠物种类：{species}\n症状/主诉：{symptoms or '未知'}\n诊断：{diagnosis or '待确认'}"
    system_prompt = (
        "你是一个有十年经验的兽医AI助手。根据给出的宠物种类、症状和诊断，"
        "生成一份专业、实用的治疗方案。\n"
        "请严格按照以下格式输出：\n"
        "第一行：治疗原则（简要概括）\n"
        "后续行：具体方案，用换行分隔每个要点\n"
        "包括：药物名称及用法用量、护理措施、饮食建议、复查建议\n"
        "只输出治疗方案，不要输出任何其他内容。"
    )
    result = ds._chat(system_prompt, user_msg)
    if result.startswith("[API错误]"):
        return jsonify({"error": result}), 500

    return jsonify({"treatment": result, "engine": "deepseek"}), 200


@ai_bp.route("/api/ai/engine-status", methods=["GET"])
@token_required
def engine_status():
    ds = get_deepseek()

    kb_status = {"rag_available": False, "rag_stats": {}}
    try:
        from services.rag_service import get_knowledge_base
        kb = get_knowledge_base()
        kb_status["rag_available"] = kb.is_ready
        kb_status["rag_stats"] = kb.get_stats()
    except Exception:
        pass

    funasr_ok = False
    try:
        from services.funasr_service import is_available
        funasr_ok = is_available()
    except Exception:
        pass

    return jsonify({
        "ai_engine": "deepseek",
        "asr_engine": "funasr",
        "deepseek_configured": ds.is_configured(),
        "deepseek_model": Config.DEEPSEEK_MODEL,
        "funasr_available": funasr_ok,
        "features": {
            "multi_agent": True,
            "grpo_self_verify": True,
            "drug_safety_check": True,
            "differential_with_evidence": True,
        },
        **kb_status,
    }), 200


# ======================== RAG 知识库端点 ========================

@ai_bp.route("/api/ai/kb/stats", methods=["GET"])
@token_required
def kb_stats():
    try:
        from services.rag_service import get_knowledge_base
        kb = get_knowledge_base()
        return jsonify(kb.get_stats()), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@ai_bp.route("/api/ai/kb/search", methods=["GET"])
@token_required
def kb_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "请提供查询关键词"}), 400

    top_k = request.args.get("top_k", 5, type=int)

    try:
        from services.rag_service import get_knowledge_base
        kb = get_knowledge_base()

        if not kb.is_ready:
            return jsonify({"error": "知识库尚未构建"}), 503

        if not kb._chunks:
            kb.load()

        results = kb.search(query, top_k=min(top_k, 20))

        tavily_results = None
        if len(results) == 0:
            try:
                from services.tavily_service import search_vet
                tavily_results = search_vet(query, max_results=min(top_k, 10))
            except Exception:
                pass

        return jsonify({
            "query": query,
            "results": results,
            "count": len(results),
            "tavily_fallback": tavily_results,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/kb/chat", methods=["POST"])
@token_required
def kb_chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    question = (data.get("question") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not question:
        return jsonify({"error": "请输入问题"}), 400

    try:
        from services.clinical_reasoning import rag_vet_chat
        answer = rag_vet_chat(question, species)

        from services.tavily_service import search_vet_context
        tavily_ctx = search_vet_context(f"{species} {question}", max_tokens=1500)
        if tavily_ctx and "没有找到相关" in answer:
            ds = get_deepseek()
            if ds.is_configured():
                prompt = f"你是兽医专家。根据联网搜索结果回答问题。\n\n{tavily_ctx}\n\n问题: {question}"
                try:
                    enhanced = ds._chat(prompt, "")
                    if enhanced and not enhanced.startswith("[API错误]"):
                        answer = enhanced
                except Exception:
                    pass

        return jsonify({
            "question": question,
            "species": species,
            "answer": answer,
            "engine": "deepseek_rag",
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/kb/treatment", methods=["POST"])
@token_required
def kb_treatment():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    symptoms = (data.get("symptoms") or "").strip()
    diagnosis = (data.get("diagnosis") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not symptoms and not diagnosis:
        return jsonify({"error": "请提供症状或诊断信息"}), 400

    try:
        from services.clinical_reasoning import generate_treatment_plan_rag
        treatment = generate_treatment_plan_rag(symptoms, diagnosis, species)
        return jsonify({
            "treatment": treatment,
            "engine": "deepseek_rag",
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/kb/soap", methods=["POST"])
@token_required
def kb_soap():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    transcript = (data.get("transcript") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not transcript:
        return jsonify({"error": "请提供对话记录"}), 400

    try:
        from services.clinical_reasoning import generate_soap_from_transcript_rag
        result = generate_soap_from_transcript_rag(transcript, species)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/kb/differential", methods=["POST"])
@token_required
def kb_differential():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    symptoms = (data.get("symptoms") or "").strip()
    diagnosis = (data.get("diagnosis") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not symptoms:
        return jsonify({"error": "请提供症状信息"}), 400

    try:
        from services.clinical_reasoning import generate_differential_diagnosis_rag
        result = generate_differential_diagnosis_rag(symptoms, diagnosis, species)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================
# Multi-Agent + GRPO 增强端点
# ========================

@ai_bp.route("/api/ai/soap/multi-agent", methods=["POST"])
@token_required
def soap_multi_agent():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    transcript = (data.get("transcript") or data.get("text") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not transcript:
        return jsonify({"error": "请提供对话记录或文本"}), 400

    try:
        from services.clinical_reasoning import generate_soap_with_multi_agent
        result = generate_soap_with_multi_agent(transcript, species)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/soap/grpo", methods=["POST"])
@token_required
def soap_grpo():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    transcript = (data.get("transcript") or data.get("text") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not transcript:
        return jsonify({"error": "请提供对话记录或文本"}), 400

    try:
        from services.clinical_reasoning import generate_soap_with_grpo
        result = generate_soap_with_grpo(transcript, species)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/multi-agent/diagnose", methods=["POST"])
@token_required
def multi_agent_diagnose():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    case_info = (data.get("case_info") or data.get("text") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not case_info:
        return jsonify({"error": "请提供病例描述"}), 400

    agents = data.get("agents", ["internal_medicine", "surgery", "dermatology", "pharmacology"])

    try:
        from services.multi_agent_service import multi_agent_diagnosis as ma_diag
        result = ma_diag(case_info, species, agents=agents)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/grpo/verify", methods=["POST"])
@token_required
def grpo_verify():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    case_info = (data.get("case_info") or data.get("text") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not case_info:
        return jsonify({"error": "请提供病例描述"}), 400

    n_candidates = data.get("n_candidates", 3)

    try:
        from services.multi_agent_service import grpo_self_verify
        result = grpo_self_verify(case_info, species, n_candidates=n_candidates)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/drug/safety", methods=["POST"])
@token_required
def drug_safety():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    drug_name = (data.get("drug_name") or "").strip()
    species = (data.get("species") or "狗").strip()
    weight_kg = data.get("weight_kg")

    if not drug_name:
        return jsonify({"error": "请提供药物名称"}), 400

    try:
        from services.clinical_reasoning import drug_safety_check
        result = drug_safety_check(drug_name, species, weight_kg=weight_kg)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/differential/evidence", methods=["POST"])
@token_required
def differential_evidence():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    symptoms = (data.get("symptoms") or "").strip()
    diagnosis = (data.get("diagnosis") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not symptoms:
        return jsonify({"error": "请提供症状信息"}), 400

    try:
        from services.clinical_reasoning import generate_differential_with_evidence
        result = generate_differential_with_evidence(symptoms, diagnosis, species)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/triage", methods=["POST"])
@token_required
def ai_triage():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    case_info = (data.get("case_info") or data.get("text") or "").strip()
    species = (data.get("species") or "狗").strip()

    if not case_info:
        return jsonify({"error": "请提供病例描述"}), 400

    try:
        from services.multi_agent_service import agent_triage
        result = agent_triage(case_info, species)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================
# Tavily 联网兽医搜索
# ========================

@ai_bp.route("/api/ai/vet-search", methods=["POST"])
@token_required
def vet_search():
    """Tavily 联网兽医文献搜索"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    query = (data.get("query") or data.get("q") or "").strip()
    if not query:
        return jsonify({"error": "请提供搜索关键词"}), 400

    max_results = data.get("max_results", 5)

    try:
        from services.tavily_service import search_vet
        result = search_vet(query, max_results=max_results)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_bp.route("/api/ai/vet-search/context", methods=["POST"])
@token_required
def vet_search_context():
    """Tavily 联网搜索 → RAG 上下文拼接"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    query = (data.get("query") or data.get("q") or "").strip()
    if not query:
        return jsonify({"error": "请提供搜索关键词"}), 400

    max_tokens = data.get("max_tokens", 2000)

    try:
        from services.tavily_service import search_vet_context
        context = search_vet_context(query, max_tokens=max_tokens)
        return jsonify({"context": context, "query": query}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
