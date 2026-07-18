"""
DeepSeek AI 服务 — 基于 DeepSeek Chat API 的智能诊疗引擎

功能:
  1. 病历文本解析 (自由文本 → 结构化 JSON)
  2. 症状 → 疾病建议
  3. 通用 AI 对话

API: https://api.deepseek.com/v1/chat/completions
模型: deepseek-chat
"""

import json
from config import Config


class DeepSeekAI:
    """DeepSeek AI 客户端"""

    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.base_url = Config.DEEPSEEK_BASE_URL
        self.model = Config.DEEPSEEK_MODEL
        self.max_tokens = Config.DEEPSEEK_MAX_TOKENS
        self.temperature = Config.DEEPSEEK_TEMPERATURE

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "")

    def _chat(self, system_prompt: str, user_message: str, json_mode: bool = False) -> str:
        """调用 DeepSeek Chat API"""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
                return f"[API错误] {error}"
        except requests.ConnectionError:
            return "[API错误] 无法连接到 DeepSeek 服务"
        except requests.Timeout:
            return "[API错误] DeepSeek 请求超时"
        except Exception as e:
            return f"[API错误] {e}"

    # ======================== 病历解析 ========================

    def parse_medical_text(self, text: str) -> dict:
        """
        使用 DeepSeek 将自由文本解析为结构化病历

        返回:
          {
            "pet_info": { pet_name, species, breed, gender, owner_name },
            "diagnosis": { name, confidence, keywords },
            "treatment": { plan, medications: [{drug, dosage}], prescription },
            "dates": { visit_date, follow_up_date },
            "vitals": { weight_kg, temperature },
            "fee": { fee_charged },
            "notes": "...",
            "summary": "...",
            "confidence": 0-100,
            "engine": "deepseek"
          }
        """
        system_prompt = """你是一个专业的兽医AI助手。你的任务是将兽医口述/书写的自由文本解析为结构化的JSON病历数据。

请严格按照以下JSON格式输出，不要输出任何其他内容：

{
  "pet_info": {
    "pet_name": "宠物名",
    "species": "狗/猫/兔/鸟/其他",
    "breed": "品种",
    "gender": "公/母/未知",
    "owner_name": "主人姓名",
    "owner_contact": "联系方式"
  },
  "diagnosis": {
    "name": "标准诊断名",
    "confidence": 0-100的整数,
    "keywords": ["匹配的关键词"]
  },
  "treatment": {
    "plan": "治疗方案描述",
    "medications": [{"drug": "药名", "dosage": "用法用量"}],
    "prescription": "处方汇总"
  },
  "dates": {
    "visit_date": "YYYY-MM-DD格式就诊日期",
    "follow_up_date": "YYYY-MM-DD格式复诊日期"
  },
  "vitals": {
    "weight_kg": 数字,
    "temperature": 数字
  },
  "fee": {
    "fee_charged": 数字
  },
  "notes": "备注补充信息",
  "summary": "一句话病历摘要"
}

规则：
- 如果某个字段无法从文本中提取，填写空字符串""或0
- 诊断名使用标准兽医术语
- 日期格式必须是YYYY-MM-DD
- 费用和体重必须是数字
- 置信度根据提取信息的完整度评分(0-100)
- 如果文本描述与宠物医疗无关，confidence设置为0"""

        result = self._chat(system_prompt, f"请解析以下兽医病历文本:\n\n{text}")

        if result.startswith("[API错误]"):
            return {"error": result, "confidence": 0, "engine": "deepseek"}

        # 解析 JSON 响应
        parsed = self._extract_json(result)

        if parsed is None:
            return {
                "error": "DeepSeek 返回格式异常",
                "raw_response": result[:500],
                "confidence": 0,
                "engine": "deepseek",
            }

        parsed["engine"] = "deepseek"
        return parsed

    def auto_fill(self, text: str, pet_id: int = None) -> dict:
        """
        一站式：解析文本 → 返回可直接提交的表单数据
        """
        parsed = self.parse_medical_text(text)

        if "error" in parsed:
            return {"error": parsed["error"], "confidence": 0}

        form_data = {
            "pet_id": pet_id,
            "vet_name": "",
            "visit_date": parsed["dates"].get("visit_date", ""),
            "diagnosis": parsed["diagnosis"].get("name", ""),
            "treatment": parsed["treatment"].get("plan", ""),
            "notes": parsed.get("notes", ""),
            "follow_up_date": parsed["dates"].get("follow_up_date") or None,
            "fee_charged": parsed["fee"].get("fee_charged", 0),
        }

        # 疫苗识别
        vaccine_data = None
        text_lower = text.lower()
        vaccine_keywords = ["疫苗", "接种", "免疫", "驱虫", "狂犬", "五联", "六联", "八联", "猫三联"]
        if any(kw in text_lower for kw in vaccine_keywords):
            vaccine_data = {
                "pet_id": pet_id,
                "vaccine_name": parsed["treatment"].get("plan", "") or "疫苗",
                "administered_date": parsed["dates"].get("visit_date", ""),
                "next_due_date": parsed["dates"].get("follow_up_date") or None,
                "vet_name": "",
            }

        return {
            "confidence": parsed.get("confidence", 0),
            "summary": parsed.get("summary", ""),
            "form_data": form_data,
            "vaccine_data": vaccine_data,
            "engine": "deepseek",
        }

    # ======================== 疾病建议 ========================

    def suggest_diseases(self, symptoms: str) -> dict:
        """
        根据症状关键词建议可能的疾病
        """
        system_prompt = """你是兽医专家。根据输入的症状关键词，列出可能的宠物疾病诊断（中兽医术语），
按可能性从高到低排列。输出纯JSON数组格式，每个元素包含: disease(病名), confidence(置信度0-100), description(简要说明)。最多5个。"""

        result = self._chat(system_prompt, f"症状: {symptoms}")

        if result.startswith("[API错误]"):
            return {"error": result, "engine": "deepseek"}

        suggestions = self._extract_json(result)
        if suggestions is None:
            return {"error": "解析失败", "raw": result[:300], "engine": "deepseek"}

        return {
            "symptoms": [s.strip() for s in symptoms.split(",")],
            "suggestions": suggestions if isinstance(suggestions, list) else [],
            "total_matches": len(suggestions) if isinstance(suggestions, list) else 0,
            "engine": "deepseek",
        }

    # ======================== 影像分析 ========================

    def analyze_image(self, image_base64: str, image_type: str = "xray",
                      species: str = "狗", context: str = "") -> dict:
        """
        使用 DeepSeek Vision 分析医学影像（DR/X光/CT/MRI）

        Args:
            image_base64: base64编码的图片（不含 data:image/... 前缀）
            image_type: 影像类型 (xray, ct, mri, ultrasound)
            species: 宠物种类
            context: 额外临床上下文（症状、病史等）

        Returns:
            {
                "findings": "影像所见",
                "diagnosis": "诊断意见",
                "differential": ["鉴别诊断1", ...],
                "abnormalities": ["异常发现1", ...],
                "confidence": 0-100,
                "recommendations": "建议",
            }
        """
        import base64

        type_names = {
            "xray": "DR/X光片",
            "ct": "CT扫描",
            "mri": "MRI核磁共振",
            "ultrasound": "B超/超声",
        }
        type_name = type_names.get(image_type, "医学影像")

        context_text = f"\n临床背景：{context}" if context else ""

        system_prompt = f"""你是一名资深兽医影像学专家。请分析这张{species}的{type_name}影像。

请严格按照以下JSON格式输出分析结果，不要输出任何其他内容：

{{
  "findings": "影像所见 - 详细描述影像中的关键发现，包括正常和异常结构",
  "diagnosis": "诊断意见 - 根据影像给出的最可能诊断",
  "differential": ["鉴别诊断1", "鉴别诊断2", "鉴别诊断3"],
  "abnormalities": ["具体异常发现1", "具体异常发现2"],
  "confidence": 0-100的整数，表示对诊断的置信度,
  "recommendations": "建议 - 推荐的进一步检查或治疗方案",
  "severity": "正常/轻度/中度/重度/危急"
}}

规则：
- 使用标准兽医影像学术语
- 鉴别诊断按可能性排序，最多5个
- 如果影像质量不足以做出判断，在findings中说明
- 对于DR/X光片，重点观察骨骼结构、心肺轮廓、腹腔脏器、软组织肿胀、骨折、关节病变等
- 如果发现危急情况（如气胸、严重骨折、心脏显著增大等），severity标为"危急"并在recommendations中建议立即处理
- 仅输出JSON，不要输出markdown代码块标记或其他内容"""

        result = self._chat_vision(system_prompt, f"请分析这张{species}的{type_name}{context_text}", image_base64)

        if result.startswith("[API错误]"):
            return {"error": result, "engine": "deepseek_vision"}

        parsed = self._extract_json(result)
        if parsed is None:
            return {"error": "分析结果解析失败", "raw": result[:500], "engine": "deepseek_vision"}

        parsed["image_type"] = image_type
        parsed["species"] = species
        parsed["engine"] = "deepseek_vision"
        return parsed

    def _chat_vision(self, system_prompt: str, user_message: str, image_base64: str) -> str:
        """调用 DeepSeek Vision API（支持图片输入）"""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_message,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                },
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
                return f"[API错误] {error}"
        except requests.ConnectionError:
            return "[API错误] 无法连接到 DeepSeek 服务"
        except requests.Timeout:
            return "[API错误] DeepSeek 请求超时"
        except Exception as e:
            return f"[API错误] {e}"

    # ======================== 工具方法 ========================

    def _extract_json(self, text: str):
        """从文本中提取 JSON 对象或数组"""
        if not text:
            return None

        text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 从 markdown 代码块中提取
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 {...} 块
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 尝试提取 [...] 块
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None


# 单例
_deepseek_instance = None


def get_deepseek() -> DeepSeekAI:
    global _deepseek_instance
    if _deepseek_instance is None:
        _deepseek_instance = DeepSeekAI()
    return _deepseek_instance
