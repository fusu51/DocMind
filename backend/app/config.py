"""全局配置 — 从 .env 加载环境变量"""
import os
from dotenv import load_dotenv

load_dotenv()

# ===== Embedding 模型 =====
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")

# ===== LLM 对话模型 =====
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")        # 空字符串表示用官方默认地址

# ===== 向量 & 存储 =====
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/conversations.db")

# ===== 服务 =====
PORT = int(os.getenv("PORT", "8001"))

# ===== CORS =====
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8001")

# ===== Reranker 重排序模型 =====
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "bge-reranker-v2-m3")
RERANKER_BASE_URL = os.getenv("RERANKER_BASE_URL", "")
RERANKER_API_KEY = os.getenv("RERANKER_API_KEY", "")  # 空则 fallback 到 EMBEDDING_API_KEY

# ===== 生成参数 =====
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "3000"))

# ===== 访问控制 =====
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")

# ===== 拒答阈值 =====
ABSTAIN_HARD_THRESHOLD = float(os.getenv("ABSTAIN_HARD_THRESHOLD", "0.1"))
ABSTAIN_SOFT_THRESHOLD = float(os.getenv("ABSTAIN_SOFT_THRESHOLD", "0.3"))
