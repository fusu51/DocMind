# DocMind 部署指南

## Ubuntu + Nginx + Systemd

### 环境

```bash
sudo apt update && sudo apt install -y nginx python3.12 python3.12-venv git
```

### 上传项目

```bash
# scp 或 git clone
git clone <your-repo> /home/fusu/project/DocMind
```

### 后端

```bash
cd /home/fusu/project/DocMind/backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install jieba rank-bm25

cp .env.example .env
# 编辑 .env，填入 API Key，路径改为绝对路径
nano .env
```

`.env` 生产配置：

```env
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=你的地址

LLM_PROVIDER=openai
LLM_API_KEY=sk-xxx
LLM_CHAT_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com

CHROMA_PERSIST_DIR=/home/fusu/project/DocMind/backend/data/chroma
UPLOAD_DIR=/home/fusu/project/DocMind/backend/data/uploads
DATABASE_URL=sqlite:////home/fusu/project/DocMind/backend/data/conversations.db

PORT=8001
ALLOWED_ORIGINS=https://docmind.fusu.pw

RERANKER_MODEL=bge-reranker-v2-m3
RERANKER_BASE_URL=你的地址
RERANKER_API_KEY=你的Key

ABSTAIN_HARD_THRESHOLD=0.1
ABSTAIN_SOFT_THRESHOLD=0.3
MAX_CONTEXT_TOKENS=3000
```

### 前端

```bash
cd /home/fusu/project/DocMind/frontend
npm install && npm run build
```

### Nginx

```bash
sudo nano /etc/nginx/sites-available/docmind
```

```nginx
server {
    listen 80;
    server_name docmind.fusu.pw;
    root /home/fusu/project/DocMind/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/docmind /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### Systemd

```bash
sudo nano /etc/systemd/system/docmind.service
```

```ini
[Unit]
Description=DocMind RAG API
After=network.target

[Service]
Type=simple
User=fusu
WorkingDirectory=/home/fusu/project/DocMind/backend
Environment="PATH=/home/fusu/project/DocMind/backend/venv/bin"
ExecStart=/home/fusu/project/DocMind/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now docmind
sudo systemctl status docmind
```

### SSL

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d docmind.fusu.pw
```

### 日常维护

```bash
# 更新代码
cd /home/fusu/project/DocMind && git pull
cd frontend && npm install && npm run build
sudo systemctl restart docmind

# 查看日志
sudo journalctl -u docmind -f

# 备份
tar -czf docmind-data-$(date +%Y%m%d).tar.gz backend/data/
```
