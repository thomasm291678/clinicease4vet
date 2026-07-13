"""
AI 智能解析引擎 — 将兽医自然语言描述转换为结构化病历数据

支持：
  1. 自由文本 → 结构化字段提取（诊断、治疗、用药、复诊等）
  2. 宠物名/主人名识别
  3. 常见宠物疾病关键词匹配
  4. 药物名称识别
  5. 日期/费用/体重等数值提取
  6. 置信度评分
"""

import re
from datetime import datetime, timedelta


# ============================================================
# 兽医领域知识库
# ============================================================

# 常见宠物疾病关键词 → 标准诊断名
DISEASE_PATTERNS = {
    # 皮肤类
    "真菌感染": ["真菌", "癣", "脱毛", "皮屑", "圆形脱毛"],
    "细菌性皮炎": ["脓皮", "红疹", "脓疱", "皮肤发红"],
    "过敏性皮炎": ["过敏", "瘙痒", "抓挠", "舔毛", "皮肤红肿"],
    "耳螨感染": ["耳螨", "耳朵痒", "甩头", "耳垢", "耳道"],
    # 消化类
    "肠胃炎": ["呕吐", "腹泻", "拉稀", "肠胃", "不吃东西", "vomiting", "diarrhea", "gastroenteritis"],
    "消化不良": ["消化", "软便", "食欲不振", "没精神", "indigestion"],
    "便秘": ["便秘", "排便困难", "不排便"],
    "胰腺炎": ["胰腺", "腹痛", "弓背", "剧烈呕吐"],
    # 呼吸类
    "上呼吸道感染": ["感冒", "咳嗽", "流鼻涕", "打喷嚏", "鼻塞", "发烧"],
    "支气管炎": ["支气管", "喘息", "呼吸困难", "湿咳"],
    "肺炎": ["肺炎", "高烧", "呼吸急促", "肺部"],
    # 寄生虫
    "体内寄生虫": ["蛔虫", "绦虫", "钩虫", "便血", "消瘦"],
    "体外寄生虫": ["跳蚤", "蜱虫", "虱子", "体外"],
    "心丝虫": ["心丝虫", "心丝"],
    # 骨骼关节
    "关节炎": ["跛行", "关节", "腿瘸", "不愿走动", "僵硬"],
    "骨折": ["骨折", "断腿", "摔伤", "不能站立"],
    # 泌尿
    "尿路感染": ["尿血", "尿频", "排尿困难", "尿闭", "尿路"],
    "膀胱结石": ["结石", "尿结晶", "排尿疼痛"],
    # 眼科
    "结膜炎": ["眼红", "流泪", "眼屎", "眼睛肿", "结膜"],
    "角膜溃疡": ["角膜", "眼睛白斑", "眯眼"],
    # 口腔
    "牙周病": ["口臭", "牙结石", "牙龈", "流口水"],
    "口腔溃疡": ["口腔", "溃疡", "口炎"],
    # 传染病
    "犬瘟热": ["犬瘟", "瘟热", "抽搐", "鼻涕黄绿"],
    "细小病毒": ["细小", "血便", "腥臭", "番茄酱样"],
    "猫瘟": ["猫瘟", "泛白细胞减少"],
    "猫传腹": ["传腹", "腹水", "腹腔积液"],
    # 内分泌
    "糖尿病": ["糖尿病", "多饮多尿", "消瘦", "血糖"],
    "甲状腺功能减退": ["甲减", "脱毛对称", "嗜睡", "肥胖"],
    # 其他
    "中暑": ["中暑", "体温过高", "喘气", "舌头发紫"],
    "中毒": ["中毒", "误食", "呕吐物", "抽搐"],
    "外伤": ["外伤", "伤口", "出血", "咬伤", "划伤"],
    "术后复查": ["术后", "拆线", "复查", "手术"],
    "常规体检": ["体检", "健康检查", "常规", "年度"],
    "疫苗反应": ["疫苗", "接种后", "反应", "精神不好"],
}

