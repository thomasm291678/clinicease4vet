"""
AI 助手路由：DeepSeek LLM 智能解析 + 科大讯飞语音转文字 + 自动填表

端点:
  POST /api/ai/transcribe      - 上传音频 → 科大讯飞语音转文字
  POST /api/ai/parse-record    - DeepSeek 解析文本为结构化病历
  POST /api/ai/auto-fill       - 一站式：文本 → DeepSeek 解析 → 预填表单
  GET  /api/ai/disease-suggest - DeepSeek 症状 → 疾病建议
  GET  /api/ai/templates       - 获取常用病历模板
  GET  /api/ai/speech-config   - 获取语音服务配置状态
  GET  /api/ai/engine-status   - 获取 AI 引擎状态
"""

from flask import Blueprint, request, jsonify
from config import Config
from services.ai_parser import parse_medical_text_with_llm, DISEASE_PATTERNS
from services.speech_service import IflytekTranscriber
from services.deepseek_service import get_deepseek
from auth.auth import token_required

ai_bp = Blueprint("ai", __name__)


# ======================== 语音转写 ========================

@ai_bp.route("/api/ai/transcribe", methods=["POST"])
@token_required
def transcribe_audio():
    """
    上传音频文件 → 科大讯飞语音转文字

    请求: multipart/form-data, 字段名 "audio"
      支持格式: WAV, PCM (16kHz, 16bit, mono)

    返回: { "text": "转写结果", "engine": "iflytek|google|fallback" }
    """
    if "audio" not in request.files:
        return jsonify({"error": "请上传音频文件 (字段名: audio)"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "音频文件名为空"}), 400

    try:
        audio_data = audio_file.read()
    except Exception as e:
        return jsonify({"error": f"读取音频失败: {e}"}), 400

    if len(audio_data) == 0:
        return jsonify({"error": "音频数据为空"}), 400
    if len(audio_data) > 10 * 1024 * 1024:  # 10MB 限制
        return jsonify({"error": "音频文件过大 (最大 10MB)"}), 413

    transcriber = IflytekTranscriber()

    # 判断引擎类型
    engine = "iflytek" if transcriber.is_configured() else "google"

    try:
        text = transcriber.transcribe(audio_data)
    except Exception as e:
        return jsonify({"error": f"语音转写失败: {e}", "engine": "fallback"}), 500

    # 检测是否回退
    if text.startswith("[回退]") or text.startswith("[错误]"):
        engine = "fallback"

    return jsonify({
        "text": text,
        "engine": engine,
        "audio_size": len(audio_data),
    }), 200


@ai_bp.route("/api/ai/speech-config", methods=["GET"])
@token_required
def speech_config():
    """获取语音服务配置状态"""
    transcriber = IflytekTranscriber()
    return jsonify({
        "iflytek_configured": transcriber.is_configured(),
        "engines_available": ["iflytek"] if transcriber.is_configured() else ["google", "manual"],
        "note": "设置 IFLYTEK_APP_ID / IFLYTEK_API_KEY / IFLYTEK_API_SECRET 环境变量启用科大讯飞",
    }), 200


# ======================== 文本解析 ========================


@ai_bp.route("/api/ai/parse-record", methods=["POST"])
@token_required
def parse_record():
    """
    DeepSeek AI 解析兽医自由文本为结构化病历数据
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "文本内容不能为空"}), 400

    result = parse_medical_text_with_llm(text)

    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "status": "ok",
        "input_length": len(text),
        "result": result,
        "engine": result.get("engine", "unknown"),
    }), 200


@ai_bp.route("/api/ai/auto-fill", methods=["POST"])
@token_required
def auto_fill():
    """
    一站式智能填表：输入文本 → DeepSeek AI 解析 → 返回预填的表单数据
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    text = (data.get("text") or "").strip()
    pet_id = data.get("pet_id")

    if not text:
        return jsonify({"error": "文本内容不能为空"}), 400

    # 优先使用 DeepSeek auto_fill
    try:
        ds = get_deepseek()
        if ds.is_configured():
            result = ds.auto_fill(text, pet_id)
            if "error" not in result:
                return jsonify(result), 200
    except Exception:
        pass

    # 回退规则引擎
    from services.ai_parser import parse_medical_text
    parsed = parse_medical_text(text)
    if "error" in parsed:
        return jsonify(parsed), 400

    form_data = {
        "pet_id": pet_id,
        "vet_name": "",
        "visit_date": parsed["dates"].get("visit_date", ""),
        "diagnosis": parsed["diagnosis"]["name"],
        "treatment": parsed["treatment"]["plan"],
        "notes": parsed.get("notes", ""),
        "follow_up_date": parsed["dates"].get("follow_up_date") or None,
        "fee_charged": parsed["fee"].get("fee_charged", 0),
    }

    vaccine_data = None
    if any(kw in text for kw in ["疫苗", "接种", "免疫", "驱虫", "狂犬", "五联", "猫三联"]):
        vaccine_data = {
            "pet_id": pet_id,
            "vaccine_name": "疫苗",
            "administered_date": parsed["dates"].get("visit_date", ""),
            "next_due_date": parsed["dates"].get("follow_up_date") or None,
            "vet_name": "",
        }

    return jsonify({
        "confidence": parsed["confidence"],
        "summary": parsed["summary"],
        "form_data": form_data,
        "vaccine_data": vaccine_data,
        "engine": "rule_based",
    }), 200


