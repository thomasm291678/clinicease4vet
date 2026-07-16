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
  8. Multi-Agent 协同诊断 (新增)
  9. GRPO 自我验证增强 (新增)

所有功能 100% 通过 DeepSeek LLM 生成，不做本地规则回退。
"""

import json
import re
from services.deepseek_service import get_deepseek
from services.rag_service import get_knowledge_base, rag_is_ready
from services.multi_agent_service import (
    multi_agent_diagnosis, grpo_self_verify, agent_triage
)


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
    result_text = ds._chat(system_prompt, f"物种: {species}\n\n对话记录:\n{transcript}", json_mode=True)
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
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n诊断: {diagnosis}", json_mode=True)
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
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n当前诊断: {diagnosis}", json_mode=True)
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
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n诊断: {diagnosis}", json_mode=True)
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
    result = ds._chat(system_prompt, f"物种: {species}\n诊断: {diagnosis}\n治疗计划: {plan}", json_mode=True)
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError("DeepSeek 返回格式异常")


# ======================== RAG 知识增强版本 ========================

def _rag_context(query: str, lang: str = "en") -> str:
    """从知识库检索相关专业知识上下文"""
    try:
        from services.rag_service import get_knowledge_base
        kb = get_knowledge_base(lang)
        if kb.is_ready:
            if not kb._chunks:
                kb.load()
            return kb.retrieve_context(query, max_tokens=3000)
    except Exception:
        pass
    return ""


def generate_soap_from_transcript_rag(transcript: str, species: str = "狗") -> dict:
    """RAG增强版: 从对话文本生成完整 SOAP 病历 + 临床推理，自动检索专业知识"""
    context = _rag_context(f"{species} {transcript[:500]}")

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

    if context:
        system_prompt += f"""

=== 以下是从兽医专业文献中检索到的相关知识，请参考这些知识来增强你的诊断分析 ===

{context}

=== 知识参考结束 ===

请在上述专业知识的基础上进行分析，但最终的SOAP记录必须基于对话中的实际信息。"""

    ds = get_deepseek()
    result_text = ds._chat(system_prompt, f"物种: {species}\n\n对话记录:\n{transcript}", json_mode=True)
    if result_text.startswith("[API错误]"):
        raise RuntimeError(result_text)

    parsed = _extract_json(result_text)
    if not parsed:
        raise RuntimeError("DeepSeek 返回格式异常，无法解析 JSON")

    parsed["engine"] = "deepseek"
    parsed["rag_enhanced"] = bool(context)
    return parsed


def generate_differential_diagnosis_rag(symptoms: str, diagnosis: str, species: str = "狗") -> dict:
    """RAG增强版: 生成鉴别诊断，自动检索相关专业知识"""
    context = _rag_context(f"{species} {symptoms} {diagnosis}")

    system_prompt = """你是兽医专家。根据症状和当前诊断生成鉴别诊断列表。
