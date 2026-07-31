"""FastAPI 应用入口"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Header, HTTPException

from .config import ALLOWED_ORIGINS, ACCESS_TOKEN
from .api import upload, chat, documents, conversations


async def verify_token(x_docmind_token: str = Header(default="")):
    """仅上传和问答接口校验令牌，其余放行"""
    if ACCESS_TOKEN and x_docmind_token != ACCESS_TOKEN:
        raise HTTPException(403, "缺少有效令牌，联系 WX：19267826845 获取")


# 抑制 ChromaDB telemetry 日志
os.environ["CHROMADB_TELEMETRY_IMPL"] = "none"
os.environ["ANONYMIZED_TELEMETRY"] = "False"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时从 ChromaDB 重建 BM25 索引"""
    print("[Startup] Rebuilding BM25 index from ChromaDB...")
    try:
        from .rag.retriever import rebuild_bm25
        count = rebuild_bm25()
        print(f"[Startup] BM25 index rebuilt: {count} chunks")
    except Exception as e:
        print(f"[Startup] BM25 rebuild failed (may be empty DB): {e}")
    yield


app = FastAPI(title="DocMind RAG API", version="0.1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")


@app.get("/api/health")
async def health():
    from .rag.bm25_index import get_bm25_index
    bm25 = get_bm25_index()
    return {"status": "ok", "bm25_chunks": bm25.size}
