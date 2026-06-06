import os
import io
import uuid
import aiofiles
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from PIL import Image as PILImage
from app.models.database import search_assets, upsert_asset, delete_asset
from app.core.config import settings
from app.core.asset_indexer import init_app
from app.models.schemas import AssetItem

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
    file_type: str = "",
):
    await ensure_init()
    results = await search_assets(query=query, category=category, sub_category=sub_category, file_type=file_type)
    return {"total": len(results), "items": results}


class SplitRequest(BaseModel):
    seg_heights: list[int] = []


@router.post("/{asset_id}/split-long")
async def split_long_image(asset_id: int, req: SplitRequest = SplitRequest()):
    """将长图按指定高度裁剪为多个片段。seg_heights为空则自动分割。"""
    await ensure_init()
    from app.models.database import get_asset_by_id

    asset = await get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    file_path = None
    for base_dir in [Path(settings.UPLOAD_DIR), Path(settings.ASSETS_DIR)]:
        p = base_dir / asset["filepath"]
        if p.exists():
            file_path = p
            break

    if not file_path:
        raise HTTPException(status_code=404, detail="素材文件不存在")

    img = PILImage.open(file_path)
    w, h = img.size

    base_name = Path(asset["filename"]).stem
    upload_dir = Path(settings.UPLOAD_DIR) / "长图裁剪"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Use custom segment heights or auto-split
    heights = req.seg_heights if req.seg_heights else [int(w * 2)] * min(10, max(2, h // (w * 2)))

    segments = []
    y = 0
    overlap = 0
    for seg_num, seg_h in enumerate(heights[:10], 1):
        if y >= h:
            break
        bottom = min(y + seg_h, h)
        crop = img.crop((0, y, w, bottom))

        buf = io.BytesIO()
        crop.save(buf, format='JPEG', quality=90, optimize=True)
        seg_data = buf.getvalue()

        seg_name = f"{base_name}_第{seg_num}段.jpg"
        seg_path = upload_dir / seg_name
        with open(seg_path, "wb") as f:
            f.write(seg_data)

        rel_path = str(seg_path.relative_to(Path(settings.UPLOAD_DIR))).replace("\\", "/")

        await upsert_asset({
            "filename": seg_name,
            "filepath": rel_path,
            "category": asset["category"],
            "sub_category": asset.get("sub_category"),
            "keywords": f"{asset.get('keywords', '')},长图裁剪{seg_num}",
            "file_size": len(seg_data),
            "file_type": "image",
        })

        segments.append({"filename": seg_name, "filepath": rel_path, "size": len(seg_data)})
        y += seg_h - overlap

    # Trigger rebuild of image descriptions and knowledge base
    import asyncio
    asyncio.create_task(_rebuild_indexes_async())

    return {"message": f"已将长图裁剪为{len(segments)}段，AI正在学习新素材...", "segments": segments}


async def _rebuild_indexes_async():
    """后台重建图片描述索引和知识库"""
    try:
        from app.core.image_descriptor import build_image_descriptions, build_vector_index
        descs = await build_image_descriptions()
        if descs:
            build_vector_index(descs)
        from app.core.knowledge_base import build_knowledge_base
        build_knowledge_base()
        print("Indexes rebuilt after image split")
    except Exception as e:
        print(f"Index rebuild error: {e}")


@router.get("/description-status")
async def get_description_status():
    from app.core.image_descriptor import get_build_progress
    return get_build_progress()


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
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，仅支持图片")

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
    from app.models.database import get_asset_by_id, delete_asset, mark_filepath_deleted
    asset = await get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    # Only delete physical file if it's in uploads (not source assets)
    file_path = Path(settings.UPLOAD_DIR) / asset["filepath"]
    if file_path.exists():
        os.remove(file_path)

    # Track deleted filepath to prevent re-scan
    await mark_filepath_deleted(asset["filepath"])

    await delete_asset(asset_id)
    return {"message": "已删除"}
