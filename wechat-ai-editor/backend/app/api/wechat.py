from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.wechat_api import wechat, sync_article_to_draft
from app.models.database import record_sync

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


class SyncRequest(BaseModel):
    title: str
    html_output: str
    history_id: Optional[int] = None


@router.get("/status")
async def check_wechat_status():
    if not wechat.configured:
        return {"configured": False, "message": "微信公众号未配置"}

    try:
        token = await wechat.get_access_token()
        masked = token[:8] + "..." if token else ""
        return {"configured": True, "connected": True, "token_preview": masked}
    except Exception as e:
        return {"configured": True, "connected": False, "error": str(e)}


@router.post("/sync")
async def sync_to_wechat(req: SyncRequest):
    if not wechat.configured:
        raise HTTPException(status_code=400, detail="微信公众号未配置，请在.env中设置WECHAT_APP_ID和WECHAT_APP_SECRET")

    try:
        result = await sync_article_to_draft(
            title=req.title,
            html_content=req.html_output,
        )
        if req.history_id:
            await record_sync(req.history_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts")
async def list_wechat_drafts(offset: int = 0, count: int = 20):
    if not wechat.configured:
        raise HTTPException(status_code=400, detail="微信公众号未配置")

    try:
        data = await wechat.get_draft_list(offset=offset, count=count)
        items = []
        for item in data.get("item", []):
            media_id = item.get("media_id", "")
            content_info = item.get("content", {})
            news_items = content_info.get("news_item", [])
            for news in news_items:
                items.append({
                    "media_id": media_id,
                    "title": news.get("title", ""),
                    "digest": news.get("digest", ""),
                    "url": news.get("url", ""),
                    "update_time": content_info.get("update_time", 0),
                })
        return {
            "total": data.get("total_count", 0),
            "items": items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