输出纯JSON格式：
{"differential_list": [{"rank": 1, "disease": "病名", "probability": "高/中/低", "rationale": "理由"}], "must_not_miss": ["必须排除的严重疾病1"]}
至少3个鉴别诊断，至少2个 must_not_miss。只输出JSON。"""

    if context:
        system_prompt += f"\n\n=== 专业知识参考 ===\n{context}\n=== 参考结束 ==="

    ds = get_deepseek()
    result = ds._chat(system_prompt, f"物种: {species}\n症状: {symptoms}\n当前诊断: {diagnosis}", json_mode=True)
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        parsed["rag_enhanced"] = bool(context)
        return parsed
    raise RuntimeError("DeepSeek 返回格式异常")


def generate_treatment_plan_rag(symptoms: str, diagnosis: str, species: str = "狗") -> str:
    """RAG增强版: 生成治疗方案，参考专业知识库"""
    context = _rag_context(f"{species} {symptoms} {diagnosis} 治疗方案")

    system_prompt = (
        "你是一个有十年经验的兽医AI助手。根据给出的宠物种类、症状和诊断，"
        "生成一份专业、实用的治疗方案。\n"
        "请严格按照以下格式输出：\n"
        "第一行：治疗原则（简要概括）\n"
        "后续行：具体方案，用换行分隔每个要点\n"
        "包括：药物名称及用法用量（需说明剂量依据）、护理措施、饮食建议、复查建议\n"
        "只输出治疗方案，不要输出任何其他内容。"
    )

    if context:
        system_prompt += f"\n\n=== 专业知识参考（请参照文献中的标准疗法） ===\n{context}\n=== 参考结束 ==="

    ds = get_deepseek()
    user_msg = f"宠物种类：{species}\n症状/主诉：{symptoms or '未知'}\n诊断：{diagnosis or '待确认'}"
    result = ds._chat(system_prompt, user_msg)
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    return result.strip()


def rag_vet_chat(question: str, species: str = "狗") -> str:
    """通用兽医知识问答，自动检索专业知识库"""
    context = _rag_context(f"{species} {question}")

    system_prompt = (
        "你是一位经验丰富的兽医专家。请用专业但易懂的语言回答以下兽医相关问题。"
    )

    if context:
        system_prompt += (
            "\n\n=== 以下是从兽医专业文献中检索到的相关知识 ===\n"
            f"{context}\n"
            "=== 知识参考结束 ===\n\n"
            "请基于以上专业知识回答问题，并在回答末尾标注引用的文献页码。"
            "如果检索到的知识与问题不直接相关，请如实说明并基于你的专业知识回答。"
        )

    ds = get_deepseek()
    user_msg = f"宠物种类: {species}\n问题: {question}"
    result = ds._chat(system_prompt, user_msg)
    if result.startswith("[API错误]"):
        raise RuntimeError(result)
    return result.strip()


# ============================================================
# 8. Multi-Agent 协同诊断 (晓闻科技架构)
# ============================================================

def generate_soap_with_multi_agent(transcript: str, species: str = "狗") -> dict:
    """Multi-Agent 协同生成 SOAP + 临床推理
    
    先用传统方式生成 SOAP，再用 Multi-Agent 做深度推理验证。
    如果 Multi-Agent 发现重要补充，会标注 conflict_resolution 字段。
    """
    from services.clinical_reasoning import generate_soap_from_transcript as _base_soap

    base_result = _base_soap(transcript, species)

    case_info = (
        f"主诉: {base_result['soap'].get('subjective', '')}\n"
        f"检查发现: {base_result['soap'].get('objective', '')}\n"
        f"初步评估: {base_result['soap'].get('assessment', '')}"
    )

    triage = agent_triage(case_info, species)
    recommended_agents = triage.get("recommended_agents", ["internal_medicine", "pharmacology"])

    ma_result = multi_agent_diagnosis(case_info, species, agents=recommended_agents)

    enhanced_reasoning = base_result.get("reasoning", {})
    if ma_result.get("consensus", {}).get("problem_list"):
        merged_problems = base_result.get("reasoning", {}).get("problem_list", [])
        ma_problems = ma_result["consensus"].get("problem_list", [])
        merged_problems.extend(ma_problems)
        enhanced_reasoning["problem_list"] = merged_problems
        enhanced_reasoning["multi_agent_enhanced"] = True

    if ma_result["consensus"].get("treatment_plan", {}).get("medication"):
        enhanced_reasoning["recommended_medication"] = ma_result["consensus"]["treatment_plan"]["medication"]

    if ma_result["consensus"].get("conflicts_resolved"):
        enhanced_reasoning["agent_conflicts"] = ma_result["consensus"]["conflicts_resolved"]

    return {
        "soap": base_result["soap"],
        "reasoning": enhanced_reasoning,
        "client_communication": base_result["client_communication"],
        "summary": base_result.get("summary", ""),
        "engine": "deepseek",
        "multi_agent": {
            "triage": triage,
            "consensus": ma_result["consensus"],
            "agents_activated": recommended_agents,
            "elapsed_seconds": ma_result["elapsed_seconds"],
        },
    }


def generate_soap_with_grpo(transcript: str, species: str = "狗") -> dict:
    """GRPO 自我验证增强版 SOAP 生成
    
    1. 传统方式生成 SOAP
    2. GRPO 生成多个候选问题清单和鉴别诊断
    3. 自我排名选出最优
    4. 合并最优候选到最终结果
    """
    from services.clinical_reasoning import generate_soap_from_transcript as _base_soap

    base_result = _base_soap(transcript, species)

    case_info = (
        f"主诉: {base_result['soap'].get('subjective', '')}\n"
        f"体征: {base_result['soap'].get('objective', '')}\n"
        f"评估: {base_result['soap'].get('assessment', '')}"
    )

    grpo = grpo_self_verify(case_info, species, n_candidates=3)

    enhanced_reasoning = base_result.get("reasoning", {})
    if grpo.get("best_diagnosis"):
        best = grpo["best_diagnosis"]
        if best.get("differential"):
            enhanced_reasoning["differential_list_grpo"] = best["differential"]
        if best.get("diagnosis"):
            enhanced_reasoning["grpo_consensus_diagnosis"] = best["diagnosis"]
        enhanced_reasoning["grpo_enhanced"] = True
        enhanced_reasoning["grpo_confidence"] = grpo.get("confidence", "未知")
        enhanced_reasoning["grpo_candidates_count"] = len(grpo.get("all_candidates", []))

    return {
        "soap": base_result["soap"],
        "reasoning": enhanced_reasoning,
        "client_communication": base_result["client_communication"],
        "summary": base_result.get("summary", ""),
        "engine": "deepseek",
        "grpo": {
            "best_diagnosis": grpo.get("best_diagnosis"),
            "ranking": grpo.get("ranking"),
            "confidence": grpo.get("confidence"),
            "method": grpo.get("method"),
        },
    }


# ============================================================
# 9. 增强 Prompt — 证据引用 + 知识图谱感知
# ============================================================

def generate_differential_with_evidence(symptoms: str, diagnosis: str, species: str = "狗") -> dict:
    """增强版鉴别诊断 — 要求关联证据和文献页码
    
    与 generate_differential_diagnosis 的区别：
    - 每个鉴别诊断必须关联具体证据
    - 从 RAG 知识库引用文献来源
    - 增加置信度评分
    """
    context = _rag_context(f"{species} {symptoms} {diagnosis}")

    system_prompt = (
        "你是宠物医疗专家。根据症状和初步诊断，生成鉴别诊断列表。\n"
        "每个鉴别诊断必须包含：疾病名、概率（高/中/低）、\n"
        "支持证据（具体临床表现或检查结果）、反对证据、\n"
        "排除方法（需要做什么检查来排除该疾病）。\n\n"
        "按概率从高到低排列，至少列出3个，最多7个。\n"
        "必须包含至少1个 Must Not Miss（不可遗漏的严重疾病）。\n\n"
        "输出JSON: {\"differential_list\": [...], \"must_not_miss\": [...], "
        "\"confidence_summary\": \"总体置信度评估\"}"
    )

    if context:
        system_prompt += f"\n\n=== 专业知识参考 ===\n{context}\n=== 参考结束 ==="

    ds = get_deepseek()
    user_msg = f"物种: {species}\n症状: {symptoms}\n初步诊断: {diagnosis}"
    result_text = ds._chat(system_prompt, user_msg, json_mode=True)
    return _extract_json(result_text)


def drug_safety_check(drug_name: str, species: str = "狗", weight_kg: float = None) -> dict:
    """药物安全检查 — 基于 RAG 知识库的药物信息查询
    
    返回：剂量范围、禁忌症、品种特异性警告、药物相互作用
    """
    query = f"{species} {drug_name} 剂量 禁忌 副作用"
    context = _rag_context(query, max_tokens=3000)

    system_prompt = (
        "你是宠物临床药理专家。请根据专业知识（及提供的参考文献），"
        "分析以下药物的安全性信息。\n\n"
        "请输出JSON格式：\n"
        "{\n"
        "  \"drug_name\": \"药物名\",\n"
        "  \"species\": \"物种\",\n"
        '  "dosage_range": "剂量范围（如适用）",\n'
        '  "contraindications": ["禁忌1", "禁忌2"],\n'
        '  "breed_specific_warnings": ["品种警告"],\n'
        '  "drug_interactions": ["相互作用1"],\n'
        '  "side_effects": ["副作用1"],\n'
        '  "monitoring": ["监测指标"],\n'
        '  "references": ["文献引用"]\n'
        "}"
    )

    if context:
        system_prompt += f"\n\n=== 参考文献 ===\n{context}\n=== 参考结束 ==="

    ds = get_deepseek()
    weight_info = f"，体重{weight_kg}kg" if weight_kg else ""
    user_msg = f"物种: {species}{weight_info}\n查询药物: {drug_name}"
    result_text = ds._chat(system_prompt, user_msg, json_mode=True)
    return _extract_json(result_text)
