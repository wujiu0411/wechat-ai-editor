import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from app.core.config import settings


DB_PATH = settings.SQLITE_DB_PATH


async def get_db():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '其他',
                sub_category TEXT,
                keywords TEXT,
                file_size INTEGER,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,
                input_params TEXT NOT NULL,
                article_title TEXT NOT NULL,
                article_content_markdown TEXT NOT NULL,
                html_output TEXT NOT NULL,
                images TEXT DEFAULT '[]',
                seo_keywords TEXT DEFAULT '[]',
                template_id TEXT DEFAULT 'tech_pro',
                quality_report TEXT,
                sync_count INTEGER DEFAULT 0,
                last_synced_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sensitive_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'general'
            );

            CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
            CREATE INDEX IF NOT EXISTS idx_assets_keywords ON assets(keywords);
            CREATE INDEX IF NOT EXISTS idx_assets_sub_category ON assets(sub_category);
            CREATE TABLE IF NOT EXISTS deleted_assets (
                filepath TEXT PRIMARY KEY,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_history_content_type ON history(content_type);
            CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at);
        """)
        await db.commit()

        # Migration: add sync_count and last_synced_at for existing databases
        try:
            await db.execute("ALTER TABLE history ADD COLUMN sync_count INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE history ADD COLUMN last_synced_at TIMESTAMP")
            await db.commit()
        except Exception:
            pass
    finally:
        await db.close()


async def insert_history(item: dict) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO history (content_type, input_params, article_title, 
               article_content_markdown, html_output, images, seo_keywords, 
               template_id, quality_report)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item["content_type"],
                json.dumps(item.get("input_params", {}), ensure_ascii=False),
                item["article_title"],
                item["article_content_markdown"],
                item["html_output"],
                json.dumps(item.get("images", []), ensure_ascii=False),
                json.dumps(item.get("seo_keywords", []), ensure_ascii=False),
                item.get("template_id", "tech_pro"),
                json.dumps(item.get("quality_report"), ensure_ascii=False) if item.get("quality_report") else None,
            ),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_history_list(limit: int = 20, offset: int = 0):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        total_cursor = await db.execute("SELECT COUNT(*) FROM history")
        total = (await total_cursor.fetchone())[0]
        return [dict(row) for row in rows], total
    finally:
        await db.close()


async def get_history_by_id(item_id: int):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM history WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_history(item_id: int, updates: dict):
    db = await get_db()
    try:
        for key, value in updates.items():
            await db.execute(
                f"UPDATE history SET {key} = ? WHERE id = ?",
                (value, item_id),
            )
        await db.commit()
    finally:
        await db.close()


async def record_sync(item_id: int):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE history SET sync_count = sync_count + 1, last_synced_at = CURRENT_TIMESTAMP WHERE id = ?",
            (item_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def delete_history(item_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM history WHERE id = ?", (item_id,))
        await db.commit()
    finally:
        await db.close()


async def upsert_asset(asset: dict):
    db = await get_db()
    try:
        existing = await db.execute(
            "SELECT id FROM assets WHERE filepath = ?", (asset["filepath"],)
        )
        row = await existing.fetchone()
        if row:
            await db.execute(
                """UPDATE assets SET filename=?, category=?, sub_category=?, 
                   keywords=?, file_size=?, file_type=? WHERE filepath=?""",
                (
                    asset["filename"],
                    asset["category"],
                    asset.get("sub_category"),
                    asset.get("keywords"),
                    asset.get("file_size"),
                    asset.get("file_type"),
                    asset["filepath"],
                ),
            )
        else:
            await db.execute(
                """INSERT INTO assets (filename, filepath, category, sub_category, 
                   keywords, file_size, file_type) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    asset["filename"],
                    asset["filepath"],
                    asset["category"],
                    asset.get("sub_category"),
                    asset.get("keywords"),
                    asset.get("file_size"),
                    asset.get("file_type"),
                ),
            )
        await db.commit()
    finally:
        await db.close()


async def search_assets(query: str = "", category: str = "", sub_category: str = "", file_type: str = ""):
    db = await get_db()
    try:
        conditions = []
        params = []
        if query:
            conditions.append("(filename LIKE ? OR keywords LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            conditions.append("category = ?")
            params.append(category)
        if sub_category:
            conditions.append("sub_category = ?")
            params.append(sub_category)
        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        cursor = await db.execute(
            f"SELECT * FROM assets WHERE {where_clause} ORDER BY category, filename",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def mark_filepath_deleted(filepath: str):
    db = await get_db()
    try:
        await db.execute("INSERT OR REPLACE INTO deleted_assets (filepath) VALUES (?)", (filepath,))
        await db.commit()
    finally:
        await db.close()


async def is_filepath_deleted(filepath: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT 1 FROM deleted_assets WHERE filepath = ?", (filepath,))
        return (await cursor.fetchone()) is not None
    finally:
        await db.close()


async def delete_asset(asset_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        await db.commit()
    finally:
        await db.close()


async def get_asset_by_id(asset_id: int):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def load_sensitive_words() -> list[str]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT word FROM sensitive_words")
        rows = await cursor.fetchall()
        if rows:
            return [row[0] for row in rows]
        return []
    finally:
        await db.close()


async def init_sensitive_words():
    words = [
        ("最好", "ad_law"), ("第一", "ad_law"), ("顶级", "ad_law"),
        ("最佳", "ad_law"), ("最优", "ad_law"), ("国家级", "ad_law"),
        ("最高级", "ad_law"), ("极致", "ad_law"), ("绝对", "ad_law"),
        ("唯一", "ad_law"), ("独创", "ad_law"), ("万能", "ad_law"),
        ("美的", "competitor"), ("沁园", "competitor"), ("安吉尔", "competitor"),
        ("3M净水", "competitor"), ("A.O.史密斯", "competitor"),
        ("海尔净水", "competitor"), ("小米净水", "competitor"),
    ]
    db = await get_db()
    try:
        for word, cat in words:
            await db.execute(
                "INSERT OR IGNORE INTO sensitive_words (word, category) VALUES (?, ?)",
                (word, cat),
            )
        await db.commit()
    finally:
        await db.close()