# 常用药物识别
MEDICATION_PATTERNS = {
    "阿莫西林": ["阿莫西林", "amoxicillin"],
    "恩诺沙星": ["恩诺沙星", "拜有利", "enrofloxacin"],
    "多西环素": ["多西环素", "强力霉素", "doxycycline"],
    "头孢氨苄": ["头孢", "头孢氨苄", "cephalexin"],
    "甲硝唑": ["甲硝唑", "metronidazole"],
    "泼尼松龙": ["泼尼松", "prednisolone", "激素"],
    "酮康唑": ["酮康唑", "ketoconazole"],
    "伊维菌素": ["伊维菌素", "ivermectin"],
    "芬苯达唑": ["芬苯达唑", "fenbendazole", "驱虫药"],
    "吡喹酮": ["吡喹酮", "praziquantel"],
    "左氧氟沙星": ["左氧氟", "levofloxacin", "可乐必妥"],
    "益生菌": ["益生菌", "probiotic", "肠道"],
    "蒙脱石散": ["蒙脱石", "思密达"],
    "葡萄糖酸钙": ["葡萄糖酸钙", "钙"],
    "维生素B": ["维生素B", "B族", "维B"],
    "消炎药": ["消炎", "抗炎"],
    "抗生素": ["抗生素", "抗菌"],
    "止痛药": ["止痛", "镇痛"],
}

# 治疗措施模式
TREATMENT_PATTERNS = [
    (r"(口服|喂|吃).*?([\u4e00-\u9fff]+(?:素|灵|片|剂|胶囊|颗粒|散|膏|液|水|粉|油|菌))", "口服给药"),
    (r"(注射|打针|输液|挂水|皮下|肌肉|静脉).*?([\u4e00-\u9fff]+(?:素|苗|液|剂))", "注射治疗"),
    (r"(外用|涂抹|擦|喷|滴).*?([\u4e00-\u9fff]+(?:膏|剂|液|水|油|粉))", "外用给药"),
    (r"(清洗|冲洗|清创|消毒|包扎)", "伤口处理"),
    (r"(禁食|禁水|空腹|观察)", "医嘱管理"),
    (r"(驱虫|疫苗|免疫)", "预防保健"),
    (r"(手术|切除|缝合|绝育|去势)", "手术治疗"),
    (r"(住院|留院|观察)", "住院观察"),
]


def extract_pet_info(text: str) -> dict:
    """从文本中提取宠物基础信息"""
    result = {}

    # 提取宠物名（"XX"叫/的XX/名叫XX）
    name_patterns = [
        r"(?:叫|名叫|名字[是为]|宠物|猫|狗|，)\s*([\u4e00-\u9fff]{1,4})\s*(?:[，。,\.!！？?\s]|$)",
        r"([\u4e00-\u9fff]{2,4})\s*(?:猫|狗|兔|鸟|鼠|龟|鱼)",
        r"宠物\s*[:：]?\s*([\u4e00-\u9fff]{2,4})",
    ]
    for pat in name_patterns:
        m = re.search(pat, text)
        if m:
            result["pet_name"] = m.group(1)
            break

    # 提取物种
    species_map = {"狗": "狗", "犬": "狗", "猫": "猫", "兔": "兔", "兔子": "兔",
                   "鸟": "鸟", "鹦鹉": "鸟", "仓鼠": "仓鼠", "鼠": "仓鼠",
                   "乌龟": "龟", "龟": "龟", "鱼": "鱼"}
    for key, val in species_map.items():
        if key in text:
            result["pet_species"] = val
            break

    # 提取品种
    breed_keywords = ["金毛", "拉布拉多", "泰迪", "贵宾", "比熊", "柯基", "柴犬", "哈士奇", "边牧",
                      "英短", "美短", "布偶", "暹罗", "橘猫", "狸花", "加菲", "波斯",
                      "垂耳兔", "荷兰猪", "龙猫"]
    for breed in breed_keywords:
        if breed in text:
            result["pet_breed"] = breed
            break

    # 提取主人
    owner_patterns = [
        r"(?:主人|宠主|家长|主人[是为叫])\s*[:：]?\s*([\u4e00-\u9fff]{2,4})",
        r"(?:主人|家长)\s*([\u4e00-\u9fff]{2,4})",
        r"([\u4e00-\u9fff]{2,4})(?:的|家)[猫狗兔鸟]",
    ]
    for pat in owner_patterns:
        m = re.search(pat, text)
        if m and m.group(1) and ("pet_name" not in result or m.group(1) != result.get("pet_name")):
            result["owner_name"] = m.group(1)
            break

    # 提取性别
    if re.search(r"公|雄性|♂|男孩", text):
        result["pet_gender"] = "公"
    elif re.search(r"母|雌性|♀|女孩", text):
        result["pet_gender"] = "母"

    return result


