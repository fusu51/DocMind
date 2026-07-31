"""问答 API — SSE 流式返回"""
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from ..main import verify_token
from ..models.schemas import ChatRequest
from ..rag.hybrid_search import hybrid_search
from ..db.repository import save_conversation
from ..rag.generator import stream_generate, compress_chunks
from ..config import MAX_CONTEXT_TOKENS

router = APIRouter()


async def _generate_sse(question: str, doc_id: str | None, history: list = None):
    # 1. 检索
    chunks, pipeline = hybrid_search(question, doc_id=doc_id)

    # 2. L4 压缩
    pipeline["l4"]["original"] = len(chunks)
    pipeline["l4"]["max_tokens"] = MAX_CONTEXT_TOKENS
    chunks = compress_chunks(chunks)
    pipeline["l4"]["compressed"] = len(chunks)

    # 3. 发送管线（含 top1_score 和 abstain_level）
    yield f"data: {json.dumps({'type': 'pipeline', 'pipeline': pipeline}, ensure_ascii=False)}\n\n"

    # 4. 硬拒答：跳过 LLM
    if pipeline.get("abstain_level") == "hard":
        yield f"data: {json.dumps({'type': 'abstain', 'message': '文档中没有足够相关内容来回答这个问题', 'level': 'hard'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # 5. 发送 sources
    sources_data = [
        {
            "doc_name": c["doc_name"],
            "page": c["page_number"],
            "text": c["text"][:200],
            "score": c["score"],
        }
        for c in chunks
    ]
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data}, ensure_ascii=False)}\n\n"

    # 6. 流式生成（软拒答时注入 refusal_hint）
    refusal_hint = (pipeline.get("abstain_level") == "soft")

    full_answer = ""
    full_reasoning = ""
    try:
        async for event in stream_generate(question, chunks, refusal_hint=refusal_hint, history=history):
            content = event["content"]
            if event["type"] == "token":
                full_answer += content
            elif event["type"] == "reasoning":
                full_reasoning += content
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except Exception as e:
        error_msg = f"LLM 调用失败: {str(e)}"
        yield f"data: {json.dumps({'type': 'token', 'content': error_msg}, ensure_ascii=False)}\n\n"

    # 7. 保存对话记录（含 reasoning 和 pipeline）
    try:
        save_conversation(doc_id, question, full_answer, sources_data, full_reasoning, pipeline)
    except Exception:
        pass

    # 8. 结束
    yield f"data: {json.dumps({'type': 'done'})}\n\n"



@router.post("/chat")
async def chat_global(req: ChatRequest, _=Depends(verify_token)):
    return StreamingResponse(
        _generate_sse(req.question, doc_id=None, history=req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/{doc_id}")
async def chat_single(doc_id: str, req: ChatRequest, _=Depends(verify_token)):
    from ..db.repository import get_document
    if not get_document(doc_id):
        raise HTTPException(404, "文档不存在")

    return StreamingResponse(
        _generate_sse(req.question, doc_id=doc_id, history=req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
