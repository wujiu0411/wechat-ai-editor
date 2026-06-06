import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "http://8.145.39.17:8080/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "glm-5.1-w8a8")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/wechat_editor.db")
    ASSETS_DIR: str = os.getenv("ASSETS_DIR", "./assets")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_IMAGES_PER_ARTICLE: int = int(os.getenv("MAX_IMAGES_PER_ARTICLE", "10"))
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "2"))
    ARTICLE_MIN_WORDS: int = int(os.getenv("ARTICLE_MIN_WORDS", "500"))
    ARTICLE_MAX_WORDS: int = int(os.getenv("ARTICLE_MAX_WORDS", "1500"))
    GENERATION_TIMEOUT: int = int(os.getenv("GENERATION_TIMEOUT", "120"))
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS", "*") != "*" else ["*"]
    WECHAT_APP_ID: str = os.getenv("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET: str = os.getenv("WECHAT_APP_SECRET", "")


settings = Settings()
