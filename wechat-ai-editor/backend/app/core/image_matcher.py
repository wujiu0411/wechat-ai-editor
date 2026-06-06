from app.models.database import search_assets


def _make_url(filepath: str) -> str:
    return f"/api/assets/serve/{filepath}"


async def match_images(image_positions: list[dict], product_name: str = "", content_type: str = "") -> list[dict]:
    matched = []
    used_filepaths = set()

    # Pre-fetch a large pool of relevant images by content_type and product_name
    pool = await _build_pool(product_name, content_type)

    for pos_info in image_positions:
        description = pos_info.get("description", "").lower()
        best = _pick_best(description, pool, used_filepaths)

        if best:
            used_filepaths.add(best["filepath"])
            matched.append({
                "position": pos_info.get("position", ""),
                "source": _make_url(best["filepath"]),
                "alt_text": description,
                "filename": best["filename"],
                "file_type": best.get("file_type", "image"),
            })
        else:
            matched.append({
                "position": pos_info.get("position", ""),
                "source": f"[缺失：{description}图片]",
                "alt_text": description,
                "filename": None,
                "file_type": None,
            })

    if not matched and product_name:
        fallback = await search_assets(query=product_name, category="产品图")
        for i, asset in enumerate(fallback[:5]):
            matched.append({
                "position": f"正文配图{i+1}",
                "source": _make_url(asset["filepath"]),
                "alt_text": asset["filename"],
                "filename": asset["filename"],
                "file_type": asset.get("file_type", "image"),
            })

    if not matched:
        logos = await search_assets(category="logo")
        posters = await search_assets(category="海报")
        for asset in (posters + logos)[:3]:
            matched.append({
                "position": f"正文配图",
                "source": _make_url(asset["filepath"]),
                "alt_text": asset["filename"],
                "filename": asset["filename"],
                "file_type": asset.get("file_type", "image"),
            })

    return matched


def _score_candidate(description: str, asset: dict, product_name: str) -> int:
    """Score how well an asset matches a description. Higher = better."""
    score = 0
    desc_lower = description.lower()
    keywords = (asset.get("keywords", "") or "").lower()
    filename = (asset.get("filename", "") or "").lower()
    category = (asset.get("category", "") or "").lower()
    combined = f"{keywords} {filename} {category}"

    # Exact keyword match
    for word in desc_lower.split():
        if word in keywords:
            score += 10
        if word in filename:
            score += 5
        if word in category:
            score += 3

    # Product match
    if product_name and product_name.lower() in combined:
        score += 5

    # Image type preferred
    if asset.get("file_type") == "image":
        score += 2

    return score


def _pick_best(description: str, pool: list[dict], used: set) -> dict | None:
    """Pick the best-scoring unused asset from the pool."""
    best = None
    best_score = -1

    for asset in pool:
        if asset["filepath"] in used:
            continue
        s = _score_candidate(description, asset, "")
        if s > best_score:
            best_score = s
            best = asset

    return best


def _is_tall_image(filepath: str) -> bool:
    """Check if an image is a tall/long image (height > 2x width)."""
    from pathlib import Path
    from app.core.config import settings
    try:
        from PIL import Image
        for base in [Path(settings.UPLOAD_DIR), Path(settings.ASSETS_DIR)]:
            fp = base / filepath
            if fp.exists():
                img = Image.open(fp)
                w, h = img.size
                return h > w * 2.5
    except Exception:
        pass
    return False


async def _build_pool(product_name: str, content_type: str) -> list[dict]:
    """Build a large pool of candidate images, excluding tall/long images."""
    type_map = {
        "节日促销": "海报",
        "新品上市": "产品图",
        "喝水知识科普": "科普图",
        "装机案例": "产品图",
        "获奖推送": "海报",
        "营销案例": "产品图",
    }
    prefer_category = type_map.get(content_type, "")

    seen = set()
    pool = []

    def add_to_pool(assets):
        for a in assets:
            if a["filepath"] not in seen:
                seen.add(a["filepath"])
                # Skip tall images for auto-selection
                if not _is_tall_image(a["filepath"]):
                    pool.append(a)

    if product_name:
        for term in [product_name] + product_name.split():
            results = await search_assets(query=term)
            add_to_pool(results)

    if prefer_category:
        results = await search_assets(category=prefer_category)
        add_to_pool(results)

    all_images = await search_assets()
    add_to_pool([a for a in all_images if a.get("file_type") == "image"])

    return pool
