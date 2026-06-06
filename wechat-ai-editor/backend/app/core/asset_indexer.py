import os
import asyncio
from pathlib import Path
from app.core.config import settings
from app.models.database import upsert_asset, init_db, init_sensitive_words


CATEGORY_MAP = {
    "产品详情页参考": "产品图",
    "单页参考": "单页",
    "节日节气海报": "海报",
    "朴道logo": "logo",
    "解决方案": "解决方案",
    "视频参考": "视频",
    "易拉宝": "易拉宝",
    "十问十答": "科普图",
}

PRODUCT_KEYWORDS = {
    "K2": "K2,名士K2,商务直饮机,2000G",
    "H7": "H7,商务直饮机H7",
    "P2": "P2,厨下净水器P2",
    "中央厨房": "中央厨房,商用净水",
    "全屋": "全屋净水,别墅机",
    "气泡水机": "气泡水机,四合一",
    "端午": "端午,节日,节气",
    "五一": "五一,劳动节,节日",
    "小满": "小满,节气",
    "春季促销": "促销,春季",
    "双12": "促销,双12",
    "公司介绍": "公司介绍,朴道,品牌",
    "金融": "金融,解决方案",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".wmv"}
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".md", ".txt"}


def _detect_category(rel_path: str) -> str:
    parts = Path(rel_path).parts
    for part in parts:
        if part in CATEGORY_MAP:
            return CATEGORY_MAP[part]
    return "其他"


def _detect_sub_category(rel_path: str) -> str | None:
    parts = Path(rel_path).parts
    for part in parts:
        for key in PRODUCT_KEYWORDS:
            if key.lower() in part.lower():
                return key
    return None


def _detect_keywords(filename: str) -> str:
    keywords = []
    name_without_ext = Path(filename).stem
    for key, kws in PRODUCT_KEYWORDS.items():
        if key.lower() in filename.lower() or key.lower() in name_without_ext.lower():
            keywords.append(kws)
    return ",".join(keywords) if keywords else name_without_ext


def _detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in DOC_EXTENSIONS:
        return "document"
    return "other"


async def scan_assets():
    assets_dir = Path(settings.ASSETS_DIR)
    if not assets_dir.exists():
        print(f"Assets directory not found: {assets_dir}")
        return 0

    count = 0
    for filepath in assets_dir.rglob("*"):
        if filepath.is_dir():
            continue
        if filepath.name.startswith("."):
            continue

        rel_path = str(filepath.relative_to(assets_dir)).replace("\\", "/")
        category = _detect_category(rel_path)
        sub_category = _detect_sub_category(rel_path)
        keywords = _detect_keywords(filepath.name)
        file_type = _detect_file_type(filepath.name)
        file_size = filepath.stat().st_size

        await upsert_asset({
            "filename": filepath.name,
            "filepath": rel_path,
            "category": category,
            "sub_category": sub_category,
            "keywords": keywords,
            "file_size": file_size,
            "file_type": file_type,
        })
        count += 1

    print(f"Indexed {count} assets")
    return count


async def init_app():
    await init_db()
    await init_sensitive_words()
    await scan_assets()


if __name__ == "__main__":
    asyncio.run(init_app())
