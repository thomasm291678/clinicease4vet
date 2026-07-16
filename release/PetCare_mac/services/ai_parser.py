"""
AI 智能解析引擎 — 本地规则 + DeepSeek LLM 双引擎

本地规则解析: 快速提取结构化字段，无需网络
LLM 解析: 通过 DeepSeek 进行深度语义理解
"""

import re
import datetime
from services.deepseek_service import get_deepseek


BREEDS = [
    "金毛", "泰迪", "柯基", "柴犬", "哈士奇", "拉布拉多", "边牧", "博美", "雪纳瑞",
    "比熊", "萨摩耶", "阿拉斯加", "德牧", "法斗", "巴哥", "贵宾", "吉娃娃", "约克夏",
    "英短", "布偶", "美短", "暹罗", "加菲", "橘猫", "波斯", "缅因",
]

SPECIES_MAP = {
    "狗": ["狗", "犬", "狗狗", "汪"],
    "猫": ["猫", "猫咪", "喵"],
}

GENDER_MAP = {
    "公": ["公", "雄性", "男孩", "弟弟"],
    "母": ["母", "雌性", "女孩", "妹妹"],
}

DIAGNOSIS_DICT = {
    "呕吐": {"disease": "肠胃炎", "confidence": 65, "keywords": ["呕吐", "恶心"]},
    "腹泻": {"disease": "肠胃炎", "confidence": 65, "keywords": ["腹泻", "拉稀"]},
    "呕吐腹泻": {"disease": "肠胃炎", "confidence": 75, "keywords": ["呕吐", "腹泻"]},
    "肠胃炎": {"disease": "肠胃炎", "confidence": 80, "keywords": ["肠胃", "炎症"]},
    "耳螨": {"disease": "耳螨感染", "confidence": 85, "keywords": ["耳螨", "瘙痒", "耳朵"]},
    "耳痒": {"disease": "耳螨感染", "confidence": 70, "keywords": ["耳痒", "抓耳"]},
    "抓耳": {"disease": "耳螨感染", "confidence": 60, "keywords": ["抓耳", "甩头"]},
    "甩头": {"disease": "耳螨感染", "confidence": 55, "keywords": ["甩头", "耳朵"]},
    "真菌": {"disease": "真菌感染", "confidence": 80, "keywords": ["真菌", "癣"]},
    "脱毛": {"disease": "真菌感染", "confidence": 55, "keywords": ["脱毛", "斑块"]},
    "斑块": {"disease": "真菌感染", "confidence": 55, "keywords": ["脱毛", "斑块"]},
    "皮屑": {"disease": "真菌感染", "confidence": 50, "keywords": ["皮屑", "瘙痒"]},
    "感冒": {"disease": "上呼吸道感染", "confidence": 70, "keywords": ["感冒", "咳嗽", "流涕"]},
    "发烧": {"disease": "发热待查", "confidence": 50, "keywords": ["发烧", "体温"]},
    "疫苗": {"disease": "疫苗接种", "confidence": 60, "keywords": ["疫苗", "免疫"]},
    "狂犬": {"disease": "狂犬疫苗接种", "confidence": 70, "keywords": ["狂犬", "疫苗"]},
    "咳嗽": {"disease": "呼吸道感染", "confidence": 55, "keywords": ["咳嗽", "呼吸道"]},
    "不吃": {"disease": "食欲不振", "confidence": 40, "keywords": ["不吃", "食欲"]},
    "精神": {"disease": "精神萎靡", "confidence": 35, "keywords": ["精神", "萎靡"]},
}

DRUG_LIST = ["阿莫西林", "酮康唑", "耳漂洗耳液", "益生菌", "蒙脱石散", "消炎药",
             "恩诺沙星", "多西环素", "驱虫药", "疫苗", "狂犬疫苗", "五联", "六联",
             "三联", "猫三联", "八联", "伊维菌素", "头孢", "甲硝唑"]


