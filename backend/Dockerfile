FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple jieba rank-bm25

COPY . .

RUN mkdir -p /app/data/chroma /app/data/uploads

ENV CHROMA_PERSIST_DIR=/app/data/chroma
ENV UPLOAD_DIR=/app/data/uploads
ENV DATABASE_URL=sqlite:////app/data/conversations.db

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
