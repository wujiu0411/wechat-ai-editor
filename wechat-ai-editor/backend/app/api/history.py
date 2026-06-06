from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.database import (
    get_history_list,
    get_history_by_id,
    delete_history,
    update_history,
)
from app.core.asset_indexer import init_app
import json

router = APIRouter(prefix="/api/history", tags=["history"])

_app_initialized = False


async def ensure_init():
    global _app_initialized
    if not _app_initialized:
        await init_app()
        _app_initialized = True


@router.get("/list")
async def list_history(limit: int = 20, offset: int = 0):
    await ensure_init()
    items, total = await get_history_list(limit=limit, offset=offset)

    for item in items:
        if isinstance(item.get("input_params"), str):
            item["input_params"] = json.loads(item["input_params"])
        if isinstance(item.get("images"), str):
            item["images"] = json.loads(item["images"])
        if isinstance(item.get("seo_keywords"), str):
            item["seo_keywords"] = json.loads(item["seo_keywords"])
        if isinstance(item.get("quality_report"), str):
            item["quality_report"] = json.loads(item["quality_report"])

    return {"total": total, "items": items, "limit": limit, "offset": offset}


@router.get("/{item_id}")
async def get_history(item_id: int):
    await ensure_init()
    item = await get_history_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")

    if isinstance(item.get("input_params"), str):
        item["input_params"] = json.loads(item["input_params"])
    if isinstance(item.get("images"), str):
        item["images"] = json.loads(item["images"])
    if isinstance(item.get("seo_keywords"), str):
        item["seo_keywords"] = json.loads(item["seo_keywords"])
    if isinstance(item.get("quality_report"), str):
        item["quality_report"] = json.loads(item["quality_report"])

    return item


class HistoryUpdate(BaseModel):
    article_title: Optional[str] = None
    article_content_markdown: Optional[str] = None
    html_output: Optional[str] = None


@router.put("/{item_id}")
async def edit_history(item_id: int, data: HistoryUpdate):
    await ensure_init()
    existing = await get_history_by_id(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="记录不存在")

    updates = {}
    if data.article_title is not None:
        updates["article_title"] = data.article_title
    if data.article_content_markdown is not None:
        updates["article_content_markdown"] = data.article_content_markdown
    if data.html_output is not None:
        updates["html_output"] = data.html_output

    if updates:
        await update_history(item_id, updates)

    return {"message": "更新成功"}


@router.delete("/{item_id}")
async def remove_history(item_id: int):
    await ensure_init()
    await delete_history(item_id)
    return {"message": "已删除"}
