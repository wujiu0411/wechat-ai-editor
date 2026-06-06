import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import ArticleInput, ArticleOutput, ImageInfo
from app.core.content_gen import generate_article
from app.core.image_matcher import match_images
from app.core.formatter import format_article
from app.core.quality_check import quality_check, auto_fix_content
from app.core.asset_indexer import scan_assets
from app.models.database import insert_history
from app.core.asset_indexer import init_app
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

    await insert_history({
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

    return result


@router.post("/reformat")
async def reformat_article(
    title: str,
    markdown_content: str,
    template_id: str = "tech_pro",
    cta: str = "点击阅读原文了解更多",
):
    html_output = format_article(
        title=title,
        markdown_content=markdown_content,
        images=[],
        cta=cta,
        template_id=template_id,
    )
    return {"html_output": html_output}


@router.post("/refresh-assets")
async def refresh_assets():
    await ensure_init()
    count = await scan_assets()
    return {"message": f"已重新索引 {count} 个素材文件"}
