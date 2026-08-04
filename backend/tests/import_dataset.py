"""增量导入 split_merged.json — 跳过已入库文档"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.rag.chunker import chunk_document
from app.rag.retriever import add_chunks
from app.db.repository import add_document
from app.db.models import get_connection
from app.config import UPLOAD_DIR

with open("split_merged.json", "r", encoding="utf-8") as f:
    data = json.load(f)

items = data["event_summary"]
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 查重：已入库的文档标题集合
conn = get_connection()
existing = set(row[0] for row in conn.execute("SELECT name FROM documents").fetchall())
conn.close()

print(f"数据集 {len(items)} 条，已入库 {len(existing)} 条\n")

success = 0
skipped = 0

for i, item in enumerate(items):
    title = item.get("title", f"doc_{i}").strip()[:80]
    text = item.get("text", "").strip()

    if not text:
        continue

    # 查重：标题已存在则跳过
    if title in existing:
        skipped += 1
        continue

    file_name = f"item_{i:04d}.txt"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    doc_id = add_document(
        name=title,
        file_path=file_path,
        file_type="txt",
        file_size=len(text.encode("utf-8")),
        total_pages=1,
        chunk_count=0,
    )

    children, parents = chunk_document(
        text=text, doc_id=doc_id, doc_name=title,
        file_type="txt", total_pages=1, use_semantic=True,
    )

    child_dicts = []
    for c in children:
        d = {
            "text": c.text,
            "doc_id": c.metadata["doc_id"],
            "doc_name": c.metadata["doc_name"],
            "page_number": c.metadata["page_number"],
            "chunk_index": c.metadata["chunk_index"],
            "chunk_type": c.metadata.get("chunk_type", "child"),
        }
        pi = c.metadata.get("parent_index")
        if pi is not None and pi < len(parents):
            d["parent_text"] = parents[pi].text
        child_dicts.append(d)

    try:
        add_chunks(child_dicts)
    except Exception as e:
        print(f"[{i+1:04d}/{len(items)}] ❌ {title[:40]} → {e}")
        continue

    conn = get_connection()
    conn.execute("UPDATE documents SET chunk_count = ? WHERE id = ?", (len(children), doc_id))
    conn.commit()
    conn.close()

    existing.add(title)
    success += 1
    print(f"[{i+1:04d}/{len(items)}] ✅ {title[:50]} → {len(children)} chunks")

print(f"\n完成: 新增 {success}, 跳过 {skipped} (已存在)")
