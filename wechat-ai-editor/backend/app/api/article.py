import asyncio
import re
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import ArticleInput, ArticleOutput, ImageInfo
from app.core.content_gen import generate_article, _parse_llm_response
from app.core.prompts import get_system_prompt, build_user_prompt
from app.core.image_matcher import match_images, _make_url
from app.core.image_descriptor import ensure_image_descriptions, match_images_semantic
from app.core.formatter import format_article
from app.core.quality_check import quality_check, auto_fix_content
from app.core.asset_indexer import scan_assets, init_app
from app.core.llm import generate_with_llm
from app.core.knowledge_base import get_rag_context
from app.models.database import insert_history, search_assets as db_search_assets
from app.templates.css_templates import get_template_for_content_type

router = APIRouter(prefix="/api/article", tags=["article"])

_app_initialized = False


async def ensure_init():
    global _app_initialized
    if not _app_initialized:
        await init_app()
        _app_initialized = True


@router.post("/generate", response_model=ArticleOutput)
async def create_article(input_data: ArticleInput):
    await ensure_init()

    params = input_data.model_dump()
    content_type = params.get("content_type", "")

    try:
        article = await asyncio.wait_for(
            generate_article(params),
            timeout=120,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="文章生成超时，请稍后重试")
    except Exception as e:
        import traceback
        print(f"ERROR in generate: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")

    image_positions = article.get("image_positions", [])
    images = await match_images(
        image_positions,
        product_name=params.get("product_name", ""),
        content_type=content_type,
    )

    title = article["article_title"]
    content = article["article_content_markdown"]

    title, content = auto_fix_content(title, content)

    template_id = input_data.template_id or get_template_for_content_type(content_type)

    html_output = format_article(
        title=title,
        markdown_content=content,
        images=images,
        cta=article.get("call_to_action", "点击阅读原文了解更多"),
        template_id=template_id,
        content_type=content_type,
    )

    q_report = await quality_check(title, content, images)

    image_infos = [
        ImageInfo(
            position=img.get("position", ""),
            source=img.get("source", ""),
            alt_text=img.get("alt_text", ""),
        )
        for img in images
    ]

    result = ArticleOutput(
        article_title=title,
        article_content_markdown=content,
        html_output=html_output,
        images=image_infos,
        seo_keywords=article.get("seo_keywords", []),
        estimated_reading_time=article.get("estimated_reading_time", "3分钟"),
        call_to_action=article.get("call_to_action", "点击阅读原文了解更多"),
        quality_report=q_report,
    )

    history_id = await insert_history({
        "content_type": content_type,
        "input_params": params,
        "article_title": title,
        "article_content_markdown": content,
        "html_output": html_output,
        "images": [img.model_dump() for img in image_infos],
        "seo_keywords": article.get("seo_keywords", []),
        "template_id": template_id,
        "quality_report": q_report,
    })

    result.history_id = history_id
    return result


class ImageBasedInput(BaseModel):
    image_filepaths: list[str]
    tone: str = "专业、科技感"
    topic_hint: Optional[str] = None


