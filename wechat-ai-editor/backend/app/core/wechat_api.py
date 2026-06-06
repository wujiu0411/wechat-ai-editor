import time
import httpx
import re
from app.core.config import settings


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

    async def upload_image(self, image_data: bytes, filename: str) -> str:
        """上传图片为永久素材，返回 media_id"""
        token = await self.get_access_token()
        url = f"{self.BASE_URL}/material/add_material?access_token={token}&type=image"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                files={"media": (filename, image_data)},
            )
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"上传图片失败: {data.get('errmsg', 'unknown')}")

        return data["media_id"]

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


def extract_images_from_html(html: str) -> list[str]:
    """从HTML中提取图片URL"""
    pattern = r'<img[^>]+src="([^"]+)"'
    return re.findall(pattern, html)


async def sync_article_to_draft(
    title: str,
    html_content: str,
    image_mapping: dict[str, bytes],
    author: str = "朴道水汇",
    digest: str = "",
) -> dict:
    """将文章HTML同步到微信公众号草稿箱

    流程:
    1. 提取HTML中的图片
    2. 上传图片到微信永久素材库
    3. 替换HTML中图片URL为微信返回的media_id引用
    4. 创建草稿
    """
    if not wechat.configured:
        raise Exception("微信公众号未配置，请在.env中设置WECHAT_APP_ID和WECHAT_APP_SECRET")

    processed_html = html_content

    uploaded_media_ids = []
    for img_src, img_data in image_mapping.items():
        try:
            media_id = await wechat.upload_image(img_data, "article_image.jpg")
            uploaded_media_ids.append(media_id)
        except Exception as e:
            raise Exception(f"上传图片失败 ({img_src}): {str(e)}")

    image_sources = re.findall(r'<img[^>]+src="([^"]+)"', processed_html)
    for i, img_src in enumerate(image_sources):
        if i < len(uploaded_media_ids):
            processed_html = processed_html.replace(
                f'src="{img_src}"',
                f'src="{img_src}" data-media-id="{uploaded_media_ids[i]}"',
            )

    thumb_media_id = uploaded_media_ids[0] if uploaded_media_ids else ""

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
        "image_count": len(uploaded_media_ids),
        "message": f"已同步到公众号草稿箱 (草稿ID: {draft_media_id})",
    }
