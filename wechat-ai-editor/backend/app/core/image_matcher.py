import re
from app.models.database import search_assets


async def match_images(image_positions: list[dict], product_name: str = "", content_type: str = "") -> list[dict]:
    matched = []

    for pos_info in image_positions:
        description = pos_info.get("description", "").lower()
        candidates = await _find_candidates(description, product_name, content_type)

        if candidates:
            best = candidates[0]
            matched.append({
                "position": pos_info.get("position", ""),
                "source": best["filepath"],
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
                "source": asset["filepath"],
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
                "source": asset["filepath"],
                "alt_text": asset["filename"],
                "filename": asset["filename"],
                "file_type": asset.get("file_type", "image"),
            })

    return matched


async def _find_candidates(description: str, product_name: str, content_type: str) -> list[dict]:
    search_queries = [description]

    product_map = {
        "k2": "K2", "名士": "K2", "h7": "H7", "p2": "P2",
        "厨下": "P2", "全屋": "全屋", "气泡": "气泡水机",
    }
    for key, val in product_map.items():
        if key in description.lower() or key in product_name.lower():
            search_queries.insert(0, val)
            break

    type_map = {
        "节日促销": "海报",
        "新品上市": "产品图",
        "喝水知识科普": "科普图",
        "装机案例": "产品图",
        "获奖推送": "海报",
        "营销案例": "产品图",
    }
    prefer_category = type_map.get(content_type, "")

    for query in search_queries:
        results = await search_assets(query=query)
        if results:
            if prefer_category:
                preferred = [r for r in results if r["category"] == prefer_category]
                if preferred:
                    return preferred
            image_results = [r for r in results if r.get("file_type") == "image"]
            if image_results:
                return image_results
            return results

    if prefer_category:
        results = await search_assets(category=prefer_category)
        if results:
            return results[:3]

    return []
