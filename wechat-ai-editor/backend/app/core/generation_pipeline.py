"""Multi-pass article generation pipeline: Plan → Draft → Polish.

Replaces single-shot generation with a 3-stage process for higher-quality,
more coherent, enterprise-grade articles.
"""

import json
import re
from app.core.llm import generate_with_llm
from app.core.prompts import get_system_prompt, PUDOW_COMPANY_INFO


async def generate_article_pipeline(
    content_type: str,
    tone: str,
    topic: str,
    key_points: list[str],
    asset_context: str,
    rag_context: str,
    progress_callback=None,
) -> dict:
    """Generate an article using the 3-stage pipeline.

    Returns:
        dict with title, content, seo_keywords, call_to_action, estimated_reading_time,
        and image_positions for matching.
    """

    context = _build_context(content_type, topic, key_points, asset_context, rag_context)

    # === Stage 1: Outline Planning ===
    if progress_callback:
        await progress_callback("planning", "正在规划文章结构...")

    outline = await _generate_outline(content_type, tone, context)
    if not outline.get("sections"):
        raise Exception("大纲生成失败，无法规划文章结构")

    # === Stage 2: Draft each section ===
    sections = outline["sections"]
    drafted_sections = []
    for i, section in enumerate(sections):
        if progress_callback:
            await progress_callback("drafting", f"正在撰写第{i+1}/{len(sections)}段: {section.get('title', '')}")

        section_content = await _draft_section(
            content_type=content_type,
            tone=tone,
            section=section,
            context=context,
            previous_sections=drafted_sections,
        )
        drafted_sections.append({
            "title": section.get("title", ""),
            "image_hint": section.get("image_hint", ""),
            "content": section_content,
        })

    # === Stage 3: Polish & Finalize ===
    if progress_callback:
        await progress_callback("polishing", "正在润色全文并优化排版...")

    polished = await _polish_article(
        content_type=content_type,
        tone=tone,
        title=outline.get("title", ""),
        sections=drafted_sections,
    )

    # Extract image positions from content
    image_positions = _extract_image_positions(polished.get("content", ""))

    return {
        "article_title": polished.get("title", outline.get("title", "未生成标题")),
        "article_content_markdown": polished.get("content", ""),
        "seo_keywords": polished.get("seo_keywords", []),
        "call_to_action": polished.get("call_to_action", "点击阅读原文了解更多"),
        "estimated_reading_time": polished.get("estimated_reading_time", "3分钟"),
        "image_positions": image_positions,
    }


async def _generate_outline(content_type: str, tone: str, context: str) -> dict:
    prompt = f"""你是一位资深公众号内容策划。请为以下内容规划文章大纲。

内容类型：{content_type}
语气风格：{tone}
背景信息：
{context}

请输出一个JSON格式的大纲：
```json
{{
  "title": "文章标题（20-30字）",
  "sections": [
    {{"title": "小节标题", "image_hint": "配图建议（如：产品主图/功能演示/场景应用/客户案例）", "key_message": "本节核心信息（1句话）"}}
  ]
}}
```

要求：
- 4-6个小节，每节有明确的主题和配图建议
- 结构逻辑：痛点引入→产品展示→技术展开→案例佐证→行动召唤
- image_hint要具体，能对应到素材库的图片类型"""

    response = await generate_with_llm(
        system_prompt="你是专业的公众号内容策划师，输出简洁精准的JSON。",
        user_prompt=prompt,
        temperature=0.6,
    )
    return _parse_json(response)


async def _draft_section(content_type: str, tone: str, section: dict, context: str, previous_sections: list[dict]) -> str:
    prev_context = ""
    if previous_sections:
        prev_context = "前文摘要：\n" + "\n".join(
            f"- {s['title']}: {s['content'][:100]}..." for s in previous_sections
        )

    prompt = f"""请撰写公众号文章的一个小节。

内容类型：{content_type} | 语气风格：{tone}
小节标题：{section.get('title', '')}
核心信息：{section.get('key_message', '')}
{prev_context}
背景参考：
{context[:800]}

要求：
- 200-400字
- 衔接前文，自然过渡
- 包含具体数据或案例细节（从背景参考中提取真实信息）
- 如果image_hint有值，在合适的段落结束后插入 [IMG:{section.get('image_hint', '配图')}]
- 禁止使用绝对化用词"""

    response = await generate_with_llm(
        system_prompt="你是专业的公众号撰稿人，输出高质量的中文段落。",
        user_prompt=prompt,
        temperature=0.7,
    )
    return response.strip()


async def _polish_article(content_type: str, tone: str, title: str, sections: list[dict]) -> dict:
    draft = f"# {title}\n\n"
    for s in sections:
        draft += f"## {s['title']}\n\n{s['content']}\n\n"

    prompt = f"""请润色以下公众号文章草稿。

内容类型：{content_type} | 语气风格：{tone}
公司品牌色：朴道蓝 #0066CC | 品牌口号：朴道，健康水专家

草稿：
{draft[:3000]}

润色要求：
1. 统一全文语气和风格
2. 优化段落过渡和衔接
3. 检查品牌用语一致性
4. 添加适当的强调（**加粗**关键信息）
5. 修正任何可能的广告法违禁词
6. 确保[IMG:xxx]标记位置合理

请输出JSON：
```json
{{
  "title": "最终标题",
  "content": "润色后的Markdown全文（保留[IMG:xxx]标记）",
  "seo_keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "call_to_action": "行动召唤文案",
  "estimated_reading_time": "X分钟"
}}
```"""

    response = await generate_with_llm(
        system_prompt="你是资深的公众号内容编辑，擅长润色和优化。输出标准的JSON格式。",
        user_prompt=prompt,
        temperature=0.5,
    )
    return _parse_json(response)


def _build_context(content_type, topic, key_points, asset_context, rag_context):
    parts = [f"内容类型：{content_type}"]
    if topic:
        parts.append(f"主题/产品：{topic}")
    if key_points:
        parts.append(f"核心卖点：{', '.join(key_points)}")
    if rag_context:
        parts.append(rag_context)
    if asset_context:
        parts.append(f"可用图片素材：\n{asset_context[:600]}")
    return "\n\n".join(parts)


def _parse_json(response: str) -> dict:
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    text = json_match.group(1) if json_match else response

    # Bracket matching for reliable JSON extraction
    start = text.find('{')
    if start == -1:
        return {}
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False; continue
        if ch == '\\':
            escape = True; continue
        if ch == '"' and not escape:
            in_string = not in_string; continue
        if in_string: continue
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


def _extract_image_positions(content: str) -> list[dict]:
    matches = re.findall(r'\[IMG:([^\]]+)\]', content)
    return [{"position": m, "description": m} for m in matches]
