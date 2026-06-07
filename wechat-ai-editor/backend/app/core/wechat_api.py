import time
import io
import httpx
import re
from pathlib import Path
from PIL import Image
from app.core.config import settings

WECHAT_IMAGE_MAX_BYTES = 2 * 1024 * 1024  # 2MB for permanent material


def _split_tall_image(data: bytes, filename: str) -> list[tuple[bytes, str]]:
    """将超长图片（高>2倍宽）裁剪为多个适合公众号显示的片段。

    长图如产品详情页（750x20000）在公众号中观感很差。
    自动裁剪为多段 4:3 比例的图片，每段保留完整宽度。
    """
    img = Image.open(io.BytesIO(data))
    w, h = img.size

    if h <= w * 2.5:
        return [(data, filename)]

    # Target each segment to be ~1:2 aspect ratio (fewer, taller segments)
    segment_height = int(w * 2)
    overlap = int(segment_height * 0.1)  # 10% overlap between segments
    segments = []
    y = 0
    seg_num = 0

    while y < h:
        seg_num += 1
        bottom = min(y + segment_height, h)
        crop = img.crop((0, y, w, bottom))

        buf = io.BytesIO()
        crop.save(buf, format='JPEG', quality=90, optimize=True)
        segment_data = buf.getvalue()

        # If over 2MB, compress
        if len(segment_data) > WECHAT_IMAGE_MAX_BYTES:
            buf2 = io.BytesIO()
            crop.save(buf2, format='JPEG', quality=75, optimize=True)
            segment_data = buf2.getvalue()

        name = Path(filename).stem
        segments.append((segment_data, f"{name}_p{seg_num}.jpg"))

        y += segment_height - overlap

        if seg_num >= 10:  # Safety limit: max 10 segments
            if y < h:
                bottom = h
                crop = img.crop((0, y, w, bottom))
                buf = io.BytesIO()
                crop.save(buf, format='JPEG', quality=90, optimize=True)
                segments.append((buf.getvalue(), f"{name}_p{seg_num + 1}.jpg"))
            break

    return segments


def _compress_image_if_needed(data: bytes, filename: str) -> tuple[bytes, str]:
    """如果图片超过微信2MB限制，智能压缩后返回。
    优先保清晰度：先缩宽度到1080px（公众号2x retina），再逐级降质量。
    长图（高度>2倍宽度）不缩放宽度，保持纵向细节。
    """
    if len(data) <= WECHAT_IMAGE_MAX_BYTES:
        return data, filename

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    is_tall = h > w * 2  # long/tall product detail images

    # Scale width to 1080 (2x retina), but skip for tall images to keep vertical detail
    target_width = 1080
    if w > target_width and not is_tall:
        ratio = target_width / w
        img = img.resize((target_width, int(h * ratio)), Image.LANCZOS)
        w, h = img.size

    # If still too big and not a tall image, try wider scaling
    buf = io.BytesIO()
    save_format = img.format or 'JPEG'
    if save_format.upper() in ('PNG', 'WEBP'):
        img_rgb = img.convert('RGB')
        img_rgb.save(buf, format='JPEG', quality=92, optimize=True)
    else:
        img.save(buf, format='JPEG', quality=92, optimize=True)
    compressed = buf.getvalue()

    if len(compressed) <= WECHAT_IMAGE_MAX_BYTES:
        return compressed, Path(filename).stem + '.jpg'

    # Second try: for normal images scale to 677 (1x), for tall only compress harder
    if not is_tall:
        ratio = 677 / w
        img = img.resize((677, int(h * ratio)), Image.LANCZOS)

    for quality in [88, 80, 72, 60]:
        buf = io.BytesIO()
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        compressed = buf.getvalue()
        if len(compressed) <= WECHAT_IMAGE_MAX_BYTES:
            return compressed, Path(filename).stem + '.jpg'

    raise Exception(f"图片过大，压缩后仍超过2MB限制（原始: {len(data) / 1024 / 1024:.1f}MB）")