def extract_diagnosis(text: str) -> dict:
    """从文本中提取诊断信息，返回诊断名 + 置信度"""
    best_diagnosis = ""
    best_confidence = 0
    matched_keywords = []

    for disease, keywords in DISEASE_PATTERNS.items():
        match_count = sum(1 for kw in keywords if kw in text)
        if match_count > 0:
            confidence = min(match_count / len(keywords) * 100, 95)
            if confidence > best_confidence:
                best_diagnosis = disease
                best_confidence = confidence
                matched_keywords = [kw for kw in keywords if kw in text]

    # 如果没有匹配到，尝试提取症状描述作为诊断
    if not best_diagnosis:
        symptoms = []
        symptom_keywords = ["呕吐", "腹泻", "咳嗽", "发烧", "瘙痒", "脱毛", "跛行",
                           "不吃", "精神", "消瘦", "出血", "肿胀", "异常"]
        for kw in symptom_keywords:
            if kw in text:
                symptoms.append(kw)
        if symptoms:
            best_diagnosis = "疑似" + "、".join(symptoms[:3])
            best_confidence = 30

    return {
        "diagnosis": best_diagnosis,
        "confidence": round(best_confidence, 1),
        "matched_keywords": matched_keywords,
    }


def extract_treatment(text: str) -> dict:
    """提取治疗方案"""
    treatments = []
    for pattern, treatment_type in TREATMENT_PATTERNS:
        m = re.search(pattern, text)
        if m:
            treatments.append({
                "type": treatment_type,
                "detail": m.group(0).strip("，。,."),
            })

    result = {
        "treatment_plan": "；".join(t["detail"] for t in treatments) if treatments else "",
        "treatment_items": treatments,
    }

    # 提取药物
    medications = []
    for drug, aliases in MEDICATION_PATTERNS.items():
        for alias in aliases:
            if alias in text.lower():
                # 尝试提取剂量
                dose_pattern = rf"{alias}.*?(\d+(?:\.\d+)?\s*(?:mg|ml|g|片|粒|次|天|日))"
                dose_m = re.search(dose_pattern, text, re.IGNORECASE)
                dose_info = dose_m.group(1) if dose_m else ""
                medications.append({"drug": drug, "dosage": dose_info, "matched": alias})
                break

    result["medications"] = medications
    if medications:
        result["prescription"] = "；".join(
            f"{m['drug']} {m['dosage']}" for m in medications
        )

    return result


