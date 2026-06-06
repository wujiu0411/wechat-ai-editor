from fastapi import APIRouter
from app.templates.css_templates import TEMPLATES
from app.models.schemas import TemplateInfo

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/list")
async def list_templates():
    result = []
    for tid, tpl in TEMPLATES.items():
        result.append(TemplateInfo(
            id=tid,
            name=tpl["name"],
            description=tpl["description"],
            content_types=tpl["content_types"],
            preview_color=tpl["preview_color"],
        ))
    return result


@router.get("/{template_id}")
async def get_template(template_id: str):
    tpl = TEMPLATES.get(template_id)
    if not tpl:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="模板不存在")
    return TemplateInfo(
        id=template_id,
        name=tpl["name"],
        description=tpl["description"],
        content_types=tpl["content_types"],
        preview_color=tpl["preview_color"],
    )
