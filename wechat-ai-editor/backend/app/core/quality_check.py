import re
from app.models.database import load_sensitive_words


async def quality_check(
    title: str,
    content: str,
    images: list[dict],
    min_words: int = 500,
    max_words: int = 1500,
    max_images: int = 10,
) -> dict:
    sensitive_words = await load_sensitive_words()

    ad_law_words = [w for w in sensitive_words if _get_word_category(w, sensitive_words) == "ad_law"]
    competitor_words = [w for w in sensitive_words if _get_word_category(w, sensitive_words) == "competitor"]

    ad_violations = _find_words(title + content, ad_law_words)
    competitor_violations = _find_words(title + content, competitor_words)

    content_clean = _strip_markdown(content)
    word_count = len(content_clean)

    valid_images = [img for img in images if not img.get("source", "").startswith("[缺失")]

    issues = []
    warnings = []

    if ad_violations:
        issues.append(f"包含广告法禁用词：{', '.join(ad_violations)}")

    if competitor_violations:
        issues.append(f"包含竞品名称：{', '.join(competitor_violations)}")

    if word_count < min_words:
        warnings.append(f"文章字数偏少（{word_count}字），建议不少于{min_words}字")

    if word_count > max_words:
        warnings.append(f"文章字数偏多（{word_count}字），建议不超过{max_words}字")

    if len(valid_images) < 3:
        warnings.append(f"配图数量偏少（{len(valid_images)}张），建议至少3张")

    if len(images) > max_images:
        warnings.append(f"图片数量超过限制（{len(images)}张），最多{max_images}张")

    missing_images = [img for img in images if img.get("source", "").startswith("[缺失")]
    if missing_images:
        warnings.append(f"有{len(missing_images)}张图片缺失，需手动补充")

    score = 100
    score -= len(ad_violations) * 20
    score -= len(competitor_violations) * 15
    score -= len(warnings) * 5
    score = max(score, 0)

    passed = len(issues) == 0

    # LLM self-evaluation (lightweight)
    self_review = await _llm_self_review(title, content)

    return {
        "passed": passed,
        "score": score,
        "issues": issues,
        "warnings": warnings,
        "self_review": self_review,
        "word_count": word_count,
        "image_count": len(valid_images),
        "missing_image_count": len(missing_images),
        "ad_violations": ad_violations,
        "competitor_violations": competitor_violations,
    }


def auto_fix_content(title: str, content: str) -> tuple[str, str]:
    competitor_replacements = {
        "美的": "传统净水设备",
        "沁园": "传统净水设备",
        "安吉尔": "传统净水设备",
        "3M净水": "传统净水设备",
        "A.O.史密斯": "传统净水设备",
        "海尔净水": "传统净水设备",
        "小米净水": "传统净水设备",
    }

    fixed_content = content
    fixed_title = title

    for word, replacement in competitor_replacements.items():
        fixed_content = fixed_content.replace(word, replacement)
        fixed_title = fixed_title.replace(word, replacement)

    return fixed_title, fixed_content


def _get_word_category(word: str, all_words: list) -> str:
    return "competitor" if word in ["美的", "沁园", "安吉尔", "3M净水", "A.O.史密斯", "海尔净水", "小米净水"] else "ad_law"


def _find_words(text: str, words: list[str]) -> list[str]:
    found = []
    for w in words:
        if w in text:
            found.append(w)
    return found


async def _llm_self_review(title: str, content: str) -> dict:
    """LLM self-evaluates its own output for quality."""
    try:
        from app.core.llm import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage

        prompt = f"""请评价这篇公众号文章的质量。仅输出JSON，不做额外解释。

标题：{title[:60]}
内容前500字：{content[:500]}

评分维度（每项1-10分）：
- 标题吸引力：是否吸引点击
- 内容完整性：是否覆盖关键信息
- 品牌调性：是否符合专业科技感
- 可读性：排版和段落节奏

```json
{{"title_appeal": 7, "content_completeness": 7, "brand_tone": 7, "readability": 7, "overall": 7, "suggestion": "一句话改进建议"}}
```"""
        llm = get_llm(temperature=0.2, max_tokens=150)
        messages = [SystemMessage(content="你是内容质量评审专家。"), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)
        resp_text = response.content.strip()

        import json, re
        json_match = re.search(r'\{[^}]*\}', resp_text)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception:
        pass

    return {"overall": 7, "suggestion": "暂无评价"}


def _strip_markdown(text: str) -> str:
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'[#*`>\-]', '', text)
    text = re.sub(r'\[IMG:[^\]]+\]', '', text)
    text = re.sub(r'\s+', '', text)
    return text
