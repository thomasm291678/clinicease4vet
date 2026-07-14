"""
临床推理引擎 — 纯 DeepSeek LLM 驱动

功能:
  1. 对话 → 完整 SOAP + 临床推理
  2. 问题清单生成 (Problem List)
  3. 鉴别诊断 (Differential List + Must Not Miss)
  4. 临床推理路径 (Reasoning Path)
  5. Missing Info / 推荐检查 / 动态问诊
  6. 客户沟通模板
  7. 病例摘要

所有功能 100% 通过 DeepSeek LLM 生成，不做本地规则回退。
"""

import json
import re
from services.deepseek_service import get_deepseek


def _extract_json(text: str):
    """从文本中提取 JSON 对象或数组"""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ======================== SOAP 生成 ========================

def generate_soap_from_transcript(transcript: str, species: str = "狗") -> dict:
    """
    从对话文本生成完整 SOAP 病历 + 临床推理

    返回:
      { soap: {}, reasoning: {}, client_communication: {}, summary: "", engine: "deepseek" }
    """
    system_prompt = """你是一位具有十年临床经验的兽医专家，精通SOAP病历书写和临床推理。
请根据以下医生与宠物主人的对话记录，生成完整的SOAP病历和临床推理分析。
请严格按照以下JSON格式输出，不要输出任何其他内容：

{
  "soap": {
    "subjective": "主观信息——包括主诉、病程、呕吐频率/内容、食欲、饮水、精神状态、排便、可能误食史、用药史、疫苗驱虫情况等。按项目列表输出，未知项标注Unknown。",
    "objective": "客观检查——体温、心率、呼吸、黏膜颜色、CRT、水合状态、腹部触诊、听诊、体重、BCS等。未检查项标注Not Performed/Not Measured。",
    "assessment": "评估——列出所有临床问题和判断，每个问题一行，按重要性排序。",
    "plan": "计划——分为诊断计划、治疗计划、家庭护理建议，每个部分用列表。"
  },
  "reasoning": {
    "problem_list": [{"rank": 1, "problem": "问题名", "evidence_for": "支持证据", "evidence_against": "反对证据"}],
    "reasoning_path": "急性呕吐 → 主要受累系统: 胃肠道 → 解剖部位: 胃/近端小肠 → 可能病变类型: 炎性/机械性 → 鉴别诊断",
    "differential_list": [{"rank": 1, "disease": "疾病名", "probability": "高/中/低", "rationale": "理由"}],
    "must_not_miss": ["必须排除的严重疾病1", "疾病2"],
    "missing_info": "需要进一步获取的信息列表，每项一行",
    "recommended_tests": [{"test": "检查名", "rationale": "推荐理由"}],
    "dynamic_questions": "针对当前情况，建议接下来询问的问题列表"
  },
  "client_communication": {
    "observations": "主人观察到的情况总结",
    "concerns": "主人的主要关切和问题",
    "understanding": "主人当前理解程度",
    "shared_decision": "共同决策内容和同意方案",
    "follow_up": "随访计划"
  },
  "summary": "一段话病例总结（包含物种、年龄、主诉、关键发现、诊断和治疗计划）"
}

规则：
- 所有信息必须从对话中提取，不能编造
- 未知或未提及的信息标注 Unknown / Not Performed
- 诊断使用标准兽医术语
- problem_list 按临床重要性降序排列，至少3个"""

    ds = get_deepseek()
    result_text = ds._chat(system_prompt, f"物种: {species}\n\n对话记录:\n{transcript}")
    if result_text.startswith("[API错误]"):
        raise RuntimeError(result_text)

    parsed = _extract_json(result_text)
    if not parsed:
        raise RuntimeError("DeepSeek 返回格式异常，无法解析 JSON")

    parsed["engine"] = "deepseek"
    return parsed


# ======================== 单功能生成 ========================

def generate_problem_list(symptoms: str, diagnosis: str, species: str = "狗") -> list:
    """生成问题清单"""
    system_prompt = """你是兽医专家。根据症状和诊断生成问题清单，按临床重要性降序排列。
输出纯JSON数组，每个元素包含: rank(序号), problem(问题名), evidence_for(支持证据), evidence_against(反对证据)。
至少3个问题，最多7个。只输出JSON数组。"""
    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n诊断: {diagnosis}")
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    parsed = _extract_json(result)
    if isinstance(parsed, list):
        return parsed
    raise RuntimeError("DeepSeek 返回格式异常")


def generate_differential_diagnosis(symptoms: str, diagnosis: str, species: str = "狗") -> dict:
    """生成鉴别诊断"""
    system_prompt = """你是兽医专家。根据症状和当前诊断生成鉴别诊断列表。
输出纯JSON格式：
{"differential_list": [{"rank": 1, "disease": "病名", "probability": "高/中/低", "rationale": "理由"}], "must_not_miss": ["必须排除的严重疾病1"]}
至少3个鉴别诊断，至少2个 must_not_miss。只输出JSON。"""
    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n当前诊断: {diagnosis}")
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError("DeepSeek 返回格式异常")


def generate_clinical_reasoning_path(symptoms: str, diagnosis: str, species: str = "狗") -> str:
    """生成临床推理路径文本"""
    system_prompt = """你是兽医专家。根据症状和诊断，生成简短清晰的临床推理路径。
格式要求：从主诉开始 → 主要受累系统 → 解剖定位 → 可能病变类型 → 鉴别诊断方向。
3-5句话即可，不要超过150字。只输出文本。"""
    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n诊断: {diagnosis}")
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    return result.strip()


def generate_missing_info_and_tests(symptoms: str, diagnosis: str, species: str = "狗") -> dict:
    """生成 Missing Info + 推荐检查 + 动态问诊"""
    system_prompt = """你是兽医专家。根据当前症状和诊断，输出以下三项内容。
输出纯JSON格式：
{"missing_info": "还需要获取哪些信息，列表形式", "recommended_tests": [{"test": "检查名称", "rationale": "推荐理由"}], "dynamic_questions": "建议询问的问题"}
只输出JSON。"""
    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n诊断: {diagnosis}")
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError("DeepSeek 返回格式异常")


def generate_case_summary(soap_data: dict, species: str) -> str:
    """生成一段话病例摘要"""
    system_prompt = """你是兽医专家。根据SOAP信息生成一段话病例摘要（50-100字）。
包含：物种、主诉、关键发现、诊断、治疗计划。只输出摘要文本。"""
    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\nSOAP数据: {json.dumps(soap_data, ensure_ascii=False)}")
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    return result.strip()


def generate_client_communication(diagnosis: str, plan: str, species: str = "狗") -> dict:
    """生成客户沟通模板"""
    system_prompt = """你是兽医专家。根据诊断和治疗计划，生成客户沟通模板。
输出纯JSON格式：
{"observations": "主人可能观察到的症状", "concerns": "主人担心的问题", "understanding": "宜说明的要点", "shared_decision": "需共同决定的选项", "follow_up": "随访计划"}
每个字段用一句话即可。只输出JSON。"""
    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\n诊断: {diagnosis}\n治疗计划: {plan}")
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError("DeepSeek 返回格式异常")