@router.post("/generate-from-images")
async def create_from_images(input_data: ImageBasedInput):
    await ensure_init()

    if not input_data.image_filepaths:
        raise HTTPException(status_code=400, detail="请至少选择一张图片")

    # Look up metadata for selected images
    all_assets = await db_search_assets()
    asset_map = {a["filepath"]: a for a in all_assets}

    image_context_parts = []
    selected_images = []
    for fp in input_data.image_filepaths:
        asset = asset_map.get(fp)
        if asset:
            selected_images.append(asset)
            image_context_parts.append(
                f"- [{asset['category']}] {asset['filename']}"
                f"（关键词: {asset.get('keywords', '无')}）"
            )

    if not selected_images:
        raise HTTPException(status_code=400, detail="未找到选中的素材")

    # Determine content type from image categories
    categories = [a["category"] for a in selected_images]
    if any(c in ["产品图"] for c in categories):
        detected_type = "新品上市"
    elif any(c in ["海报"] for c in categories):
        detected_type = "节日促销"
    elif any(c in ["科普图"] for c in categories):
        detected_type = "喝水知识科普"
    else:
        detected_type = "新品上市"

    # Build prompts
    from app.core.prompts import IMAGE_BASED_PROMPT, PUDOW_COMPANY_INFO

    topic_text = f"\n用户建议主题：{input_data.topic_hint}" if input_data.topic_hint else ""
    image_context = "\n".join(image_context_parts)

    system_prompt = IMAGE_BASED_PROMPT.replace("{company_info}", PUDOW_COMPANY_INFO) \
        .replace("{tone}", input_data.tone) \
        .replace("{image_context}", image_context + topic_text)

    user_prompt = f"请根据以上宣传图片的信息，创作一篇微信公众号文章。{topic_text}"

    try:
        article = await asyncio.wait_for(
            generate_with_llm(system_prompt, user_prompt, temperature=0.7),
            timeout=120,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="文章生成超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")

    article_data = _parse_llm_response(article)

    # Build image list directly from selected images
    images = []
    for asset in selected_images:
        images.append({
            "position": asset.get("keywords", asset["filename"]),
            "source": _make_url(asset["filepath"]),
            "alt_text": asset["filename"],
            "filename": asset["filename"],
            "file_type": asset.get("file_type", "image"),
        })

    title = article_data.get("title", "未生成标题")
    content = article_data.get("content", "")

    title, content = auto_fix_content(title, content)

    template_id = get_template_for_content_type(detected_type)

    html_output = format_article(
        title=title,
        markdown_content=content,
        images=images,
        cta=article_data.get("call_to_action", "点击阅读原文了解更多"),
        template_id=template_id,
        content_type=detected_type,
    )

    q_report = await quality_check(title, content, images)

    image_infos = [
        ImageInfo(position=img.get("position", ""), source=img.get("source", ""), alt_text=img.get("alt_text", ""))
        for img in images
    ]

    result = ArticleOutput(
        article_title=title,
        article_content_markdown=content,
        html_output=html_output,
        images=image_infos,
        seo_keywords=article_data.get("seo_keywords", []),
        estimated_reading_time=article_data.get("estimated_reading_time", "3分钟"),
        call_to_action=article_data.get("call_to_action", "点击阅读原文了解更多"),
        quality_report=q_report,
    )

    history_id = await insert_history({
        "content_type": f"选图-{detected_type}",
        "input_params": {"image_filepaths": input_data.image_filepaths, "tone": input_data.tone},
        "article_title": title,
        "article_content_markdown": content,
        "html_output": html_output,
        "images": [img.model_dump() for img in image_infos],
        "seo_keywords": article_data.get("seo_keywords", []),
        "template_id": template_id,
        "quality_report": q_report,
    })

    result.history_id = history_id
    return result


class ReformatRequest(BaseModel):
    title: str
    markdown_content: str
    template_id: str = "tech_pro"
    cta: str = "点击阅读原文了解更多"
    images: list[dict] = []


