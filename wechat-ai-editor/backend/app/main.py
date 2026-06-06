from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import settings
from app.core.asset_indexer import init_app
from app.api import article, asset, history, template, wechat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_app()
    print("App initialized: DB + Assets indexed")
    yield


app = FastAPI(
    title="微信公众号内容生成与排版AI员工",
    description="自动生成图文并茂的公众号文章，并排版输出可直接复制到微信公众号后台的HTML",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(article.router)
app.include_router(asset.router)
app.include_router(history.router)
app.include_router(template.router)
app.include_router(wechat.router)

assets_dir = Path(settings.ASSETS_DIR)
if assets_dir.exists():
    app.mount("/static/assets", StaticFiles(directory=str(assets_dir)), name="assets")

uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.responses import FileResponse
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "model": settings.LLM_MODEL_NAME}
