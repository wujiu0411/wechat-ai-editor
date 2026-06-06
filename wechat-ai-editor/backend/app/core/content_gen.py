import json
import re
import asyncio
from app.core.llm import generate_with_llm
from app.core.prompts import get_system_prompt, build_user_prompt
from app.models.database import search_assets


async def _gather_asset_context(params: dict) -> str:
    product_name = params.get("product_name", "")
    key_points = params.get("key_points", [])
    topic = params.get("topic", "")
    search_terms = [product_name] + key_points + [topic]
    search_terms = [t for t in search_terms if t]

    all_assets = []
    for term in search_terms:
        assets = await search_assets(query=term)
        all_assets.extend(assets)

    seen = set()
    unique_assets = []
    for a in all_assets:
        if a["filepath"] not in seen:
            seen.add(a["filepath"])
            unique_assets.append(a)

    if not unique_assets:
        assets = await search_assets(category="产品图")
        unique_assets = assets[:5]

    lines = []
    for a in unique_assets[:15]:
        lines.append(f"- [{a['category']}] {a['filename']} (路径: {a['filepath']}, 关键词: {a.get('keywords', '')})")

    return "\n".join(lines) if lines else "暂无匹配素材"


async def generate_article(params: dict) -> dict:
    content_type = params.get("content_type", "")
    tone = params.get("tone", "专业、科技感")

    asset_context = await _gather_asset_context(params)
    params_with_context = {**params, "asset_context": asset_context}

    system_prompt = get_system_prompt(content_type, tone)
    user_prompt = build_user_prompt(params_with_context)

    raw_response = await generate_with_llm(system_prompt, user_prompt, temperature=0.7)

    article_data = _parse_llm_response(raw_response)

    image_positions = _extract_image_positions(article_data.get("content", ""))

    return {
        "article_title": article_data.get("title", "未生成标题"),
        "article_content_markdown": article_data.get("content", ""),
        "seo_keywords": article_data.get("seo_keywords", []),
        "call_to_action": article_data.get("call_to_action", ""),
        "estimated_reading_time": article_data.get("estimated_reading_time", "3分钟"),
        "image_positions": image_positions,
    }


def _parse_llm_response(response: str) -> dict:
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', response)
    content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', response, re.DOTALL)
    return {
        "title": title_match.group(1) if title_match else "朴道水汇公众号文章",
        "content": content_match.group(1) if content_match else response,
        "seo_keywords": [],
        "call_to_action": "点击阅读原文了解更多",
        "estimated_reading_time": "3分钟",
    }


def _extract_image_positions(content: str) -> list[dict]:
    pattern = r'\[IMG:([^\]]+)\]'
    matches = re.findall(pattern, content)
    return [{"position": m, "description": m} for m in matches]
