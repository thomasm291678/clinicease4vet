"""
AI 智能解析引擎 — 纯 DeepSeek LLM 驱动

所有解析功能 100% 依赖 DeepSeek AI，不做本地规则回退。
"""

from services.deepseek_service import get_deepseek


def parse_medical_text_with_llm(text: str) -> dict:
    """
    使用 DeepSeek LLM 将兽医自由文本解析为结构化病历

    返回:
      {
        "pet_info": { pet_name, species, breed, gender, owner_name, owner_contact },
        "diagnosis": { name, confidence, keywords },
        "treatment": { plan, medications, prescription },
        "dates": { visit_date, follow_up_date },
        "vitals": { weight_kg, temperature },
        "fee": { fee_charged },
        "notes": "...",
        "summary": "...",
        "confidence": 0-100,
        "engine": "deepseek"
      }
    """
    if not text or not text.strip():
        return {"error": "输入文本为空", "confidence": 0, "engine": "deepseek"}

    ds = get_deepseek()
    if not ds.is_configured():
        return {
            "error": "DeepSeek API 未配置，请设置 DEEPSEEK_API_KEY",
            "confidence": 0,
            "engine": "deepseek",
        }

    result = ds.parse_medical_text(text.strip())
    if "error" in result:
        return result

    result["engine"] = "deepseek"
    return result
