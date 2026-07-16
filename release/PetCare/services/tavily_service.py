"""Tavily 联网搜索服务 — 增强 RAG 知识库

用于兽医文献实时联网检索，弥补离线知识库覆盖不足。
API: https://docs.tavily.com/
"""

import requests
import logging

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


def search_vet(query: str, max_results: int = 5) -> dict:
    """兽医知识联网搜索

    Args:
        query: 搜索关键词（英文效果更好，自动中英混合）
        max_results: 返回条数 5-10

    Returns:
        {"results": [...], "answer": "...", "count": N}
    """
    from config import Config

    api_key = Config.TAVILY_API_KEY
    if not api_key:
        return {"error": "Tavily API Key 未配置", "results": [], "count": 0}

    vet_query = f"veterinary medicine {query}"
    payload = {
        "api_key": api_key,
        "query": vet_query,
        "search_depth": "advanced",
        "topic": "general",
        "max_results": min(max(max_results, 3), 10),
        "include_raw_content": False,
        "include_images": False,
    }

    try:
        resp = requests.post(TAVILY_API_URL, json=payload, timeout=15)
        if resp.status_code != 200:
            return {"error": f"Tavily API 错误: {resp.status_code}", "results": [], "count": 0}

        data = resp.json()
        results = data.get("results", [])
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                    "score": round(r.get("score", 0), 3),
                }
                for r in results
            ],
            "answer": data.get("answer", ""),
            "count": len(results),
        }
    except requests.Timeout:
        return {"error": "Tavily 请求超时", "results": [], "count": 0}
    except Exception as e:
        return {"error": str(e), "results": [], "count": 0}


def search_vet_context(query: str, max_tokens: int = 2000) -> str:
    """兽医联网搜索 → 拼接为上下文文本（用于注入 LLM prompt）

    Args:
        query: 搜索关键词
        max_tokens: 上下文最大 token 数（约2000字≈3000 tokens）
    """
    result = search_vet(query, max_results=5)
    if result.get("error"):
        return ""

    lines = []
    char_limit = max_tokens * 2  # 粗略: 1 token ≈ 0.5 中文字符

    if result.get("answer"):
        lines.append(f"## AI 摘要\n{result['answer']}\n")

    lines.append("## 搜索结果")
    total_chars = 0
    for r in result.get("results", []):
        text = f"- **{r['title']}**: {r['content']} (来源: {r['url']})"
        lines.append(text)
        total_chars += len(text)
        if total_chars > char_limit:
            break

    return "\n".join(lines)
