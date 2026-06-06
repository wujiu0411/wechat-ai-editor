import os
import uuid
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models.database import search_assets, upsert_asset, delete_asset
from app.core.asset_indexer import init_app
from app.models.schemas import AssetItem
from pathlib import Path
from app.core.config import settings

router = APIRouter(prefix="/api/assets", tags=["assets"])

_app_initialized = False


async def ensure_init():
    global _app_initialized
    if not _app_initialized:
        await init_app()
        _app_initialized = True


@router.get("/list")
async def list_assets(
    query: str = "",
    category: str = "",
    sub_category: str = "",
):
    await ensure_init()
    results = await search_assets(query=query, category=category, sub_category=sub_category)
    return {"total": len(results), "items": results}


@router.get("/categories")
async def get_categories():
    await ensure_init()
    all_assets = await search_assets()
    categories = {}
    for a in all_assets:
        cat = a["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "sub_categories": set()}
        categories[cat]["count"] += 1
        if a.get("sub_category"):
            categories[cat]["sub_categories"].add(a["sub_category"])

    result = []
    for cat, info in categories.items():
        result.append({
            "name": cat,
            "count": info["count"],
            "sub_categories": list(info["sub_categories"]),
        })
    return result


@router.get("/serve/{filepath:path}")
async def serve_asset(filepath: str):
    from fastapi.responses import FileResponse

    for base_dir in [Path(settings.UPLOAD_DIR), Path(settings.ASSETS_DIR)]:
        file_path = base_dir / filepath
        if file_path.exists():
            if not str(file_path.resolve()).startswith(str(base_dir.resolve())):
                raise HTTPException(status_code=403, detail="无权访问")
            return FileResponse(str(file_path))

    raise HTTPException(status_code=404, detail="文件不存在")


@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    category: str = Form("其他"),
    sub_category: str = Form(""),
    keywords: str = Form(""),
):
    await ensure_init()

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".mp4", ".pdf"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    content = await file.read()
    file_size = len(content)
    max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"} and file_size > max_size:
        raise HTTPException(status_code=400, detail=f"图片大小超过{settings.MAX_IMAGE_SIZE_MB}MB限制")

    upload_dir = Path(settings.UPLOAD_DIR) / category
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    file_path = upload_dir / unique_name

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    rel_path = str(file_path.relative_to(Path(settings.UPLOAD_DIR))).replace("\\", "/")

    file_type = "image" if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"} else ("video" if ext == ".mp4" else "document")

    await upsert_asset({
        "filename": file.filename,
        "filepath": rel_path,
        "category": category,
        "sub_category": sub_category or None,
        "keywords": keywords or file.filename,
        "file_size": file_size,
        "file_type": file_type,
    })

    return {"message": "上传成功", "filepath": rel_path, "filename": file.filename}


@router.put("/{asset_id}")
async def update_asset(
    asset_id: int,
    category: str = Form(None),
    sub_category: str = Form(None),
    keywords: str = Form(None),
):
    await ensure_init()
    from app.models.database import get_asset_by_id
    asset = await get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    if category is not None:
        asset["category"] = category
    if sub_category is not None:
        asset["sub_category"] = sub_category
    if keywords is not None:
        asset["keywords"] = keywords

    await upsert_asset(asset)
    return {"message": "更新成功"}


@router.delete("/{asset_id}")
async def remove_asset(asset_id: int):
    await ensure_init()
    from app.models.database import get_asset_by_id, delete_asset
    asset = await get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    file_path = Path(settings.UPLOAD_DIR) / asset["filepath"]
    if file_path.exists():
        os.remove(file_path)

    await delete_asset(asset_id)
    return {"message": "已删除"}