@ai_bp.route("/api/ai/disease-suggest", methods=["GET"])
@token_required
def disease_suggest():
    """
    DeepSeek AI: 根据症状关键词建议可能的疾病
    """
    symptoms = request.args.get("symptoms", "").strip()
    if not symptoms:
        return jsonify({"error": "请提供症状关键词，用逗号分隔"}), 400

    # 优先 DeepSeek
    try:
        ds = get_deepseek()
        if ds.is_configured():
            result = ds.suggest_diseases(symptoms)
            if "error" not in result:
                return jsonify(result), 200
    except Exception:
        pass

    # 回退规则引擎
    symptom_list = [s.strip() for s in symptoms.split(",") if s.strip()]
    suggestions = []
    for disease, keywords in DISEASE_PATTERNS.items():
        matched = [kw for kw in keywords if any(s in kw or kw in s for s in symptom_list)]
        if matched:
            suggestions.append({
                "disease": disease,
                "matched_keywords": matched,
                "match_count": len(matched),
                "confidence": round(min(len(matched) / len(keywords) * 100, 90), 1),
            })
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)

    return jsonify({
        "symptoms": symptom_list,
        "suggestions": suggestions[:5],
        "total_matches": len(suggestions),
        "engine": "rule_based",
    }), 200


@ai_bp.route("/api/ai/templates", methods=["GET"])
@token_required
def get_templates():
    """
    获取常用病历模板，方便快速填写
    """
    templates = [
        {
            "id": "skin",
            "name": "皮肤病模板",
            "category": "皮肤科",
            "content": "主诉：宠物出现{症状}，持续约{天数}天。\n检查：皮肤镜检发现{发现}。\n诊断：{皮肤真菌/细菌/过敏性皮炎}\n治疗：{药品名} {用法用量}，每日{次数}次。\n医嘱：{戴伊丽莎白圈/避免抓挠/保持干燥}\n复诊：{天数}天后复查。",
        },
        {
            "id": "gi",
            "name": "消化系统模板",
            "category": "内科",
            "content": "主诉：{呕吐/腹泻/食欲不振}，持续{天数}天。\n检查：腹部触诊{正常/敏感}，体温{体温}°C。\n诊断：{急性肠胃炎/消化不良/胰腺炎}\n治疗：禁食{小时}小时后，{药品名} {用法用量}。\n医嘱：少量多餐，观察精神状态。\n复诊：{天数}天后复查。",
        },
        {
            "id": "respiratory",
            "name": "呼吸道感染模板",
            "category": "内科",
            "content": "主诉：{咳嗽/打喷嚏/流鼻涕}，{天数}天。\n检查：听诊肺部{正常/有啰音}，体温{体温}°C。\n诊断：{上呼吸道感染/支气管炎/肺炎}\n治疗：{抗生素名} {用法用量}，配合{辅助治疗}。\n医嘱：注意保暖，避免剧烈运动。\n复诊：{天数}天后复查。",
        },
        {
            "id": "vaccine",
            "name": "疫苗接种模板",
            "category": "预防保健",
            "content": "疫苗名称：{狂犬/五联/猫三联}疫苗 第{剂次}剂\n接种日期：{日期}\n批次号：{批次号}\n接种兽医：{兽医名}\n下次接种：{日期}\n备注：接种后观察30分钟无异常。",
        },
        {
            "id": "surgery",
            "name": "手术记录模板",
            "category": "外科",
            "content": "手术名称：{绝育/肿瘤切除/骨折内固定}\n术前诊断：{诊断}\n麻醉方式：{方式}\n手术过程：{描述}\n术后医嘱：{医嘱}\n复诊拆线：{日期}",
        },
        {
            "id": "checkup",
            "name": "常规体检模板",
            "category": "预防保健",
            "content": "体检类型：年度体检\n体重：{体重}kg\n体温：{体温}°C\n体况评分：{评分}/9\n牙齿：{正常/牙结石}\n皮肤：{正常/异常}\n建议：{建议}",
        },
    ]

    return jsonify({"templates": templates, "count": len(templates)}), 200


@ai_bp.route("/api/ai/engine-status", methods=["GET"])
@token_required
def engine_status():
    """获取当前 AI 引擎状态"""
    ds = get_deepseek()
    transcriber = IflytekTranscriber()
    return jsonify({
        "ai_engine": "deepseek" if ds.is_configured() else "rule_based",
        "deepseek_configured": ds.is_configured(),
        "deepseek_model": Config.DEEPSEEK_MODEL,
        "iflytek_configured": transcriber.is_configured(),
        "note": "DeepSeek LLM 优先，规则引擎兜底。无网环境自动降级。",
    }), 200