@router.post("/generate-v2", response_model=ArticleOutput)
async def create_article_v2(input_data: ArticleInput):
    """增强版生成：RAG知识库 + 链式思考prompt"""
    await ensure_init()

    params = input_data.model_dump()
    content_type = params.get("content_type", "")
    tone = params.get("tone", "专业、科技感")
    product_name = params.get("product_name", "") or params.get("topic", "")
    key_points = params.get("key_points", [])

    # Gather RAG context from company documents
    rag_context = get_rag_context(product_name, content_type, key_points)

    # Gather asset context
    asset_context = await _gather_asset_context_v2(params)

    # Build enhanced system prompt with chain-of-thought instructions
    system_prompt = get_system_prompt(content_type, tone)
    enhanced_system = system_prompt + """

【增强指令 - 按以下步骤思考后再输出】
第一步：先在心里规划文章结构（开头痛点 → 主体2-3个卖点展开 → 客户案例 → 结尾CTA）
第二步：每个卖点段落引用下方【公司知识库参考内容】中的真实数据
第三步：为每段选择最合适的配图位置，[IMG:描述] 放在段落之间
第四步：全文写完后自查：参数是否准确、图片位置是否合理、语气是否统一"""

    user_prompt = build_user_prompt(params)
    if rag_context:
        user_prompt += f"\n\n{rag_context}"
    if asset_context:
        user_prompt += f"\n可用图片素材：\n{asset_context}"

    try:
        article = await asyncio.wait_for(
            generate_with_llm(enhanced_system, user_prompt, temperature=0.7),
            timeout=180,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="文章生成超时，请稍后重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")

    from app.core.content_gen import _parse_llm_response
    article_data = _parse_llm_response(article)

    # Use semantic matching: split content into paragraphs, match each to best image
    content_text = article_data.get("content", "")
    paragraphs = [p.strip() for p in re.split(r'\n\n+', content_text) if len(p.strip()) > 30]
    semantic_images = await match_images_semantic(paragraphs[:10])

    # Also try traditional positional matching for explicit [IMG:xxx] markers
    image_positions = _extract_image_positions(content_text)
    traditional_images = await match_images(image_positions, product_name=product_name, content_type=content_type)

    # Merge: prefer semantic matches, fallback to traditional for explicit markers
    images = semantic_images if semantic_images else traditional_images

    title = article_data.get("title", "未生成标题")
    content = article_data.get("content", "")
    title, content = auto_fix_content(title, content)

    template_id = input_data.template_id or get_template_for_content_type(content_type)

    html_output = format_article(
        title=title, markdown_content=content, images=images,
        cta=article_data.get("call_to_action", "点击阅读原文了解更多"),
        template_id=template_id, content_type=content_type,
    )

    q_report = await quality_check(title, content, images)

    image_infos = [ImageInfo(position=img.get("position", ""), source=img.get("source", ""), alt_text=img.get("alt_text", "")) for img in images]

    result = ArticleOutput(
        article_title=title, article_content_markdown=content,
        html_output=html_output, images=image_infos,
        seo_keywords=article_data.get("seo_keywords", []),
        estimated_reading_time=article_data.get("estimated_reading_time", "3分钟"),
        call_to_action=article_data.get("call_to_action", "点击阅读原文了解更多"),
        quality_report=q_report,
    )

    history_id = await insert_history({
        "content_type": content_type, "input_params": params,
        "article_title": title, "article_content_markdown": content,
        "html_output": html_output, "images": [img.model_dump() for img in image_infos],
        "seo_keywords": article_data.get("seo_keywords", []),
        "template_id": template_id, "quality_report": q_report,
    })
    result.history_id = history_id
    return result


async def _gather_asset_context_v2(params: dict) -> str:
    product_name = params.get("product_name", "")
    key_points = params.get("key_points", [])
    topic = params.get("topic", "")
    search_terms = [product_name] + key_points + [topic]
    search_terms = [t for t in search_terms if t]

    all_assets = []
    for term in search_terms:
        assets = await db_search_assets(query=term, file_type="image")
        all_assets.extend(assets)

    seen = set()
    unique = []
    for a in all_assets:
        if a["filepath"] not in seen:
            seen.add(a["filepath"])
            unique.append(a)

    if not unique:
        assets = await db_search_assets(category="产品图", file_type="image")
        unique = assets[:5]

    lines = []
    for a in unique[:10]:
        lines.append(f"- [{a['category']}] {a['filename']} (关键词: {a.get('keywords', '')})")
    return "\n".join(lines) if lines else "暂无匹配素材"


def _extract_image_positions(content: str) -> list[dict]:
    import re
    matches = re.findall(r'\[IMG:([^\]]+)\]', content)
    return [{"position": m, "description": m} for m in matches]


