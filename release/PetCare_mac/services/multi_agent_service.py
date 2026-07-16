"""Multi-Agent 协同诊断服务 — 模拟晓闻科技 Multi-Agent 架构
Orchestrator → 专科Agent并行分析 → Consensus共识 → 综合输出
"""

import json
import time
from services.deepseek_service import get_deepseek
from services.rag_service import get_knowledge_base, rag_is_ready

SPECIALTY_AGENTS = {
    "internal_medicine": {
        "name": "内科Agent",
        "focus": "消化、呼吸、心血管、泌尿、内分泌、血液系统疾病",
        "system_prompt": """你是宠物内科专家Agent。根据病例信息，从内科角度分析：
1. 列出可能的内科疾病（消化/呼吸/心血管/泌尿/内分泌/血液）
2. 分析各系统受累可能性和证据
3. 推荐内科相关检查项目
4. 评估脱水和电解质紊乱风险
请输出JSON格式。""",
    },
    "surgery": {
        "name": "外科Agent",
        "focus": "骨科、软组织外科、神经外科",
        "system_prompt": """你是宠物外科专家Agent。根据病例信息，从外科角度分析：
1. 判断是否需要外科干预（异物、骨折、肿瘤、疝气等）
2. 评估紧急手术指征
3. 推荐影像学检查（X光、B超、CT/MRI适用范围）
4. 评估麻醉风险
请输出JSON格式。""",
    },
    "dermatology": {
        "name": "皮肤科Agent",
        "focus": "皮肤病、耳病、过敏",
        "system_prompt": """你是宠物皮肤科专家Agent。根据病例信息，分析：
1. 皮肤病可能病因（过敏/真菌/细菌/寄生虫/免疫介导/内分泌）
2. 皮肤病与全身性疾病的关系
3. 推荐皮肤科检查（皮肤刮片、细胞学、菌培养、过敏原检测）
请输出JSON格式。""",
    },
    "pharmacology": {
        "name": "药理Agent",
        "focus": "药物选择、剂量、相互作用、禁忌",
        "system_prompt": """你是宠物临床药理专家Agent。根据诊断和治疗方向：
1. 推荐具体药物方案（药物名称、剂量、给药途径、疗程）
2. 检查药物相互作用和禁忌症
3. 评估肝肾毒性风险
4. 推荐监测指标
5. 注意品种特异性禁忌（如柯利犬禁用伊维菌素）
请输出JSON格式。""",
    },
}

ORCHESTRATOR_PROMPT = """你是一位资深兽医全科专家（Orchestrator Agent），负责整合多个专科Agent的分析意见。

## 各专科Agent分析结果：
{agent_outputs}

## 你的任务：
1. 识别各专科意见中的冲突和共识点
2. 综合各专科意见，形成统一的诊断结论
3. 按临床重要性排序问题列表
4. 制定综合治疗计划（兼顾各专科建议）
5. 标注不同诊断的确信度（高/中/低）

## 输出JSON格式：
{{
    "consensus_diagnosis": "综合诊断结论",
    "problem_list": [{{"rank": 1, "problem": "问题", "confidence": "高/中/低", "supporting_agents": ["内科","外科"], "evidence_from": "Agent分析依据"}}],
    "conflicts_resolved": [{{"topic": "冲突主题", "agent_a": "意见A", "agent_b": "意见B", "resolution": "解决方案"}}],
    "treatment_plan": {{
        "emergency": ["紧急处理"],
        "medication": [{{"drug": "药物", "reason": "来自药理Agent"}}],
        "diagnostics": [{{"test": "检查", "priority": "紧急/常规"}}],
        "monitoring": ["监测项目"],
        "follow_up": "随访计划"
    }},
    "referral_recommendation": "是否需要转诊建议",
    "summary": "50字内综合摘要"
}}"""

CONSENSUS_PROMPT = """你是医疗共识专家，负责对多个候选诊断方案进行投票排序。

## 病例信息：
{case_info}

## 候选方案：
{candidates}

## 你的任务：
对每个方案从以下维度打分（1-10分）：
- 诊断合理性：鉴别诊断是否全面且符合临床逻辑
- 循证依据：是否有充分证据支持
- 方案可操作性：治疗计划是否具体可执行
- 安全性：是否考虑了禁忌症和风险
- 完整性：检查计划和随访建议是否充分

输出JSON：
{{"rankings": [{{"candidate_id": 1, "scores": {{"diagnosis": 8, "evidence": 7, "operability": 9, "safety": 8, "completeness": 7}}, "total": 39, "strength": "优势", "weakness": "不足"}}], "best_candidate": 1, "confidence": "高/中/低"}}"""


def _get_rag_context(query: str, max_tokens: int = 2000) -> str:
    if not rag_is_ready("zh"):
        if not rag_is_ready("en"):
            return ""
    try:
        kb = get_knowledge_base("zh")
        if not kb.is_ready:
            kb = get_knowledge_base("en")
        return kb.retrieve_context(query, max_tokens)
    except Exception:
        return ""


def _run_agent(agent_config: dict, case_info: str, species: str) -> dict:
    """运行单个专科Agent"""
    ds = get_deepseek()
    user_message = f"物种: {species}\n\n病例信息:\n{case_info}"
    result_text = ds._chat(agent_config["system_prompt"], user_message, json_mode=True)
    return _safe_parse_json(result_text)


def _safe_parse_json(text: str) -> dict:
    for extractor in [
        lambda t: json.loads(t),
        lambda t: json.loads(t[t.find("{"):t.rfind("}") + 1]) if "{" in t and "}" in t else {},
        lambda t: json.loads("{" + t.split("{", 1)[1].rsplit("}", 1)[0] + "}") if "{" in t and "}" in t else {},
    ]:
        try:
            return extractor(text)
        except (json.JSONDecodeError, ValueError, IndexError):
            continue
    return {"raw_output": text, "parse_error": True}