def extract_pet_info(text: str) -> dict:
    result = {}

    for species, keywords in SPECIES_MAP.items():
        for kw in keywords:
            if kw in text:
                result["pet_species"] = species
                break
        if "pet_species" in result:
            break

    for breed in sorted(BREEDS, key=len, reverse=True):
        if breed in text:
            result["pet_breed"] = breed
            break

    for gender, keywords in GENDER_MAP.items():
        for kw in keywords:
            if kw in text:
                result["pet_gender"] = gender
                break
        if "pet_gender" in result:
            break

    name_patterns = [
        r'(?:叫|名叫|叫做|名)\s*([\u4e00-\u9fff]{1,3})',
        r'[\u4e00-\u9fff]{1,3}(?:猫|狗|犬)\s*([\u4e00-\u9fff]{1,3})',
        r'([\u4e00-\u9fff]{1,3})\s*(?:是|的|来)',
        r'(?:猫|狗)\s*([\u4e00-\u9fff]{1,3})(?:[。，,\s]|$)',
    ]
    for pat in name_patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1)
            if name not in ("今天", "一只", "这个", "那只", "我家", "那个") and name not in BREEDS:
                result["pet_name"] = name
                break
    if "pet_name" not in result:
        m = re.search(r'[\u4e00-\u9fff]{1,3}的(?:狗|猫|宠物)', text)
        if m:
            owner = m.group(0).rstrip("的狗猫宠物")
            if owner and owner not in BREEDS:
                result["pet_name"] = owner

    owner_match = re.search(r'(?:主人|家长)\s*([\u4e00-\u9fff]{2,4})', text)
    if owner_match:
        result["owner_name"] = owner_match.group(1)

    return result