class WeChatAPI:
    """微信公众号API封装"""

    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self):
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    @property
    def app_id(self) -> str:
        return settings.WECHAT_APP_ID

    @property
    def app_secret(self) -> str:
        return settings.WECHAT_APP_SECRET

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.app_secret
                    and self.app_id != "your_wechat_app_id"
                    and self.app_secret != "your_wechat_app_secret")

    async def get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token

        url = f"{self.BASE_URL}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"获取access_token失败: {data.get('errmsg', 'unknown')} (code={data['errcode']})")

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 7200)
        return self._access_token

    async def upload_image(self, image_data: bytes, filename: str) -> dict:
        """上传图片为永久素材，返回 {media_id, url}"""
        token = await self.get_access_token()
        url = f"{self.BASE_URL}/material/add_material?access_token={token}&type=image"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                files={"media": (filename, image_data)},
            )
            data = resp.json()
            print(f"WeChat upload response: {data}")

        if data.get("errcode", 0) != 0:
            raise Exception(f"上传图片失败: {data.get('errmsg', 'unknown')} (code={data.get('errcode')})")

        return {"media_id": data["media_id"], "url": data.get("url", "")}

    async def add_draft(self, articles: list[dict]) -> str:
        """创建草稿文章，返回 media_id"""
        token = await self.get_access_token()
        url = f"{self.BASE_URL}/draft/add?access_token={token}"

        body = {"articles": articles}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body)
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"创建草稿失败: {data.get('errmsg', 'unknown')} (code={data['errcode']})")

        return data.get("media_id", "")

    async def get_draft_list(self, offset: int = 0, count: int = 20) -> dict:
        """获取草稿列表"""
        token = await self.get_access_token()
        url = f"{self.BASE_URL}/draft/batchget?access_token={token}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"offset": offset, "count": count, "no_content": 1})
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"获取草稿列表失败: {data.get('errmsg', 'unknown')}")

        return data


wechat = WeChatAPI()


def _find_image_file(src: str) -> Path | None:
    """根据HTML中的图片src查找本地文件"""
    # Strip URL prefix: /api/assets/serve/xxx or http://host/api/assets/serve/xxx -> xxx
    clean = src.split("/api/assets/serve/")[-1].lstrip("./")
    for base_dir in [Path(settings.UPLOAD_DIR), Path(settings.ASSETS_DIR)]:
        file_path = base_dir / clean
        if file_path.exists():
            return file_path
    return None


async def sync_article_to_draft(
    title: str,
    html_content: str,
    author: str = "朴道水汇",
    digest: str = "",
) -> dict:
    """将文章HTML同步到微信公众号草稿箱

    1. 提取HTML中的图片src
    2. 从本地磁盘读取图片并上传到微信永久素材库
    3. 用第一张图作为封面
    4. 创建草稿
    """
    if not wechat.configured:
        raise Exception("微信公众号未配置，请在.env中设置WECHAT_APP_ID和WECHAT_APP_SECRET")

    image_sources = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
    if not image_sources:
        raise Exception("文章中没有图片，微信草稿必须有封面图。请确保文章至少包含一张图片")

    # Upload images and create mapping: original_src -> {media_id, url}
    src_to_info = {}
    for img_src in image_sources:
        file_path = _find_image_file(img_src)
        if not file_path:
            continue
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
            compressed, upload_name = _compress_image_if_needed(image_data, file_path.name)
            result = await wechat.upload_image(compressed, upload_name)
            src_to_info[img_src] = result
        except Exception as e:
            print(f"WeChat upload error for {file_path.name}: {e}")
            raise Exception(f"上传图片失败 ({file_path.name}): {str(e)}")

    if not src_to_info:
        raise Exception("未能上传任何图片到微信素材库")

    # Replace local image URLs with WeChat's public CDN URLs
    processed_html = html_content
    for img_src, info in src_to_info.items():
        wechat_url = info["url"]
        if wechat_url:
            processed_html = processed_html.replace(f'src="{img_src}"', f'src="{wechat_url}"')

    thumb_media_id = list(src_to_info.values())[0]["media_id"]

    digest_text = digest or re.sub(r'<[^>]+>', '', html_content)[:120].strip() + "..."

    article = {
        "title": title,
        "author": author,
        "digest": digest_text,
        "content": processed_html,
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }

    draft_media_id = await wechat.add_draft([article])

    return {
        "draft_media_id": draft_media_id,
        "image_count": len(src_to_info),
        "message": f"已同步到公众号草稿箱 (草稿ID: {draft_media_id})",
    }
