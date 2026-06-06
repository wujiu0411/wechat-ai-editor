"""Knowledge base with TF-IDF retrieval for RAG-based article generation.

Indexes text from company documents (PDFs, docx) and image metadata,
then retrieves relevant chunks at generation time to ground the LLM.
"""

import os
import re
import pickle
import asyncio
from pathlib import Path
from app.core.config import settings

# Lazy imports for optional dependencies
_pdf_available = True
_docx_available = True
_tfidf_available = True

try:
    from PyPDF2 import PdfReader
except ImportError:
    _pdf_available = False

try:
    from docx import Document
except ImportError:
    _docx_available = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    _tfidf_available = False


KB_CACHE_PATH = Path(settings.SQLITE_DB_PATH).parent / "kb_cache.pkl"
CHUNK_SIZE = 300  # characters per chunk


def _extract_pdf_text(filepath: Path) -> str:
    if not _pdf_available:
        return ""
    try:
        reader = PdfReader(str(filepath))
        return " ".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _extract_docx_text(filepath: Path) -> str:
    if not _docx_available:
        return ""
    try:
        doc = Document(str(filepath))
        return " ".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


def _extract_asset_metadata() -> list[str]:
    """Collect image filenames, categories, and keywords as knowledge chunks."""
    from app.models.database import search_assets
    import asyncio

    async def _get():
        return await search_assets(file_type="image")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _get())
                assets = future.result()
        else:
            assets = asyncio.run(_get())
    except RuntimeError:
        try:
            assets = asyncio.run(_get())
        except Exception:
            return []

    chunks = []
    for a in (assets or []):
        info = f"图片: {a['filename']} | 分类: {a['category']}"
        if a.get('sub_category'):
            info += f" | 型号: {a['sub_category']}"
        if a.get('keywords'):
            info += f" | 关键词: {a['keywords']}"
        chunks.append(info)
    return chunks


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE // 2):
        chunk = text[i:i + CHUNK_SIZE]
        if len(chunk) > 50:
            chunks.append(chunk)
    return chunks


def build_knowledge_base() -> dict:
    """Build TF-IDF index from all company documents and asset metadata."""
    if not _tfidf_available:
        print("WARNING: scikit-learn not available, RAG disabled")
        return {"chunks": [], "vectorizer": None, "matrix": None}

    assets_dir = Path(settings.ASSETS_DIR)
    all_chunks = []

    # Extract from documents
    for filepath in assets_dir.rglob("*"):
        if not filepath.is_file():
            continue
        text = ""
        ext = filepath.suffix.lower()
        if ext == ".pdf":
            text = _extract_pdf_text(filepath)
        elif ext in (".docx", ".doc"):
            text = _extract_docx_text(filepath)
        elif ext in (".txt", ".md"):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception:
                pass

        if text:
            all_chunks.extend(_chunk_text(text))

    # Add image metadata
    metadata_chunks = _extract_asset_metadata()
    all_chunks.extend(metadata_chunks)

    if not all_chunks:
        print("WARNING: No documents found for knowledge base")
        return {"chunks": [], "vectorizer": None, "matrix": None}

    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(all_chunks)

    kb = {
        "chunks": all_chunks,
        "vectorizer": vectorizer,
        "matrix": matrix,
    }

    # Cache to disk
    KB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KB_CACHE_PATH, "wb") as f:
        pickle.dump(kb, f)

    print(f"Knowledge base built: {len(all_chunks)} chunks indexed")
    return kb


def load_knowledge_base() -> dict:
    """Load cached knowledge base or build if not exists."""
    if KB_CACHE_PATH.exists():
        try:
            with open(KB_CACHE_PATH, "rb") as f:
                kb = pickle.load(f)
            if kb.get("chunks"):
                return kb
        except Exception:
            pass
    return build_knowledge_base()


def retrieve_context(query: str, kb: dict = None, top_k: int = 5) -> str:
    """Retrieve most relevant knowledge chunks for a query."""
    if kb is None:
        kb = load_knowledge_base()

    if not kb.get("chunks") or kb["matrix"] is None:
        return ""

    try:
        query_vec = kb["vectorizer"].transform([query])
        scores = cosine_similarity(query_vec, kb["matrix"])[0]
        top_indices = scores.argsort()[-top_k:][::-1]

        relevant = []
        for idx in top_indices:
            if scores[idx] > 0.05:  # minimal relevance threshold
                relevant.append(kb["chunks"][idx])

        return "\n---\n".join(relevant) if relevant else ""
    except Exception:
        return ""


def get_rag_context(product_name: str, content_type: str, key_points: list[str] = None) -> str:
    """Get RAG context for article generation.

    Combines multiple queries to find the most relevant knowledge.
    """
    kb = load_knowledge_base()
    if not kb.get("chunks"):
        return ""

    queries = [product_name, content_type]
    if key_points:
        queries.extend(key_points)

    all_results = set()
    for q in queries:
        if not q:
            continue
        result = retrieve_context(q, kb, top_k=2)
        if result:
            for line in result.split("\n---\n"):
                all_results.add(line.strip())

    if not all_results:
        return ""

    # Limit to top 4 most relevant chunks to keep prompt concise
    return "【公司知识库参考内容】\n" + "\n---\n".join(list(all_results)[:5])
