"""文档上传 API — 上传 → 解析 → 语义分块 → 向量化 → 入库"""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from ..auth import verify_token
from ..config import UPLOAD_DIR
from ..rag.parser import parse_document
from ..rag.chunker import chunk_document
from ..rag.retriever import add_chunks
from ..db.repository import add_document

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".md", ".txt"}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), _=Depends(verify_token)):
    """上传文档并自动索引"""

    # 1. 校验文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}")

    # 2. 保存到本地
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = uuid.uuid4().hex[:12]
    save_name = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)

    content = await file.read()
    file_size = len(content)

    with open(save_path, "wb") as f:
        f.write(content)

    # 3. 解析文档
    try:
        text, meta = parse_document(save_path)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(500, f"文档解析失败: {str(e)}")

    # 4. 入库获得 doc_id
    doc_id = add_document(
        name=file.filename,
        file_path=save_path,
        file_type=meta["file_type"],
        file_size=file_size,
        total_pages=meta["total_pages"],
        chunk_count=0,
    )

    # 5. 语义分块（L0）— 返回 (子块, 父块)
    child_chunks, parent_chunks = chunk_document(
        text=text,
        doc_id=doc_id,
        doc_name=file.filename,
        file_type=meta["file_type"],
        total_pages=meta["total_pages"],
        use_semantic=True,
    )

    if not child_chunks:
        os.remove(save_path)
        raise HTTPException(400, "文档内容为空，无法索引")

    # 6. 将子块入库（向量检索用），同时注入父块文本
    child_dicts = []
    for c in child_chunks:
        d = {
            "text": c.text,
            "doc_id": c.metadata["doc_id"],
            "doc_name": c.metadata["doc_name"],
            "page_number": c.metadata["page_number"],
            "chunk_index": c.metadata["chunk_index"],
            "chunk_type": c.metadata.get("chunk_type", "child"),
        }
        # 关联父块文本（LLM 回答时使用更大上下文）
        pi = c.metadata.get("parent_index")
        if pi is not None and pi < len(parent_chunks):
            d["parent_text"] = parent_chunks[pi].text
        child_dicts.append(d)

    try:
        add_chunks(child_dicts)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(500, f"向量化失败: {str(e)}")

    # 7. 更新分块数量
    from ..db.models import get_connection
    conn = get_connection()
    conn.execute("UPDATE documents SET chunk_count = ? WHERE id = ?", (len(child_chunks), doc_id))
    conn.commit()
    conn.close()

    return {
        "id": doc_id,
        "name": file.filename,
        "chunks": len(child_chunks),
        "message": "上传并索引成功",
    }
