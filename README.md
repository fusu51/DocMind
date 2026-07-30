# 📚 DocMind — 自建 RAG 文档问答系统

基于 Python + FastAPI + Vue 3 的轻量级 RAG 文档问答系统，支持多格式文档上传、自然语言提问、流式回答和来源引用。

## 特性

- **多格式支持**：PDF / Word / Markdown / TXT
- **四层混合检索**：L0 语义分块 → L1 查询改写 → L2 双路召回 (Dense + BM25) → L3 重排序 (BGE-Reranker)
- **推理模型兼容**：支持 DeepSeek V4-Flash 等推理模型，前端展示思考过程
- **双阶拒答**：基于检索分数自动判定，防止外域问题编造
- **多轮对话**：支持追问，自动携带历史上下文
- **流式输出**：SSE 逐 Token 渲染 + Markdown 解析
- **可观测性**：前端展示完整检索管线（L1→L4 数据流）

## 评估指标

在 55 题 CRUD 测试集上（50 题知识库内 + 5 题外域拒答）：

| 指标 | 分数 |
|------|:---:|
| Faithfulness | 9.7 |
| Answer Correctness | 9.1 |
| Context Precision | 7.9 |
| Context Recall | 8.1 |
| 外域拒答率 | 80% |

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端 | Python + FastAPI + ChromaDB + SQLite |
| 前端 | Vue 3 (Composition API) + Vite |
| Embedding | OpenAI text-embedding-3-small / 阿里云 MaaS |
| LLM | DeepSeek V4-Flash (支持推理链) |
| 重排序 | BGE-Reranker-v2-m3 |
| 关键词检索 | BM25 (jieba 分词 + 字符 2-gram) |

## 项目结构

```
DocMind/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + 启动钩子
│   │   ├── config.py            # 全局配置
│   │   ├── api/                 # 路由层
│   │   │   ├── chat.py          # 问答 SSE 流式
│   │   │   ├── upload.py        # 文档上传 & 索引
│   │   │   ├── documents.py     # 文档管理
│   │   │   └── conversations.py # 对话历史
│   │   ├── rag/                 # RAG 引擎
│   │   │   ├── parser.py        # 文档解析
│   │   │   ├── chunker.py       # L0 语义分块
│   │   │   ├── embeddings.py    # 向量化
│   │   │   ├── retriever.py     # Dense 检索
│   │   │   ├── bm25_index.py    # L2 稀疏检索
│   │   │   ├── query_processor.py # L1 查询处理
│   │   │   ├── reranker.py      # L3 重排序
│   │   │   ├── hybrid_search.py # 检索编排
│   │   │   └── generator.py     # L4 上下文压缩 + LLM 调用
│   │   ├── db/                  # 数据库
│   │   │   ├── models.py        # 表定义
│   │   │   └── repository.py    # CRUD
│   │   └── models/
│   │       └── schemas.py       # Pydantic 模型
│   ├── tests/
│   │   ├── run_eval.py          # 评估脚本
│   │   └── import_dataset.py    # 批量导入
│   ├── data/                    # ChromaDB + 上传文件 + SQLite
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── views/               # ChatView / DocumentsView
    │   ├── components/          # ChatPanel, SourceCard 等
    │   └── api/index.js         # 后端 API 封装
    └── package.json
```

## 快速开始

### 1. 环境准备

```bash
# 后端
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install jieba rank-bm25

# 前端
cd ../frontend
npm install
```

### 2. 配置

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 3. 启动

```bash
# 终端 1 — 后端
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# 终端 2 — 前端
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`

### 4. 运行评估

```bash
cd backend/tests
python run_eval.py
```

## 部署

见 [部署指南](DEPLOY.md) — Ubuntu + Nginx + Systemd + Let's Encrypt。

## API

| 接口 | 说明 |
|------|------|
| `POST /api/upload` | 上传文档，自动解析分块索引 |
| `POST /api/chat` | 全局跨文档问答 (SSE 流式) |
| `POST /api/chat/{doc_id}` | 单文档问答 (SSE) |
| `GET /api/documents` | 文档列表 |
| `DELETE /api/documents/{id}` | 删除文档（向量 + 文件 + 记录） |
| `GET /api/conversations` | 对话历史 |
| `DELETE /api/conversations/{id}` | 删除单条对话 |
| `GET /api/health` | 健康检查 |

SSE 事件类型：

```json
{"type": "pipeline", "pipeline": {...}}
{"type": "sources", "sources": [...]}
{"type": "reasoning", "content": "..."}
{"type": "token", "content": "..."}
{"type": "abstain", "message": "...", "level": "hard"}
{"type": "done"}
```

## License

MIT
