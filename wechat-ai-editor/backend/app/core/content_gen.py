import json
import re
import asyncio
from app.core.llm import generate_with_llm
from app.core.prompts import get_system_prompt, build_user_prompt
from app.core.knowledge_base import get_rag_context
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

    rag_context = get_rag_context(
        product_name=params.get("product_name", ""),
        content_type=content_type,
        key_points=params.get("key_points", []),
    )
    if rag_context:
        params_with_context["rag_context"] = rag_context

    system_prompt = get_system_prompt(content_type, tone)
    user_prompt = build_user_prompt(params_with_context)

    raw_response = await generate_with_llm(system_prompt, user_prompt, temperature=0.7)
    print(f"DEBUG LLM response (first 500 chars): {raw_response[:500]}")

    article_data = _parse_llm_response(raw_response)

    # Fix: if content field is nested JSON (e.g. {"title":..., "content":...}), extract inner content
    content_text = article_data.get("content", "")
    if content_text.strip().startswith("{"):
        try:
            nested = json.loads(content_text)
            if "content" in nested:
                article_data["content"] = nested["content"]
            if "title" in nested and not article_data.get("title"):
                article_data["title"] = nested["title"]
        except (json.JSONDecodeError, TypeError):
            pass

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
    if not response or not response.strip():
        raise ValueError("LLM returned empty response")

    # 1) Extract content between ```json ... ``` markers
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    block_text = code_block.group(1) if code_block else response

    # 2) Find the outermost JSON object by bracket matching
    json_text = _extract_json_object(block_text)
    if json_text:
        try:
            return json.loads(json_text)
        except (json.JSONDecodeError, TypeError):
            pass

    # 3) Try parsing the full block as JSON
    try:
        return json.loads(block_text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 4) Fallback: regex extraction
    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', response)
    content_match = re.search(r'"content"\s*:\s*"([^"]*)"', response)
    keywords_match = re.search(r'"seo_keywords"\s*:\s*\[(.*?)\]', response, re.DOTALL)
    cta_match = re.search(r'"call_to_action"\s*:\s*"([^"]+)"', response)
    time_match = re.search(r'"estimated_reading_time"\s*:\s*"([^"]+)"', response)

    seo_keywords = []
    if keywords_match:
        kw_text = keywords_match.group(1)
        seo_keywords = [k.strip().strip('"') for k in kw_text.split(",") if k.strip()]

    return {
        "title": title_match.group(1) if title_match else "朴道水汇公众号文章",
        "content": content_match.group(1) if content_match else response,
        "seo_keywords": seo_keywords,
        "call_to_action": cta_match.group(1) if cta_match else "点击阅读原文了解更多",
        "estimated_reading_time": time_match.group(1) if time_match else "3分钟",
    }


def _extract_json_object(text: str) -> str | None:
    """Extract the outermost JSON object using bracket matching."""
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _extract_image_positions(content: str) -> list[dict]:
    pattern = r'\[IMG:([^\]]+)\]'
    matches = re.findall(pattern, content)
    return [{"position": m, "description": m} for m in matches]