def extract_dates(text: str) -> dict:
    """提取日期信息"""
    result = {}

    # 今天日期
    today = datetime.now().strftime("%Y-%m-%d")

    # 提取明确日期 YYYY-MM-DD 或 YYYY/MM/DD
    date_pattern = r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})"
    dates = re.findall(date_pattern, text)
    if dates:
        result["visit_date"] = dates[0].replace("/", "-")

    # "X天后复诊" / "X周后复查"
    follow_patterns = [
        (r"一[周个]后?复[诊查]", "one_week"),
        (r"(\d+)\s*天后?复[诊查]", "days"),
        (r"(\d+)\s*周后?复[诊查]", "weeks"),
        (r"(\d+)\s*天后?再[来去]", "days"),
        (r"(\d+)\s*个月后?复[诊查]", "months"),
        (r"下(?:周|星期)([一二三四五六日天])", "next_week"),
    ]
    for pat, unit in follow_patterns:
        m = re.search(pat, text)
        if m:
            if unit == "one_week":
                result["follow_up_date"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            elif unit == "days":
                result["follow_up_date"] = (datetime.now() + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
            elif unit == "weeks":
                result["follow_up_date"] = (datetime.now() + timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")
            elif unit == "months":
                result["follow_up_date"] = (datetime.now() + timedelta(days=int(m.group(1)) * 30)).strftime("%Y-%m-%d")
            elif unit == "next_week":
                week_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "天": 6, "日": 6}
                days_ahead = (7 + week_map.get(m.group(1), 0) - datetime.now().weekday()) % 7 or 7
                result["follow_up_date"] = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            break

    # 推断就诊日期（如果有"今天"）
    if "今天" in text or "今日" in text:
        result["visit_date"] = today

    return result


def extract_vitals(text: str) -> dict:
    """提取生命体征"""
    result = {}

    # 体重
    weight_pat = r"(\d+(?:\.\d+)?)\s*(?:kg|公斤|千克)"
    m = re.search(weight_pat, text)
    if m:
        result["weight_kg"] = float(m.group(1))

    # 体温
    temp_pat = r"(?:体温|温度)[:：]?\s*(\d{2}(?:\.\d)?)\s*(?:°C|度|摄氏度)?[\s，,。\.]?"
    m = re.search(temp_pat, text)
    if m:
        temp = float(m.group(1))
        if 35 <= temp <= 43:
            result["temperature"] = temp

    return result


def extract_fee(text: str) -> dict:
    """提取费用信息"""
    result = {}
    fee_patterns = [
        r"(?:费用|收费|共计|合计|总共|花费)[:：]?\s*(\d+)\s*(?:元|块)?",
        r"(\d+)\s*(?:元|块钱)(?:左右)?\s*(?:[，。收费])",
    ]
    for pat in fee_patterns:
        m = re.search(pat, text)
        if m:
            result["fee_charged"] = int(m.group(1))
            break
    return result


def parse_medical_text(text: str) -> dict:
    """
    主解析函数：将兽医自由文本解析为结构化病历数据

    返回包含以下字段的字典：
      - pet_info: 宠物基础信息
      - diagnosis: 诊断结果 + 置信度
      - treatment: 治疗方案 + 用药
      - dates: 就诊日期 + 复诊日期
      - vitals: 生命体征（体重/体温）
      - fee: 费用
      - notes: 其他备注
      - confidence: 整体解析置信度
    """
    if not text or not text.strip():
        return {"error": "输入文本为空", "confidence": 0}

    text = text.strip()

    pet_info = extract_pet_info(text)
    diagnosis = extract_diagnosis(text)
    treatment = extract_treatment(text)
    dates = extract_dates(text)
    vitals = extract_vitals(text)
    fee = extract_fee(text)

    # 整体置信度
    confidences = [diagnosis.get("confidence", 0)]
    if treatment.get("medications"):
        confidences.append(70)
    if dates.get("follow_up_date"):
        confidences.append(60)
    overall_confidence = round(sum(confidences) / len(confidences), 1)

    # 自动生成病历摘要
    summary_parts = []
    if diagnosis.get("diagnosis"):
        summary_parts.append(f"诊断：{diagnosis['diagnosis']}")
    if treatment.get("treatment_plan"):
        summary_parts.append(f"治疗：{treatment['treatment_plan']}")
    if dates.get("follow_up_date"):
        summary_parts.append(f"复诊：{dates['follow_up_date']}")
    if fee.get("fee_charged"):
        summary_parts.append(f"费用：{fee['fee_charged']}元")

    # 提取未分类的文本作为备注
    notes = text
    for section in [pet_info, diagnosis, treatment, dates, vitals, fee]:
        for keyword in [v for v in section.values() if isinstance(v, str)]:
            notes = notes.replace(keyword, "")
    notes = re.sub(r"\s+", " ", notes).strip("，。,.")
    notes = notes[:200] if len(notes) > 200 else notes  # 截断过长备注

    return {
        "pet_info": pet_info,
        "diagnosis": {
            "name": diagnosis.get("diagnosis", ""),
            "confidence": diagnosis.get("confidence", 0),
            "keywords": diagnosis.get("matched_keywords", []),
        },
        "treatment": {
            "plan": treatment.get("treatment_plan", ""),
            "items": treatment.get("treatment_items", []),
            "medications": treatment.get("medications", []),
            "prescription": treatment.get("prescription", ""),
        },
        "dates": {
            "visit_date": dates.get("visit_date", ""),
            "follow_up_date": dates.get("follow_up_date", ""),
        },
        "vitals": vitals,
        "fee": fee,
        "notes": notes if notes and len(notes) > 5 else "",
        "summary": "。".join(summary_parts) + "。" if summary_parts else "",
        "confidence": overall_confidence,
        "engine": "rule_based",
    }


def parse_medical_text_with_llm(text: str) -> dict:
    """
    智能解析：优先 DeepSeek LLM → 回退规则引擎

    相同接口，自动选择最优引擎。
    """
    # 先尝试 DeepSeek
    try:
        from services.deepseek_service import get_deepseek
        ds = get_deepseek()
        if ds.is_configured():
            result = ds.parse_medical_text(text)
            if "error" not in result:
                return result
    except Exception:
        pass

    # 回退到规则引擎
    result = parse_medical_text(text)
    result["engine"] = "rule_based"
    return result
