"""Topic suggester: AI-driven content calendar based on dates, seasons, and asset inventory."""

import json
import pickle
import re
from datetime import datetime, timedelta
from pathlib import Path
from app.core.config import settings

# Chinese holiday/event calendar
HOLIDAYS = {
    "01-01": "元旦新年",
    "02-14": "情人节",
    "03-08": "三八妇女节",
    "03-15": "315消费者权益日",
    "04-01": "愚人节",
    "05-01": "五一劳动节",
    "05-04": "五四青年节",
    "06-01": "六一儿童节",
    "06-18": "618年中大促",
    "07-01": "建党节",
    "08-01": "八一建军节",
    "09-10": "教师节",
    "10-01": "国庆节",
    "11-11": "双十一购物节",
    "12-12": "双十二促销",
    "12-25": "圣诞节",
}

# 24 solar terms (approximate dates)
SOLAR_TERMS = [
    ("01-05", "小寒"), ("01-20", "大寒"), ("02-04", "立春"),
    ("02-19", "雨水"), ("03-06", "惊蛰"), ("03-21", "春分"),
    ("04-05", "清明"), ("04-20", "谷雨"), ("05-06", "立夏"),
    ("05-21", "小满"), ("06-06", "芒种"), ("06-21", "夏至"),
    ("07-07", "小暑"), ("07-23", "大暑"), ("08-07", "立秋"),
    ("08-23", "处暑"), ("09-08", "白露"), ("09-23", "秋分"),
    ("10-08", "寒露"), ("10-23", "霜降"), ("11-07", "立冬"),
    ("11-22", "小雪"), ("12-07", "大雪"), ("12-22", "冬至"),
]

SEASONS = {
    (3, 4, 5): "春季",
    (6, 7, 8): "夏季",
    (9, 10, 11): "秋季",
    (12, 1, 2): "冬季",
}

SUGGESTIONS_CACHE = Path(settings.SQLITE_DB_PATH).parent / "suggestions_cache.pkl"
CACHE_TTL_DAYS = 7


SUGGESTION_TEMPLATES = {
    "新品上市": "产品推广类 — 适合突出技术创新和产品优势",
    "节日促销": "活动促销类 — 适合结合节日氛围和优惠活动",
    "喝水知识科普": "健康科普类 — 适合传递品牌专业度和健康理念",
    "装机案例": "案例展示类 — 适合展示真实客户成功案例",
    "获奖推送": "品牌荣誉类 — 适合提升品牌权威性和行业地位",
    "营销案例": "客户合作类 — 适合展示解决方案落地效果",
}


async def get_suggestions(force_refresh: bool = False) -> list[dict]:
    """Generate topic suggestions for the upcoming week. Cached for 7 days."""
    if not force_refresh and SUGGESTIONS_CACHE.exists():
        try:
            with open(SUGGESTIONS_CACHE, "rb") as f:
                cached = pickle.load(f)
            cache_time = cached.get("_cached_at", 0)
            if datetime.now().timestamp() - cache_time < CACHE_TTL_DAYS * 86400:
                return cached.get("suggestions", [])
        except Exception:
            pass

    suggestions = await _compute_suggestions()

    SUGGESTIONS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {"suggestions": suggestions, "_cached_at": datetime.now().timestamp()}
    with open(SUGGESTIONS_CACHE, "wb") as f:
        pickle.dump(cache_data, f)

    return suggestions


async def _compute_suggestions() -> list[dict]:
    """Compute topic suggestions (no caching)."""
    today = datetime.now()
    suggestions = []

    # 1. Upcoming holidays/events in next 14 days
    for i in range(14):
        d = today + timedelta(days=i)
        key = d.strftime("%m-%d")
        if key in HOLIDAYS:
            suggestions.append({
                "content_type": "节日促销",
                "topic": f"{HOLIDAYS[key]}特惠活动",
                "reason": f"{d.strftime('%m月%d日')}是{HOLIDAYS[key]}，是促销推广的好时机",
                "urgency": "high" if i <= 3 else "medium",
            })

    # 2. Current solar term
    for date_str, name in SOLAR_TERMS:
        key = today.strftime("%m-%d")
        if date_str == key or (date_str > key and date_str <= (today + timedelta(days=7)).strftime("%m-%d")):
            suggestions.append({
                "content_type": "喝水知识科普",
                "topic": f"{name}时节，如何科学饮水保持健康",
                "reason": f"正值{name}节气，是写健康科普内容的好时机",
                "urgency": "medium",
            })
            break

    # 3. Seasonal health tips
    month = today.month
    current_season = None
    for months, name in SEASONS.items():
        if month in months:
            current_season = name
            break
    if current_season:
        suggestions.append({
            "content_type": "喝水知识科普",
            "topic": f"{current_season}办公饮水指南：企业如何保障员工健康饮水",
            "reason": f"{current_season}是饮水需求变化的季节，适合科普+产品植入",
            "urgency": "low",
        })

    # 4. Evergreen enterprise content
    from app.models.database import search_assets

    product_assets = await search_assets(category="产品图", file_type="image")
    if product_assets:
        suggestions.append({
            "content_type": "新品上市",
            "topic": "朴道智能直饮机：为企业打造健康饮水新标准",
            "reason": "素材库有新图片素材，适合发布产品推广文章",
            "urgency": "medium",
        })

    suggestions.append({
        "content_type": "装机案例",
        "topic": "名企饮水升级案例：朴道如何助力企业提升员工满意度",
        "reason": "客户案例类文章能有效增强潜在客户信任感",
        "urgency": "low",
    })

    return suggestions[:8]