def extract_diagnosis(text: str) -> dict:
    best = {"diagnosis": "", "confidence": 0, "keywords": []}
    lower = text.lower()
    for keyword, info in sorted(DIAGNOSIS_DICT.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in text:
            score = info["confidence"]
            if score > best["confidence"]:
                best["diagnosis"] = info["disease"]
                best["confidence"] = score
                best["keywords"] = info["keywords"]

    if best["confidence"] < 30:
        if any(c in text for c in ["呕吐", "腹泻", "咳嗽", "发烧"]):
            best["diagnosis"] = "疑似疾病"
            best["confidence"] = 25
            best["keywords"] = []
        elif len(text.strip()) < 5:
            best["confidence"] = max(best["confidence"], 10)
        else:
            best["confidence"] = max(best["confidence"], 15)

    return best


def extract_treatment(text: str) -> dict:
    result = {"medications": [], "treatment_plan": ""}
    for drug in DRUG_LIST:
        if drug in text:
            result["medications"].append({"drug": drug, "dosage": ""})

    plan_patterns = [
        r'(?:治疗|方案)[：:]\s*(.+?)(?:[。，,\n]|$)',
        r'(?:用药|用药方案)[：:]\s*(.+?)(?:[。，,\n]|$)',
    ]
    for pat in plan_patterns:
        m = re.search(pat, text)
        if m:
            result["treatment_plan"] = m.group(1).strip()
            break

    if not result["treatment_plan"] and result["medications"]:
        result["treatment_plan"] = "药物治疗"

    if not result["treatment_plan"]:
        if "注射" in text or "输液" in text:
            result["treatment_plan"] = "注射治疗"

    return result


def extract_dates(text: str) -> dict:
    result = {}
    today_date = datetime.date.today()
    today_str = today_date.isoformat()

    date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
    if date_match:
        result["visit_date"] = date_match.group(1).replace("/", "-")

    if "visit_date" not in result:
        if "今天" in text:
            result["visit_date"] = today_str

    follow_patterns = [
        (r'(\d+)\s*天后?\s*复诊', lambda m: (today_date + datetime.timedelta(days=int(m.group(1)))).isoformat()),
        (r'(\d+)\s*周后?\s*复诊', lambda m: (today_date + datetime.timedelta(weeks=int(m.group(1)))).isoformat()),
        (r'复诊.*?(\d{4}[-/]\d{1,2}[-/]\d{1,2})', lambda m: m.group(1).replace("/", "-")),
    ]
    for pat, fn in follow_patterns:
        m = re.search(pat, text)
        if m:
            result["follow_up_date"] = fn(m)
            break

    if "follow_up_date" not in result:
        if "周后复诊" in text:
            result["follow_up_date"] = (today_date + datetime.timedelta(weeks=1)).isoformat()

    return result


def extract_vitals(text: str) -> dict:
    result = {}

    weight_m = re.search(r'体重\s*(\d+\.?\d*)\s*(?:kg|公斤|千克)', text)
    if weight_m:
        result["weight_kg"] = float(weight_m.group(1))

    temp_m = re.search(r'体温\s*(\d+\.?\d*)\s*(?:度|℃)?', text)
    if temp_m:
        temp_val = float(temp_m.group(1))
        if 30 < temp_val < 45:
            result["temperature"] = temp_val

    return result


def extract_fee(text: str) -> dict:
    result = {}
    fee_m = re.search(r'(?:费用|费)[：:]*\s*(\d+)\s*(?:元)?', text)
    if not fee_m:
        fee_m = re.search(r'(\d+)\s*元\s*(?:[。，,\n]|$)', text)
    if fee_m:
        result["fee_charged"] = int(fee_m.group(1))
    return result


def _calc_confidence(pet: dict, diag: dict, treat: dict, dates: dict, vitals: dict, fee: dict) -> int:
    score = 0
    if pet.get("pet_name"):
        score += 15
    if pet.get("pet_species"):
        score += 10
    if diag.get("diagnosis") and diag.get("confidence", 0) >= 50:
        score += diag["confidence"] // 2
    if treat.get("medications"):
        score += min(len(treat["medications"]) * 10, 20)
    if dates.get("follow_up_date"):
        score += 10
    if fee.get("fee_charged"):
        score += 10
    if vitals:
        score += 10
    score = max(10, min(100, score))
    return score


def _generate_summary(pet: dict, diag: dict, treat: dict, fee: dict) -> str:
    parts = []
    breed = pet.get("pet_breed", "")
    name = pet.get("pet_name", "")
    species = pet.get("pet_species", "")
    if breed and name:
        parts.append(f"{breed}{name}")
    elif name and species:
        parts.append(f"{species}{name}")
    elif name:
        parts.append(name)
    elif breed:
        parts.append(breed)
    elif species:
        parts.append(species)

    if diag.get("diagnosis"):
        parts.append(f"诊断{diag['diagnosis']}")

    if treat.get("medications"):
        drugs = [m["drug"] for m in treat["medications"]]
        parts.append(f"使用{'、'.join(drugs[:3])}")

    if fee.get("fee_charged"):
        parts.append(f"费用{fee['fee_charged']}元")

    return "，".join(parts) + "。" if parts else ""


def parse_medical_text(text: str) -> dict:
    if not text or not text.strip():
        return {"error": "输入文本为空", "confidence": 0}

    text = text.strip()

    pet_info = extract_pet_info(text)
    diagnosis = extract_diagnosis(text)
    treatment = extract_treatment(text)
    dates = extract_dates(text)
    vitals = extract_vitals(text)
    fee = extract_fee(text)

    confidence = _calc_confidence(pet_info, diagnosis, treatment, dates, vitals, fee)
    summary = _generate_summary(pet_info, diagnosis, treatment, fee)

    return {
        "pet_info": {
            "pet_name": pet_info.get("pet_name", ""),
            "pet_species": pet_info.get("pet_species", ""),
            "pet_breed": pet_info.get("pet_breed", ""),
            "pet_gender": pet_info.get("pet_gender", ""),
            "owner_name": pet_info.get("owner_name", ""),
        },
        "diagnosis": {
            "name": diagnosis.get("diagnosis", ""),
            "confidence": diagnosis.get("confidence", 0),
            "keywords": diagnosis.get("keywords", []),
        },
        "treatment": {
            "medications": treatment.get("medications", []),
            "treatment_plan": treatment.get("treatment_plan", ""),
        },
        "dates": {
            "visit_date": dates.get("visit_date", ""),
            "follow_up_date": dates.get("follow_up_date", ""),
        },
        "vitals": {
            "weight_kg": vitals.get("weight_kg", 0),
            "temperature": vitals.get("temperature", 0),
        },
        "fee": {
            "fee_charged": fee.get("fee_charged", 0),
        },
        "confidence": confidence,
        "summary": summary,
    }


# ======================== LLM 解析 ========================

def parse_medical_text_with_llm(text: str) -> dict:
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
