"""Semantic image descriptor: LLM-generated descriptions + TF-IDF vectors.

For each image in the asset library, generates a rich description using the LLM
(once, cached), then builds a TF-IDF index for fast semantic matching between
article paragraphs and images.
"""

import asyncio
import json
import pickle
import re
from pathlib import Path
from app.core.config import settings

CACHE_PATH = Path(settings.SQLITE_DB_PATH).parent / "image_descriptions.pkl"

# Cached state
_descriptions = None  # list of {filepath, description, vector_keywords}
_vectorizer = None
_matrix = None
_chunks = None

# Progress tracking for LLM description building
_build_progress = {"current": 0, "total": 0, "done": False}


def _build_empty():
    return [], None, None, []


async def _generate_description(asset: dict) -> str:
    """Ask the LLM to describe an image based on its metadata, enabling semantic matching later."""
    from app.core.llm import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    filename = asset.get("filename", "")
    category = asset.get("category", "")
    keywords = asset.get("keywords", "")
    sub = asset.get("sub_category", "")

    prompt = f"""请用一句话（20-40字）描述这张图片的内容，用于图文语义匹配。

图片元数据：
- 文件名: {filename}
- 分类: {category}
- 型号/子分类: {sub}
- 关键词: {keywords}

描述要求：
1. 用中文，简洁精准
2. 包含图片展示的核心元素（产品、场景、功能等）
3. 便于后续与文章段落进行语义匹配
4. 仅输出描述文字，不要任何额外内容"""

    try:
        llm = get_llm(temperature=0.3, max_tokens=80)
        messages = [SystemMessage(content="你是图片内容描述专家，输出简洁精准的中文描述。"), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)
        return response.content.strip()
    except Exception:
        # Fallback: use metadata
        parts = [f"{category}图片", filename]
        if keywords:
            parts.append(f"关键词:{keywords}")
        return " ".join(parts)


def get_build_progress() -> dict:
    return dict(_build_progress)


async def build_image_descriptions() -> list[dict]:
    """Generate LLM descriptions for all images (cached). Returns list of {filepath, description}."""
    global _descriptions, _build_progress

    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "rb") as f:
                cached = pickle.load(f)
            if cached and len(cached) > 0:
                _descriptions = cached
                _build_progress = {"current": len(cached), "total": len(cached), "done": True}
                print(f"Loaded {len(cached)} cached image descriptions")
                return cached
        except Exception:
            pass

    from app.models.database import search_assets

    assets = await search_assets(file_type="image")
    if not assets:
        _build_progress = {"current": 0, "total": 0, "done": True}
        return []

    _build_progress = {"current": 0, "total": len(assets), "done": False}

    descriptions = []
    for i, asset in enumerate(assets):
        desc = await _generate_description(asset)
        descriptions.append({
            "filepath": asset["filepath"],
            "description": desc,
            "category": asset.get("category", ""),
            "filename": asset.get("filename", ""),
        })
        _build_progress["current"] = i + 1
        if (i + 1) % 5 == 0:
            print(f"  Described {i + 1}/{len(assets)} images...")

    # Cache
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(descriptions, f)

    _descriptions = descriptions
    _build_progress["done"] = True
    print(f"Built {len(descriptions)} image descriptions")
    return descriptions


def build_vector_index(descriptions: list[dict]):
    """Build TF-IDF index from image descriptions for fast matching."""
    global _vectorizer, _matrix, _chunks
    from sklearn.feature_extraction.text import TfidfVectorizer

    chunks = [d["description"] for d in descriptions]
    if not chunks:
        _vectorizer, _matrix, _chunks = None, None, []
        return

    vectorizer = TfidfVectorizer(max_features=300, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(chunks)
    _vectorizer = vectorizer
    _matrix = matrix
    _chunks = chunks
    _descriptions = descriptions


def match_by_semantics(paragraph: str, top_k: int = 3) -> list[dict]:
    """Find the most semantically relevant images for a paragraph.

    Returns list of {filepath, description, score} sorted by relevance.
    """
    global _vectorizer, _matrix, _chunks, _descriptions

    if not _vectorizer or not _descriptions:
        return []

    from sklearn.metrics.pairwise import cosine_similarity

    try:
        query_vec = _vectorizer.transform([paragraph])
        scores = cosine_similarity(query_vec, _matrix)[0]
        top_indices = scores.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if scores[idx] > 0.03:
                results.append({
                    "filepath": _descriptions[idx]["filepath"],
                    "description": _descriptions[idx]["description"],
                    "score": float(scores[idx]),
                    "filename": _descriptions[idx].get("filename", ""),
                })
        return results
    except Exception:
        return []


async def _build_metadata_index():
    """Fast fallback: index from image metadata without LLM calls."""
    global _descriptions, _vectorizer, _matrix, _chunks
    from app.models.database import search_assets

    assets = await search_assets(file_type="image")
    descs = []
    for a in (assets or []):
        parts = [f"{a['category']}图片", a['filename']]
        if a.get('keywords'):
            parts.append(f"关键词:{a['keywords']}")
        if a.get('sub_category'):
            parts.append(f"型号:{a['sub_category']}")
        descs.append({
            "filepath": a["filepath"],
            "description": " ".join(parts),
            "category": a.get("category", ""),
            "filename": a.get("filename", ""),
        })

    build_vector_index(descs)
    return descs


async def ensure_image_descriptions():
    """Ensure image descriptions are built and vector index is ready."""
    global _descriptions, _vectorizer

    if _vectorizer is not None and _descriptions is not None:
        return

    # Try loading cached LLM descriptions
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "rb") as f:
                cached = pickle.load(f)
            if cached:
                build_vector_index(cached)
                _descriptions = cached
                print(f"Loaded {len(cached)} cached LLM descriptions")
                return
        except Exception:
            pass

    # Use metadata fallback immediately
    await _build_metadata_index()
    print(f"Built metadata index for {len(_descriptions or [])} images")

    # Build LLM descriptions in background for better matching later
    import asyncio
    asyncio.create_task(_build_and_cache())


async def _build_and_cache():
    """Background task to build LLM descriptions."""
    global _descriptions
    descs = await build_image_descriptions()
    if descs:
        build_vector_index(descs)
        _descriptions = descs


async def match_images_semantic(
    paragraphs: list[str],
    used_filepaths: set = None,
) -> list[dict]:
    """Match images to paragraphs using semantic understanding.

    Args:
        paragraphs: List of text paragraphs to match images for
        used_filepaths: Set of already-used image filepaths (for dedup)

    Returns:
        List of {position, source, alt_text, filename, file_type} for each paragraph
    """
    await ensure_image_descriptions()

    if used_filepaths is None:
        used_filepaths = set()

    results = []
    for para in paragraphs:
        candidates = match_by_semantics(para, top_k=5)
        best = None
        for c in candidates:
            if c["filepath"] not in used_filepaths:
                best = c
                break
        if not best and candidates:
            best = candidates[0]

        if best:
            used_filepaths.add(best["filepath"])
            results.append({
                "position": para[:30],
                "source": _make_url(best["filepath"]),
                "alt_text": best.get("description", best.get("filename", "")),
                "filename": best.get("filename", ""),
                "file_type": "image",
            })

    return results


def _make_url(filepath: str) -> str:
    return f"/api/assets/serve/{filepath}"