@router.post("/reformat")
async def reformat_article(req: ReformatRequest):
    html_output = format_article(
        title=req.title,
        markdown_content=req.markdown_content,
        images=req.images or [],
        cta=req.cta,
        template_id=req.template_id,
    )
    return {"html_output": html_output}


class BatchGenerateInput(BaseModel):
    articles: list[dict]  # list of ArticleInput-like dicts


@router.post("/batch-generate")
async def batch_generate(input_data: BatchGenerateInput):
    """批量生成多篇文章"""
    await ensure_init()

    if not input_data.articles:
        raise HTTPException(status_code=400, detail="请至少指定一篇要生成的文章")

    results = []
    errors = []
    for i, art_params in enumerate(input_data.articles):
        try:
            art_input = ArticleInput(**art_params)
            # Use the internal generate logic directly
            params = art_input.model_dump()
            content_type = params.get("content_type", "")

            article = await asyncio.wait_for(generate_article(params), timeout=180)
            image_positions = article.get("image_positions", [])
            images = await match_images(image_positions, product_name=params.get("product_name", ""), content_type=content_type)

            title = article["article_title"]
            content = article["article_content_markdown"]
            title, content = auto_fix_content(title, content)

            template_id = art_input.template_id or get_template_for_content_type(content_type)
            html_output = format_article(title=title, markdown_content=content, images=images, cta=article.get("call_to_action", "点击阅读原文了解更多"), template_id=template_id, content_type=content_type)
            q_report = await quality_check(title, content, images)

            image_infos = [ImageInfo(position=img.get("position", ""), source=img.get("source", ""), alt_text=img.get("alt_text", "")) for img in images]

            result = ArticleOutput(
                article_title=title, article_content_markdown=content,
                html_output=html_output, images=image_infos,
                seo_keywords=article.get("seo_keywords", []),
                estimated_reading_time=article.get("estimated_reading_time", "3分钟"),
                call_to_action=article.get("call_to_action", "点击阅读原文了解更多"),
                quality_report=q_report,
            )

            history_id = await insert_history({
                "content_type": content_type, "input_params": params,
                "article_title": title, "article_content_markdown": content,
                "html_output": html_output, "images": [img.model_dump() for img in image_infos],
                "seo_keywords": article.get("seo_keywords", []),
                "template_id": template_id, "quality_report": q_report,
            })
            result.history_id = history_id
            results.append({"index": i, "status": "ok", "result": result.model_dump()})
        except Exception as e:
            errors.append({"index": i, "status": "error", "error": str(e)})

    return {"total": len(input_data.articles), "success": len(results), "failed": len(errors), "results": results, "errors": errors}


class SuggestionGenerateInput(BaseModel):
    topic: str
    content_type: str
    tone: str = "专业、科技感"


@router.post("/generate-from-suggestion")
async def generate_from_suggestion(input_data: SuggestionGenerateInput):
    """根据选题建议直接生成文章"""
    await ensure_init()

    art_input = ArticleInput(
        content_type=input_data.content_type,
        product_name="朴道直饮机" if input_data.content_type in ["新品上市", "装机案例"] else "",
        topic=input_data.topic,
        key_points=[],
        tone=input_data.tone,
    )

    return await create_article_v2(art_input)


@router.get("/suggestions")
async def get_topic_suggestions(force_refresh: bool = False):
    """获取本周选题建议，含配图提示词。缓存7天，传force_refresh=true强制刷新"""
    await ensure_init()
    from app.core.topic_suggester import get_suggestions, get_today_suggested_articles, generate_image_prompts_sync

    suggestions = await get_suggestions(force_refresh=force_refresh)

    # Add image prompts for all suggestions (instant, template-based)
    for s in suggestions:
        s["image_prompts"] = generate_image_prompts_sync(s["topic"], s["content_type"], count=3)

    articles = await get_today_suggested_articles()
    return {"suggestions": suggestions, "suggested_articles": articles}


@router.post("/refresh-assets")
async def refresh_assets():
    await ensure_init()
    count = await scan_assets()
    return {"message": f"已重新索引 {count} 个素材文件"}