PROMPT_TEMPLATES = {
    "新品上市": [
        "朴道{product}产品特写，科技蓝背景，专业影棚灯光，简洁构图 --ar 16:9 --style business",
        "现代企业办公场景中员工使用{product}直饮机，自然光，商务氛围 --ar 16:9",
        "{product}核心滤芯技术微距特写，科技感，蓝色调，精密工业风 --ar 16:9",
        "朴道{product}产品白色背景商业摄影，多角度展示 --ar 1:1 --style business",
        "企业茶水间场景，{product}直饮机融入环境，温馨自然 --ar 16:9",
    ],
    "节日促销": [
        "{occasion}促销海报风格，朴道蓝#0066CC为主色调，净水产品与礼物元素 --ar 3:4",
        "{occasion}优惠活动弹窗设计，清爽商务风，现代简洁 --ar 16:9",
        "节日氛围企业饮水产品推广图，喜庆配色，高端质感 --ar 16:9",
    ],
    "喝水知识科普": [
        "玻璃杯中清澈的水滴特写，蓝色背景，健康清新 --ar 16:9",
        "人体水分补充示意图，简约插画风格，蓝白配色 --ar 16:9",
        "夏季饮水健康科普信息图，清新蓝色调，现代设计 --ar 3:4",
        "矿物质保留对比示意图，科技科普风格，蓝色系 --ar 16:9",
    ],
    "装机案例": [
        "企业客户安装现场实拍风格，{product}直饮机，专业商务感 --ar 16:9",
        "办公楼宇饮水设备布局示意图，现代企业环境 --ar 16:9",
        "客户员工使用直饮机场景，真实自然氛围 --ar 16:9",
    ],
    "获奖推送": [
        "荣誉奖项展示海报风格，朴道蓝主色调，金色点缀 --ar 3:4",
        "企业获奖证书与产品组合图，专业商务风格 --ar 16:9",
        "品牌荣誉历程时间轴信息图，科技企业风格 --ar 16:9",
    ],
    "营销案例": [
        "合作客户品牌联合展示图，高端商务风 --ar 16:9",
        "解决方案效果对比示意图，数据可视化风格 --ar 16:9",
        "客户场景实拍风格，{product}产品融入工作环境 --ar 16:9",
    ],
}


def generate_image_prompts_sync(topic: str, content_type: str, count: int = 3) -> list[str]:
    """Generate image creation prompts from templates (no LLM, instant)."""
    templates = PROMPT_TEMPLATES.get(content_type, PROMPT_TEMPLATES["新品上市"])

    # Extract product name or occasion from topic
    product = "名士K2" if "K2" in topic else ("H7" if "H7" in topic else "朴道直饮机")
    # Extract short event name for occasion placeholder
    occasion = topic.split("特惠")[0].split("活动")[0].strip()[:12]

    prompts = []
    for t in templates:
        filled = t.replace("{product}", product).replace("{occasion}", occasion)
        prompts.append(filled)

    return prompts[:count]


async def generate_image_prompts(topic: str, content_type: str, count: int = 3) -> list[str]:
    """Async wrapper for sync function."""
    return generate_image_prompts_sync(topic, content_type, count)


async def get_today_suggested_articles() -> list[dict]:
    """Get concrete article generation parameters for today's top suggestions."""
    suggestions = await get_suggestions()
    articles = []

    for i, s in enumerate(suggestions[:3]):
        params = {
            "content_type": s["content_type"],
            "tone": "专业、科技感" if s["content_type"] in ["新品上市", "装机案例"] else (
                "活泼、促销感" if s["content_type"] == "节日促销" else "科普、亲和"
            ),
            "product_name": "" if s["content_type"] not in ["新品上市", "装机案例"] else "朴道直饮机",
            "key_points": [],
            "topic": s["topic"],
        }
        articles.append({
            "title": s["topic"],
            "reason": s["reason"],
            "content_type": s["content_type"],
            "urgency": s["urgency"],
            "params": params,
        })

    return articles