def multi_agent_diagnosis(case_info: str, species: str = "狗", agents: list = None) -> dict:
    """Multi-Agent 协同诊断 - 核心入口
    
    Args:
        case_info: 病例描述（主诉+体征+检查结果等）
        species: 物种
        agents: 指定激活的Agent列表，默认全部
    
    Returns:
        { consensus, agent_outputs, orchestration, elapsed_seconds }
    """
    if agents is None:
        agents = ["internal_medicine", "surgery", "dermatology", "pharmacology"]

    start_time = time.time()
    agent_outputs = {}
    ds = get_deepseek()

    # Phase 1: 并行运行专科Agent（实际是串行，因为DeepSeek是同步调用）
    for agent_key in agents:
        if agent_key in SPECIALTY_AGENTS:
            agent_outputs[agent_key] = _run_agent(SPECIALTY_AGENTS[agent_key], case_info, species)

    # Phase 2: RAG增强
    rag_ctx = _get_rag_context(case_info)

    # Phase 3: Orchestrator 综合
    agent_summary = ""
    for key, output in agent_outputs.items():
        agent_summary += f"\n### {SPECIALTY_AGENTS[key]['name']}（{SPECIALTY_AGENTS[key]['focus']}）:\n"
        agent_summary += json.dumps(output, ensure_ascii=False, indent=2)
        agent_summary += "\n"

    orch_prompt = ORCHESTRATOR_PROMPT.format(agent_outputs=agent_summary)
    orch_user = f"物种: {species}\n\n原始病例:\n{case_info}\n\n" + (f"RAG知识库参考:\n{rag_ctx}\n\n" if rag_ctx else "")
    orch_result = ds._chat(orch_prompt, orch_user, json_mode=True)
    consensus = _safe_parse_json(orch_result)

    elapsed = round(time.time() - start_time, 1)

    return {
        "consensus": consensus,
        "agent_outputs": {
            key: {"name": SPECIALTY_AGENTS[key]["name"], "focus": SPECIALTY_AGENTS[key]["focus"], "output": output}
            for key, output in agent_outputs.items()
        },
        "rag_enhanced": bool(rag_ctx),
        "elapsed_seconds": elapsed,
        "activated_agents": agents,
    }


def grpo_self_verify(case_info: str, species: str = "狗", n_candidates: int = 3) -> dict:
    """GRPO式自我验证 — 生成多个候选方案，自我排名选出最优
    
    Args:
        case_info: 病例描述
        species: 物种
        n_candidates: 候选方案数量（2-5）
    
    Returns:
        { best_diagnosis, all_candidates, ranking, confidence }
    """
    ds = get_deepseek()
    n_candidates = max(2, min(5, n_candidates))

    # Step 1: 生成多个候选方案
    gen_prompt = f"""你是宠物医疗专家。请对以下病例生成{n_candidates}个不同的诊断和治疗候选方案。
每个方案从不同角度切入（如侧重鉴别诊断、侧重紧急处理、侧重慢性管理等），使方案具有多样性。

病例: {case_info}
物种: {species}

输出JSON:
{{"candidates": [{{"id": 1, "angle": "角度说明", "diagnosis": "诊断", "differential": ["鉴别1","鉴别2"], "treatment": "治疗方案", "tests": ["检查"]}}]}}"""

    candidates_text = ds._chat(gen_prompt, "", json_mode=True)
    candidates_data = _safe_parse_json(candidates_text)

    if not candidates_data.get("candidates"):
        return {
            "best_diagnosis": candidates_data,
            "all_candidates": [],
            "ranking": None,
            "confidence": "未知",
            "note": "候选生成不足"
        }

    # Step 2: 自我排名
    rank_prompt = CONSENSUS_PROMPT.format(
        case_info=f"物种: {species}\n{case_info}",
        candidates=json.dumps(candidates_data["candidates"], ensure_ascii=False, indent=2)
    )

    rank_text = ds._chat(rank_prompt, "", json_mode=True)
    ranking = _safe_parse_json(rank_text)

    # Step 3: 返回最优结果
    best_id = ranking.get("best_candidate", 1) if ranking else 1
    best = next((c for c in candidates_data["candidates"] if c.get("id") == best_id), candidates_data["candidates"][0])

    return {
        "best_diagnosis": best,
        "all_candidates": candidates_data["candidates"],
        "ranking": ranking,
        "confidence": ranking.get("confidence", "未知") if ranking else "未知",
        "method": "GRPO-style self-verification (n=%d)" % n_candidates,
    }


def agent_triage(case_info: str, species: str = "狗") -> dict:
    """智能分诊 — 根据病例自动选择最相关的专科Agent
    
    Returns:
        { recommended_agents, urgency, reasoning }
    """
    ds = get_deepseek()
    prompt = """你是宠物医疗分诊专家。根据病例描述，判断最需要哪些专科Agent参与诊断。

可用专科：内科(消化/呼吸/心血管/泌尿/内分泌)、外科(骨科/软组织/神经)、皮肤科、药理

输出JSON:
{
    "recommended_agents": ["internal_medicine", "surgery"],
    "urgency": "紧急/次紧急/常规",
    "primary_system": "主要受累系统",
    "reasoning": "分诊依据",
    "red_flags": ["危险信号列表"]
}"""

    result = ds._chat(prompt, f"物种: {species}\n\n{case_info}", json_mode=True)
    triage = _safe_parse_json(result)

    return triage
