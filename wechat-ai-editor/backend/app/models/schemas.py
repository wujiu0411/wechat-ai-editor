from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    NEW_PRODUCT = "新品上市"
    FESTIVAL_PROMO = "节日促销"
    HEALTH_SCIENCE = "喝水知识科普"
    INSTALL_CASE = "装机案例"
    AWARD_PUSH = "获奖推送"
    MARKETING_CASE = "营销案例"


class ArticleInput(BaseModel):
    content_type: ContentType = Field(..., description="内容类型")
    product_name: Optional[str] = Field(None, description="产品名称")
    key_points: Optional[list[str]] = Field(None, description="核心卖点")
    target_audience: Optional[str] = Field(None, description="目标受众")
    tone: Optional[str] = Field("专业、科技感", description="语气风格")
    occasion: Optional[str] = Field(None, description="节日/场合")
    promotion_detail: Optional[str] = Field(None, description="促销详情")
    deadline: Optional[str] = Field(None, description="促销截止日期")
    topic: Optional[str] = Field(None, description="科普主题")
    key_message: Optional[str] = Field(None, description="核心信息")
    product_association: Optional[str] = Field(None, description="产品关联")
    image_requirement: Optional[str] = Field(None, description="图片需求描述")
    template_id: Optional[str] = Field("tech_pro", description="排版模板ID")
    customer_name: Optional[str] = Field(None, description="客户名称（装机案例）")
    install_location: Optional[str] = Field(None, description="装机地址（装机案例）")
    equipment_model: Optional[str] = Field(None, description="设备型号（装机案例）")
    install_results: Optional[str] = Field(None, description="使用效果（装机案例）")
    award_name: Optional[str] = Field(None, description="获奖名称（获奖推送）")
    award_organization: Optional[str] = Field(None, description="颁奖机构（获奖推送）")
    award_significance: Optional[str] = Field(None, description="获奖意义（获奖推送）")
    case_name: Optional[str] = Field(None, description="案例名称（营销案例）")
    client_name: Optional[str] = Field(None, description="合作客户（营销案例）")
    case_challenge: Optional[str] = Field(None, description="客户挑战（营销案例）")
    case_solution: Optional[str] = Field(None, description="解决方案（营销案例）")
    case_results: Optional[str] = Field(None, description="案例成果（营销案例）")


class ImageInfo(BaseModel):
    position: str = Field(..., description="图片插入位置")
    source: str = Field(..., description="图片来源路径")
    alt_text: str = Field(..., description="替代文本")


class ArticleOutput(BaseModel):
    article_title: str = Field(..., description="文章标题")
    article_content_markdown: str = Field(..., description="Markdown格式正文")
    html_output: str = Field(..., description="已排版HTML")
    images: list[ImageInfo] = Field(default_factory=list, description="图片列表")
    seo_keywords: list[str] = Field(default_factory=list, description="SEO关键词")
    estimated_reading_time: str = Field(..., description="预计阅读时间")
    call_to_action: str = Field(..., description="行动召唤文案")
    quality_report: Optional[dict] = Field(None, description="质量检查报告")


class AssetItem(BaseModel):
    id: Optional[int] = None
    filename: str
    filepath: str
    category: str = Field(..., description="素材分类：产品图/logo/海报/单页/视频/其他")
    sub_category: Optional[str] = Field(None, description="子分类，如产品型号")
    keywords: Optional[str] = Field(None, description="检索关键词，逗号分隔")
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    created_at: Optional[datetime] = None


class HistoryItem(BaseModel):
    id: Optional[int] = None
    content_type: str
    input_params: dict
    article_title: str
    article_content_markdown: str
    html_output: str
    images: list[dict] = Field(default_factory=list)
    seo_keywords: list[str] = Field(default_factory=list)
    template_id: str = "tech_pro"
    quality_report: Optional[dict] = None
    created_at: Optional[datetime] = None


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    content_types: list[str]
    preview_color: str = "#0066CC"
